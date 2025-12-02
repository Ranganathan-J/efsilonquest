from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


class BusinessEntity(models.Model):
    """
    Business or organization that owns the feedback data.
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # Owner
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='entities',
        help_text="User who created this entity"
    )
    
    # Settings
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Business Entities"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_active']),
        ]

    def __str__(self):
        return self.name
    
    @property
    def total_feedbacks(self):
        return self.raw_feeds.count()
    
    @property
    def new_feedbacks(self):
        return self.raw_feeds.filter(status='new').count()
    
    @property
    def processed_feedbacks(self):
        return self.raw_feeds.filter(status='processed').count()


class RawFeed(models.Model):
    """
    Raw feedback data from various sources.
    """
    
    SOURCE_CHOICES = [
        ('website', 'Website'),
        ('twitter', 'Twitter'),
        ('reddit', 'Reddit'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('app_store', 'App Store'),
        ('play_store', 'Play Store'),
        ('email', 'Email'),
        ('csv', 'CSV Upload'),
        ('api', 'API'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ]
    
    # Relationships
    entity = models.ForeignKey(
        BusinessEntity, 
        on_delete=models.CASCADE, 
        related_name='raw_feeds'
    )
    
    # Core Fields
    text = models.TextField(help_text="Raw feedback text")
    source = models.CharField(
        max_length=50, 
        choices=SOURCE_CHOICES, 
        default='other'
    )
    
    # Optional Metadata
    product_name = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="Product being reviewed"
    )
    customer_name = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="Name of customer who gave feedback"
    )
    customer_email = models.EmailField(
        null=True,
        blank=True,
        help_text="Customer email address"
    )
    rating = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5"
    )
    
    # External ID for tracking
    external_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="External reference ID from source system"
    )
    
    # Status Tracking
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='new'
    )
    error_message = models.TextField(
        null=True, 
        blank=True,
        help_text="Error details if processing failed"
    )
    
    # Timestamps
    feedback_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Original date when feedback was given"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When record was created in our system"
    )
    processed_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When feedback was successfully processed"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['source', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['product_name']),
        ]
        verbose_name = "Raw Feedback"
        verbose_name_plural = "Raw Feedbacks"
    
    def __str__(self):
        preview = self.text[:50] + '...' if len(self.text) > 50 else self.text
        return f"Feedback #{self.id} - {self.entity.name} ({self.status})"
    
    @property
    def is_new(self):
        return self.status == 'new'
    
    @property
    def is_processed(self):
        return self.status == 'processed'
    
    @property
    def is_failed(self):
        return self.status == 'failed'


class FeedbackBatch(models.Model):
    """
    Track bulk upload batches for better organization.
    """
    
    entity = models.ForeignKey(
        BusinessEntity,
        on_delete=models.CASCADE,
        related_name='batches'
    )
    
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_batches'
    )
    
    # Batch Info
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20)  # csv, xlsx, json
    source = models.CharField(
        max_length=50,
        choices=RawFeed.SOURCE_CHOICES,
        default='csv'
    )
    
    # Statistics
    total_rows = models.IntegerField(default=0)
    successful_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    
    # Status
    STATUS_CHOICES = [
        ('uploading', 'Uploading'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='uploading'
    )
    
    error_log = models.JSONField(
        default=list,
        help_text="List of errors encountered during processing"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Feedback Batch"
        verbose_name_plural = "Feedback Batches"
    
    def __str__(self):
        return f"Batch #{self.id} - {self.file_name} ({self.status})"
    
    @property
    def success_rate(self):
        if self.total_rows == 0:
            return 0
        return (self.successful_rows / self.total_rows) * 100