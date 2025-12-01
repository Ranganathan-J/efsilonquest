from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class User(AbstractUser):
   
   Roll_choices = [
        ('admin', 'Admin'),
        ('analyst', 'Analyst'),
        ('viewer', 'Viewer'),
   ]
   role = models.CharField(max_length=20, choices=Roll_choices, default='viewer')

   def __str__(self):
        return f"{self.username} - {self.role}"