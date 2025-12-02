from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Avg, Q
from .models import ProcessedFeedback
from .serializers import (
    ProcessedFeedbackSerializer,
    ProcessedFeedbackListSerializer,
    SentimentStatsSerializer
)
from data_ingestion.tasks import reprocess_failed_feedbacks
import logging

logger = logging.getLogger(__name__)


class ProcessedFeedbackViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing processed feedbacks.
    
    list: GET /api/analysis/processed-feedbacks/
    retrieve: GET /api/analysis/processed-feedbacks/{id}/
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['raw_feed__text', 'summary', 'topics']
    ordering_fields = ['processed_at', 'sentiment_score']
    ordering = ['-processed_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProcessedFeedbackListSerializer
        return ProcessedFeedbackSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Base queryset with optimized joins
        queryset = ProcessedFeedback.objects.select_related(
            'raw_feed',
            'raw_feed__entity',
            'raw_feed__entity__owner'
        )
        
        # Filter by user permissions
        if not user.is_admin:
            queryset = queryset.filter(raw_feed__entity__owner=user)
        
        # Apply filters
        return self._apply_filters(queryset)
    
    def _apply_filters(self, queryset):
        """Apply query parameter filters"""
        
        # Filter by entity
        entity_id = self.request.query_params.get('entity_id')
        if entity_id:
            queryset = queryset.filter(raw_feed__entity_id=entity_id)
        
        # Filter by sentiment
        sentiment = self.request.query_params.get('sentiment')
        if sentiment:
            queryset = queryset.filter(sentiment=sentiment)
        
        # Filter by minimum sentiment score
        min_score = self.request.query_params.get('min_score')
        if min_score:
            queryset = queryset.filter(sentiment_score__gte=float(min_score))
        
        # Filter by topic
        topic = self.request.query_params.get('topic')
        if topic:
            queryset = queryset.filter(topics__contains=[topic])
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(processed_at__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(processed_at__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def sentiment_stats(self, request):
        """
        Get sentiment statistics.
        
        GET /api/analysis/processed-feedbacks/sentiment_stats/
        Query params:
        - entity_id: Filter by entity
        - start_date: Filter by start date
        - end_date: Filter by end date
        """
        queryset = self.get_queryset()
        
        total = queryset.count()
        
        if total == 0:
            return Response({
                'total_processed': 0,
                'message': 'No processed feedbacks found'
            })
        
        # Count by sentiment
        sentiment_counts = queryset.values('sentiment').annotate(
            count=Count('id')
        )
        
        positive_count = next(
            (item['count'] for item in sentiment_counts if item['sentiment'] == 'positive'),
            0
        )
        neutral_count = next(
            (item['count'] for item in sentiment_counts if item['sentiment'] == 'neutral'),
            0
        )
        negative_count = next(
            (item['count'] for item in sentiment_counts if item['sentiment'] == 'negative'),
            0
        )
        
        # Calculate percentages
        stats = {
            'total_processed': total,
            'positive_count': positive_count,
            'neutral_count': neutral_count,
            'negative_count': negative_count,
            'positive_percentage': (positive_count / total * 100) if total > 0 else 0,
            'neutral_percentage': (neutral_count / total * 100) if total > 0 else 0,
            'negative_percentage': (negative_count / total * 100) if total > 0 else 0,
            'average_sentiment_score': queryset.aggregate(
                avg=Avg('sentiment_score')
            )['avg'] or 0,
            'topic_breakdown': self._get_topic_breakdown(queryset)
        }
        
        serializer = SentimentStatsSerializer(stats)
        return Response(serializer.data)
    
    def _get_topic_breakdown(self, queryset):
        """Get breakdown of topics from processed feedbacks"""
        topic_counts = {}
        
        for feedback in queryset:
            for topic in feedback.topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Sort by count and return top 10
        sorted_topics = sorted(
            topic_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return dict(sorted_topics)
    
    @action(detail=False, methods=['post'])
    def reprocess_failed(self, request):
        """
        Trigger reprocessing of all failed feedbacks.
        
        POST /api/analysis/processed-feedbacks/reprocess_failed/
        """
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can trigger reprocessing'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Trigger Celery task
        task = reprocess_failed_feedbacks.delay()
        
        logger.info(f"Reprocess task triggered by {request.user.username}")
        
        return Response({
            'message': 'Reprocessing task triggered',
            'task_id': task.id
        })