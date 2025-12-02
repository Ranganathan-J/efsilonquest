from rest_framework import status, viewsets, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from .models import BusinessEntity, RawFeed, FeedbackBatch
from .serializer import (
    BusinessEntitySerializer, BusinessEntityListSerializer,
    RawFeedSerializer, RawFeedListSerializer, RawFeedCreateSerializer,
    FileUploadSerializer, FeedbackBatchSerializer, FeedbackStatsSerializer
)
import csv
import io
import pandas as pd
import json
import logging

logger = logging.getLogger(__name__)


class BusinessEntityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Business Entities.
    
    list: GET /api/data-ingestion/entities/
    retrieve: GET /api/data-ingestion/entities/{id}/
    create: POST /api/data-ingestion/entities/
    update: PUT /api/data-ingestion/entities/{id}/
    partial_update: PATCH /api/data-ingestion/entities/{id}/
    destroy: DELETE /api/data-ingestion/entities/{id}/
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BusinessEntityListSerializer
        return BusinessEntitySerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Admins can see all entities, others only their own
        if user.is_admin:
            queryset = BusinessEntity.objects.all()
        else:
            queryset = BusinessEntity.objects.filter(owner=user)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            is_active_bool = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active_bool)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set current user as owner"""
        serializer.save(owner=self.request.user)
        logger.info(f"Entity created: {serializer.data['name']} by {self.request.user.username}")
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get detailed statistics for an entity"""
        entity = self.get_object()
        
        feedbacks = entity.raw_feeds.all()
        
        stats = {
            'total_feedbacks': feedbacks.count(),
            'new_feedbacks': feedbacks.filter(status='new').count(),
            'processing_feedbacks': feedbacks.filter(status='processing').count(),
            'processed_feedbacks': feedbacks.filter(status='processed').count(),
            'failed_feedbacks': feedbacks.filter(status='failed').count(),
            'average_rating': feedbacks.aggregate(
                avg_rating=Avg('rating')
            )['avg_rating'] or 0,
            'sources_breakdown': dict(
                feedbacks.values('source').annotate(
                    count=Count('id')
                ).values_list('source', 'count')
            ),
            'products_breakdown': dict(
                feedbacks.filter(product_name__isnull=False)
                .values('product_name').annotate(
                    count=Count('id')
                ).order_by('-count')[:10]
                .values_list('product_name', 'count')
            ),
            'daily_trend': self._get_daily_trend(feedbacks)
        }
        
        serializer = FeedbackStatsSerializer(stats)
        return Response(serializer.data)
    
    def _get_daily_trend(self, queryset):
        """Get feedback count for last 7 days"""
        today = timezone.now().date()
        trend = []
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            count = queryset.filter(created_at__date=date).count()
            trend.append({
                'date': date.isoformat(),
                'count': count
            })
        
        return trend


class RawFeedViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Raw Feedbacks.
    
    list: GET /api/data-ingestion/feedbacks/
    retrieve: GET /api/data-ingestion/feedbacks/{id}/
    create: POST /api/data-ingestion/feedbacks/
    update: PUT /api/data-ingestion/feedbacks/{id}/
    partial_update: PATCH /api/data-ingestion/feedbacks/{id}/
    destroy: DELETE /api/data-ingestion/feedbacks/{id}/
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['text', 'product_name', 'customer_name', 'customer_email']
    ordering_fields = ['created_at', 'rating', 'status', 'processed_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RawFeedListSerializer
        elif self.action == 'create':
            return RawFeedCreateSerializer
        return RawFeedSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Base queryset - users can only see feedbacks from their entities
        if user.is_admin:
            queryset = RawFeed.objects.select_related('entity').all()
        else:
            queryset = RawFeed.objects.select_related('entity').filter(
                entity__owner=user
            )
        
        # Apply filters
        queryset = self._apply_filters(queryset)
        
        return queryset
    
    def _apply_filters(self, queryset):
        """Apply query parameter filters"""
        
        # Filter by entity
        entity_id = self.request.query_params.get('entity_id')
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by source
        source = self.request.query_params.get('source')
        if source:
            queryset = queryset.filter(source=source)
        
        # Filter by product
        product = self.request.query_params.get('product_name')
        if product:
            queryset = queryset.filter(product_name__icontains=product)
        
        # Filter by rating
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            queryset = queryset.filter(rating__gte=int(min_rating))
        
        max_rating = self.request.query_params.get('max_rating')
        if max_rating:
            queryset = queryset.filter(rating__lte=int(max_rating))
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create feedback"""
        # Verify user owns the entity
        entity = serializer.validated_data['entity']
        if not self.request.user.is_admin and entity.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to add feedback to this entity.")
        
        instance = serializer.save()
        logger.info(f"Feedback created: #{instance.id} by {self.request.user.username}")
    
    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Reprocess a specific feedback"""
        feedback = self.get_object()
        
        if feedback.status == 'processing':
            return Response(
                {'error': 'Feedback is already being processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset status
        feedback.status = 'new'
        feedback.error_message = None
        feedback.save(update_fields=['status', 'error_message'])
        
        logger.info(f"Feedback #{feedback.id} queued for reprocessing")
        
        return Response({
            'message': 'Feedback queued for reprocessing',
            'feedback_id': feedback.id
        })


class BulkFeedbackUploadView(APIView):
    """
    Handle bulk feedback uploads via CSV, Excel, or JSON.
    
    POST /api/data-ingestion/bulk-upload/
    
    Form Data:
    - file: The file to upload
    - entity_id: ID of the business entity
    - source: Source of the feedback (default: csv)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = FileUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = serializer.validated_data['file']
        entity_id = serializer.validated_data['entity_id']
        source = serializer.validated_data['source']
        
        # Verify user owns the entity
        try:
            entity = BusinessEntity.objects.get(id=entity_id)
            if not request.user.is_admin and entity.owner != request.user:
                return Response(
                    {'error': "You don't have permission to upload to this entity"},
                    status=status.HTTP_403_FORBIDDEN
                )
        except BusinessEntity.DoesNotExist:
            return Response(
                {'error': 'Business entity not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create batch record
        batch = FeedbackBatch.objects.create(
            entity=entity,
            uploaded_by=request.user,
            file_name=file.name,
            file_type=file.name.split('.')[-1].lower(),
            source=source,
            status='processing'
        )
        
        try:
            # Process based on file type
            if file.name.endswith('.csv'):
                result = self._process_csv(file, entity, source, batch)
            elif file.name.endswith(('.xls', '.xlsx')):
                result = self._process_excel(file, entity, source, batch)
            elif file.name.endswith('.json'):
                result = self._process_json(file, entity, source, batch)
            else:
                batch.status = 'failed'
                batch.save()
                return Response(
                    {'error': 'Unsupported file format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update batch status
            batch.status = 'completed'
            batch.completed_at = timezone.now()
            batch.save()
            
            logger.info(
                f"Batch upload completed: {result['created_count']} created, "
                f"{result['skipped_count']} skipped by {request.user.username}"
            )
            
            return Response({
                'batch_id': batch.id,
                **result
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            batch.status = 'failed'
            batch.error_log.append({'error': str(e)})
            batch.save()
            
            logger.error(f"Batch upload failed: {str(e)}")
            
            return Response(
                {'error': f'Upload failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _process_csv(self, file, entity, source, batch):
        """Process CSV file"""
        decoded_file = file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        return self._create_feedbacks_from_rows(reader, entity, source, batch)
    
    def _process_excel(self, file, entity, source, batch):
        """Process Excel file"""
        df = pd.read_excel(file)
        # Replace NaN with None
        df = df.where(pd.notna(df), None)
        rows = df.to_dict('records')
        
        return self._create_feedbacks_from_rows(rows, entity, source, batch)
    
    def _process_json(self, file, entity, source, batch):
        """Process JSON file"""
        data = json.load(file)
        
        if not isinstance(data, list):
            raise ValueError("JSON must be an array of feedback objects")
        
        return self._create_feedbacks_from_rows(data, entity, source, batch)
    
    def _create_feedbacks_from_rows(self, rows, entity, source, batch):
        """Create RawFeed objects from rows"""
        created_feedbacks = []
        skipped_rows = []
        
        for index, row in enumerate(rows, start=1):
            # Map common column names (flexible)
            text = (
                row.get('text') or 
                row.get('feedback_text') or 
                row.get('feedback') or
                row.get('comment') or
                row.get('review')
            )
            
            if not text or len(str(text).strip()) < 5:
                error = {
                    'row': index,
                    'reason': 'Text missing or too short'
                }
                skipped_rows.append(error)
                batch.error_log.append(error)
                continue
            
            try:
                # Extract rating
                rating_value = row.get('rating')
                if rating_value:
                    try:
                        rating_value = int(float(rating_value))
                        if rating_value < 1 or rating_value > 5:
                            rating_value = None
                    except (ValueError, TypeError):
                        rating_value = None
                
                feedback = RawFeed.objects.create(
                    entity=entity,
                    text=str(text).strip(),
                    source=row.get('source', source),
                    product_name=row.get('product_name'),
                    customer_name=row.get('customer_name'),
                    customer_email=row.get('customer_email'),
                    rating=rating_value,
                    external_id=row.get('external_id') or row.get('id'),
                    status='new'
                )
                created_feedbacks.append(feedback)
                
            except Exception as e:
                error = {
                    'row': index,
                    'reason': str(e)
                }
                skipped_rows.append(error)
                batch.error_log.append(error)
        
        # Update batch statistics
        batch.total_rows = index
        batch.successful_rows = len(created_feedbacks)
        batch.failed_rows = len(skipped_rows)
        batch.save()
        
        return {
            'message': 'Bulk upload completed',
            'created_count': len(created_feedbacks),
            'skipped_count': len(skipped_rows),
            'created_ids': [f.id for f in created_feedbacks],
            'skipped_rows': skipped_rows[:20],  # Return first 20 errors
            'total_errors': len(skipped_rows)
        }


class FeedbackStatsView(APIView):
    """
    Get overall feedback statistics.
    
    GET /api/data-ingestion/statistics/
    Query params:
    - entity_id: Filter by entity
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        entity_id = request.query_params.get('entity_id')
        
        # Get feedbacks based on user permissions
        if user.is_admin:
            queryset = RawFeed.objects.all()
        else:
            queryset = RawFeed.objects.filter(entity__owner=user)
        
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        
        stats = {
            'total_feedbacks': queryset.count(),
            'new_feedbacks': queryset.filter(status='new').count(),
            'processing_feedbacks': queryset.filter(status='processing').count(),
            'processed_feedbacks': queryset.filter(status='processed').count(),
            'failed_feedbacks': queryset.filter(status='failed').count(),
            'average_rating': queryset.aggregate(
                avg_rating=Avg('rating')
            )['avg_rating'] or 0,
            'sources_breakdown': dict(
                queryset.values('source').annotate(
                    count=Count('id')
                ).values_list('source', 'count')
            ),
            'products_breakdown': dict(
                queryset.filter(product_name__isnull=False)
                .values('product_name').annotate(
                    count=Count('id')
                ).order_by('-count')[:10]
                .values_list('product_name', 'count')
            ),
            'daily_trend': self._get_daily_trend(queryset)
        }
        
        serializer = FeedbackStatsSerializer(stats)
        return Response(serializer.data)
    
    def _get_daily_trend(self, queryset):
        """Get feedback count for last 7 days"""
        today = timezone.now().date()
        trend = []
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            count = queryset.filter(created_at__date=date).count()
            trend.append({
                'date': date.isoformat(),
                'count': count
            })
        
        return trend


class FeedbackBatchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing Feedback Batches.
    
    list: GET /api/data-ingestion/batches/
    retrieve: GET /api/data-ingestion/batches/{id}/
    """
    serializer_class = FeedbackBatchSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin:
            return FeedbackBatch.objects.select_related(
                'entity', 'uploaded_by'
            ).all()
        else:
            return FeedbackBatch.objects.select_related(
                'entity', 'uploaded_by'
            ).filter(uploaded_by=user)