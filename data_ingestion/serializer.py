from rest_framework import serializers
from django.core.validators import FileExtensionValidator
from .models import BusinessEntity, RawFeed, FeedbackBatch


class BusinessEntitySerializer(serializers.ModelSerializer):
    """Serializer for Business Entity"""
    
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    total_feedbacks = serializers.IntegerField(read_only=True)
    new_feedbacks = serializers.IntegerField(read_only=True)
    processed_feedbacks = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = BusinessEntity
        fields = [
            'id', 'name', 'description', 'owner', 'owner_username',
            'is_active', 'total_feedbacks', 'new_feedbacks',
            'processed_feedbacks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']
    
    def validate_name(self, value):
        """Ensure name is not empty and unique"""
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")
        
        # Check uniqueness (excluding current instance during update)
        queryset = BusinessEntity.objects.filter(name__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("Business entity with this name already exists.")
        
        return value.strip()


class BusinessEntityListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    feedback_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BusinessEntity
        fields = [
            'id', 'name', 'owner_username', 
            'is_active', 'feedback_count', 'created_at'
        ]
    
    def get_feedback_count(self, obj):
        return obj.raw_feeds.count()


class RawFeedSerializer(serializers.ModelSerializer):
    """Serializer for Raw Feedback"""
    
    entity_name = serializers.CharField(source='entity.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    
    class Meta:
        model = RawFeed
        fields = [
            'id', 'entity', 'entity_name', 'text', 'source', 'source_display',
            'product_name', 'customer_name', 'customer_email', 'rating',
            'external_id', 'status', 'status_display', 'error_message',
            'feedback_date', 'created_at', 'processed_at'
        ]
        read_only_fields = [
            'status', 'error_message', 'created_at', 'processed_at'
        ]
    
    def validate_text(self, value):
        """Ensure feedback text is not empty and has minimum length"""
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Feedback text must be at least 5 characters long."
            )
        return value.strip()
    
    def validate_rating(self, value):
        """Validate rating is between 1 and 5"""
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError(
                "Rating must be between 1 and 5."
            )
        return value
    
    def validate_entity(self, value):
        """Ensure entity is active"""
        if not value.is_active:
            raise serializers.ValidationError(
                "Cannot add feedback to inactive entity."
            )
        return value


class RawFeedListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    
    entity_name = serializers.CharField(source='entity.name', read_only=True)
    text_preview = serializers.SerializerMethodField()
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    
    class Meta:
        model = RawFeed
        fields = [
            'id', 'entity_name', 'text_preview', 'source', 'source_display',
            'product_name', 'rating', 'status', 'created_at'
        ]
    
    def get_text_preview(self, obj):
        """Return first 80 characters of text"""
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text


class RawFeedCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating single feedback"""
    
    class Meta:
        model = RawFeed
        fields = [
            'entity', 'text', 'source', 'product_name',
            'customer_name', 'customer_email', 'rating',
            'external_id', 'feedback_date'
        ]
    
    def validate_text(self, value):
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Feedback text must be at least 5 characters long."
            )
        return value.strip()


class BulkFeedbackSerializer(serializers.Serializer):
    """Serializer for bulk feedback creation from data rows"""
    
    entity_id = serializers.IntegerField()
    text = serializers.CharField(max_length=10000)
    source = serializers.ChoiceField(
        choices=RawFeed.SOURCE_CHOICES,
        default='csv'
    )
    product_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True
    )
    customer_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True
    )
    customer_email = serializers.EmailField(
        required=False,
        allow_blank=True,
        allow_null=True
    )
    rating = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=5
    )
    external_id = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True
    )
    
    def validate_entity_id(self, value):
        """Ensure entity exists and is active"""
        try:
            entity = BusinessEntity.objects.get(id=value)
            if not entity.is_active:
                raise serializers.ValidationError("Entity is not active.")
            return value
        except BusinessEntity.DoesNotExist:
            raise serializers.ValidationError(
                f"BusinessEntity with id {value} does not exist."
            )
    
    def validate_text(self, value):
        """Ensure text is not empty"""
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Text must be at least 5 characters long."
            )
        return value.strip()


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file uploads"""
    
    file = serializers.FileField(
        validators=[
            FileExtensionValidator(
                allowed_extensions=['csv', 'xlsx', 'xls', 'json']
            )
        ]
    )
    entity_id = serializers.IntegerField()
    source = serializers.ChoiceField(
        choices=RawFeed.SOURCE_CHOICES,
        default='csv'
    )
    
    def validate_file(self, value):
        """Validate file size"""
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size cannot exceed {max_size / (1024 * 1024):.0f}MB. "
                f"Your file is {value.size / (1024 * 1024):.2f}MB."
            )
        return value
    
    def validate_entity_id(self, value):
        """Ensure entity exists and is active"""
        try:
            entity = BusinessEntity.objects.get(id=value)
            if not entity.is_active:
                raise serializers.ValidationError("Cannot upload to inactive entity.")
            return value
        except BusinessEntity.DoesNotExist:
            raise serializers.ValidationError(
                f"BusinessEntity with id {value} does not exist."
            )


class FeedbackBatchSerializer(serializers.ModelSerializer):
    """Serializer for Feedback Batch"""
    
    uploaded_by_username = serializers.CharField(
        source='uploaded_by.username',
        read_only=True
    )
    entity_name = serializers.CharField(source='entity.name', read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = FeedbackBatch
        fields = [
            'id', 'entity', 'entity_name', 'uploaded_by',
            'uploaded_by_username', 'file_name', 'file_type', 'source',
            'total_rows', 'successful_rows', 'failed_rows',
            'success_rate', 'status', 'error_log',
            'created_at', 'completed_at'
        ]
        read_only_fields = [
            'uploaded_by', 'total_rows', 'successful_rows',
            'failed_rows', 'status', 'error_log',
            'created_at', 'completed_at'
        ]


class FeedbackStatsSerializer(serializers.Serializer):
    """Serializer for feedback statistics"""
    
    total_feedbacks = serializers.IntegerField()
    new_feedbacks = serializers.IntegerField()
    processing_feedbacks = serializers.IntegerField()
    processed_feedbacks = serializers.IntegerField()
    failed_feedbacks = serializers.IntegerField()
    average_rating = serializers.FloatField()
    sources_breakdown = serializers.DictField()
    products_breakdown = serializers.DictField()
    daily_trend = serializers.ListField()