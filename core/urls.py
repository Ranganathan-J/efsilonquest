from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.permissions import AllowAny

schema_view = get_schema_view(
    openapi.Info(
        title="EpsilonQuest API",
        default_version='v1',
        description="API documentation for EpsilonQuest",
    ),
    public=True,
    permission_classes=[AllowAny],
    authentication_classes = [],
)

def home(request):
    return HttpResponse("Welcome to EpsilonQuest API!")

urlpatterns = [
    path('admin/', admin.site.urls),

    # User module
    path('api/users/', include('users.urls')),

    # Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    # Default home
    path('', home),
]
