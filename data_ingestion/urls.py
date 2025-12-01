from django.urls import path
from .views import SubmitRawFeedView, EntityRawFeedView


urlpatterns = [
    path('submit-raw-feed/', SubmitRawFeedView.as_view(), name='submit-raw-feed'),
    path('entity-raw-feeds/<int:entity_id>/', EntityRawFeedView.as_view(), name='entity-raw-feeds'),
]