from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BusinessEntityViewSet,
    RawFeedViewSet,
    BulkFeedbackUploadView,
    FeedbackStatsView,
    FeedbackBatchViewSet,
)

router = DefaultRouter()
router.register(r'entities', BusinessEntityViewSet, basename='entity')
router.register(r'feedbacks', RawFeedViewSet, basename='feedback')
router.register(r'batches', FeedbackBatchViewSet, basename='batch')

urlpatterns = [
    path('', include(router.urls)),
    path('bulk-upload/', BulkFeedbackUploadView.as_view(), name='bulk-upload'),
    path('statistics/', FeedbackStatsView.as_view(), name='statistics'),
]