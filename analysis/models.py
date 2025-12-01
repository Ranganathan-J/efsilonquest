from django.db import models
from data_ingestion.models import BusinessEntity, RawFeed
# Create your models here.
class ProcessFeedback(models.Model):
    raw = models.OneToOneField(RawFeed, on_delete=models.CASCADE)
    sentiment = models.CharField(max_length=50)
    topics = models.JSONField()
    embeddings = models.JSONField()
    timesstamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"raw_id{self.raw.id}"
    


class Insights(models.Model):
    ProcessFeedback = models.ForeignKey(ProcessFeedback, on_delete=models.CASCADE)
    text = models.TextField()
    score = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"insight_id{self.id}"
