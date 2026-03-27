
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # ReDoc
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),


    path("auth/", include("users.urls")),
    path("", include("jobs.urls")),
    path("", include("candidates.urls")),
    path("", include("interviews.urls")),
    path("", include("notification.urls")),
    
    ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
