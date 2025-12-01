from django.db import models

# Create your models here.
class BusinessEntity(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    

    def __str__(self):
        return self.name
    

class RawFeed(models.Model):
    text = models.TextField()
    source = models.CharField(max_length=255)
    entity = models.ForeignKey(BusinessEntity, on_delete=models.CASCADE, related_name='raw_feeds')
    timestamp = models.DateTimeField(auto_now_add=True)