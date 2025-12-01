from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import BusinessEntity, RawFeed
from .serializer import BusinessEntitySerializer, RawFeedSerializer
# Create your views here.

#submit raw feed data
class SubmitRawFeedView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = RawFeedSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


# list all the feedback
class EntityRawFeedView(APIView):
    def get(self, request, entity_id, *args, **kwargs):
        try:
            entity = BusinessEntity.objects.get(id=entity_id)
        except BusinessEntity.DoesNotExist:
            return Response({"error": "BusinessEntity not found."}, status=status.HTTP_404_NOT_FOUND)
        
        raw_feeds = RawFeed.objects.filter(entity=entity)
        serializer = RawFeedSerializer(raw_feeds, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
