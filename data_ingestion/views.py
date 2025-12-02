from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import BusinessEntity, RawFeed
from .serializer import RawFeedSerializer
from .tasks import process_feedback
import csv
import io
import pandas as pd

class SubmitRawFeedView(APIView):
    """
    Accepts:
    - Single JSON feedback object
    - CSV file upload
    - Excel file upload (XLS/XLSX)
    
    Triggers async Celery task for each feedback.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        saved_instances = []
        skipped_rows = 0

        file = request.FILES.get('file')

        # ------------------ CSV upload ------------------
        if file and file.name.endswith('.csv'):
            data_set = file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            reader = csv.DictReader(io_string)

            for row in reader:
                entity_id = row.get('entity_id')
                if not entity_id or not row.get('product_name'):
                    skipped_rows += 1
                    continue
                try:
                    entity = BusinessEntity.objects.get(id=entity_id)
                except BusinessEntity.DoesNotExist:
                    skipped_rows += 1
                    continue

                feedback = RawFeed.objects.create(
                    entity=entity,
                    customer_name=row.get('customer_name'),
                    product_name=row.get('product_name'),
                    feedback_text=row.get('feedback_text'),
                    rating=int(row.get('rating', 0)),
                    status='new'
                )
                saved_instances.append(feedback)
                process_feedback.delay(feedback.id)

            serializer = RawFeedSerializer(saved_instances, many=True)
            return Response({
                "created": serializer.data,
                "skipped_rows": skipped_rows
            }, status=status.HTTP_201_CREATED)

        # ------------------ Excel upload ------------------
        if file and file.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file)
            for _, row in df.iterrows():
                entity_id = row.get('entity_id')
                if not entity_id or not row.get('product_name'):
                    skipped_rows += 1
                    continue
                try:
                    entity = BusinessEntity.objects.get(id=entity_id)
                except BusinessEntity.DoesNotExist:
                    skipped_rows += 1
                    continue

                feedback = RawFeed.objects.create(
                    entity=entity,
                    customer_name=row.get('customer_name'),
                    product_name=row.get('product_name'),
                    feedback_text=row.get('feedback_text'),
                    rating=int(row.get('rating', 0)),
                    status='new'
                )
                saved_instances.append(feedback)
                process_feedback.delay(feedback.id)

            serializer = RawFeedSerializer(saved_instances, many=True)
            return Response({
                "created": serializer.data,
                "skipped_rows": skipped_rows
            }, status=status.HTTP_201_CREATED)

        # ------------------ JSON single feedback ------------------
        serializer = RawFeedSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            process_feedback.delay(instance.id)
            return Response({
                "created": serializer.data,
                "skipped_rows": 0
            }, status=status.HTTP_201_CREATED)

        # ------------------ Invalid request ------------------
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class EntityRawFeedView(APIView):
    """
    List all feedbacks for a specific BusinessEntity
    """
    def get(self, request, entity_id, *args, **kwargs):
        try:
            entity = BusinessEntity.objects.get(id=entity_id)
        except BusinessEntity.DoesNotExist:
            return Response({"error": "BusinessEntity not found."}, status=status.HTTP_404_NOT_FOUND)

        raw_feeds = RawFeed.objects.filter(entity=entity)
        serializer = RawFeedSerializer(raw_feeds, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
