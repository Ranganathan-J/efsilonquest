from django.db import models
from data_ingestion.models import RawFeed


class ProcessedFeedback(models.Model):
    """
    AI-processed feedback with sentiment analysis and topics.
    Created by Celery tasks after processing RawFeed.
    """
    
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]
    
    # Link to original raw feedback (one-to-one)
    raw_feed = models.OneToOneField(
        RawFeed,
        on_delete=models.CASCADE,
        related_name='processed_feedback',
        help_text="Original raw feedback that was processed"
    )
    
    # AI Analysis Results
    sentiment = models.CharField(
        max_length=20,
        choices=SENTIMENT_CHOICES,
        help_text="Overall sentiment: positive, negative, or neutral"
    )
    
    sentiment_score = models.FloatField(
        help_text="Confidence score for sentiment (0.0 to 1.0)"
    )
    
    topics = models.JSONField(
        default=list,
        help_text="List of extracted topics/keywords"
    )
    
    embeddings = models.JSONField(
        default=list,
        help_text="Vector embeddings for similarity search"
    )
    
    # Summary and Key Information
    summary = models.TextField(
        blank=True,
        null=True,
        help_text="AI-generated summary of the feedback"
    )
    
    key_phrases = models.JSONField(
        default=list,
        help_text="Important phrases extracted from feedback"
    )
    
    # Processing Metadata
    processing_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Time taken to process (in seconds)"
    )
    
    model_version = models.CharField(
        max_length=50,
        default="v1.0",
        help_text="Version of AI model used for processing"
    )
    
    processed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the feedback was processed"
    )
    
    class Meta:
        ordering = ['-processed_at']
        indexes = [
            models.Index(fields=['sentiment', 'processed_at']),
            models.Index(fields=['sentiment_score']),
        ]
        verbose_name = "Processed Feedback"
        verbose_name_plural = "Processed Feedbacks"
    
    def __str__(self):
        return f"Processed #{self.raw_feed.id} - {self.sentiment} ({self.sentiment_score:.2f})"
    
    @property
    def is_positive(self):
        return self.sentiment == 'positive'
    
    @property
    def is_negative(self):
        return self.sentiment == 'negative'
    
    @property
    def is_high_confidence(self):
        return self.sentiment_score >= 0.8