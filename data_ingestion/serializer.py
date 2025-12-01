from rest_framework import serializers
from .models import BusinessEntity, RawFeed


class BusinessEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessEntity
        fields = ['id', 'name', 'description']

    

class RawFeedSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawFeed
        fields = ['id', 'text', 'source', 'entity', 'timestamp']
        read_only_fields = ['timestamp']