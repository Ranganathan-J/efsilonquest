from rest_framework import serializers
from .models import ProcessedFeedback
from data_ingestion.serializers import RawFeedSerializer


class ProcessedFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for ProcessedFeedback with related raw feed data"""
    
    # Include raw feed details
    raw_feed_text = serializers.CharField(source='raw_feed.text', read_only=True)
    entity_name = serializers.CharField(source='raw_feed.entity.name', read_only=True)
    product_name = serializers.CharField(source='raw_feed.product_name', read_only=True)
    rating = serializers.IntegerField(source='raw_feed.rating', read_only=True)
    source = serializers.CharField(source='raw_feed.source', read_only=True)
    sentiment_display = serializers.CharField(source='get_sentiment_display', read_only=True)
    
    class Meta:
        model = ProcessedFeedback
        fields = [
            'id', 'raw_feed', 'raw_feed_text', 'entity_name',
            'product_name', 'rating', 'source',
            'sentiment', 'sentiment_display', 'sentiment_score',
            'topics', 'key_phrases', 'summary',
            'processing_time', 'model_version', 'processed_at'
        ]
        read_only_fields = ['processed_at']


class ProcessedFeedbackListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    
    entity_name = serializers.CharField(source='raw_feed.entity.name', read_only=True)
    text_preview = serializers.SerializerMethodField()
    sentiment_display = serializers.CharField(source='get_sentiment_display', read_only=True)
    
    class Meta:
        model = ProcessedFeedback
        fields = [
            'id', 'raw_feed', 'entity_name', 'text_preview',
            'sentiment', 'sentiment_display', 'sentiment_score',
            'topics', 'processed_at'
        ]
    
    def get_text_preview(self, obj):
        text = obj.raw_feed.text
        return text[:80] + '...' if len(text) > 80 else text


class SentimentStatsSerializer(serializers.Serializer):
    """Serializer for sentiment statistics"""
    
    total_processed = serializers.IntegerField()
    positive_count = serializers.IntegerField()
    neutral_count = serializers.IntegerField()
    negative_count = serializers.IntegerField()
    positive_percentage = serializers.FloatField()
    neutral_percentage = serializers.FloatField()
    negative_percentage = serializers.FloatField()
    average_sentiment_score = serializers.FloatField()
    topic_breakdown = serializers.DictField()