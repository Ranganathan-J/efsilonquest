from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

# DRF Spectacular
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

def home(request):
    return HttpResponse("Welcome to EpsilonQuest API!")

urlpatterns = [
    path('admin/', admin.site.urls),

    # API modules
    path('api/users/', include('users.urls')),
    path('api/data-ingestion/', include('data_ingestion.urls')),

    # Analysis module
    path('api/analysis/', include('analysis.urls')),

    # DRF Spectacular schema + docs
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Default route
    path('', home),
]
