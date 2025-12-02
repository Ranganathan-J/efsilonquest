from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProcessedFeedbackViewSet

router = DefaultRouter()
router.register(r'processed-feedbacks', ProcessedFeedbackViewSet, basename='processed-feedback')

urlpatterns = [
    path('', include(router.urls)),
]