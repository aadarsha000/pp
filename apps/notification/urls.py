from django.urls import path, include
from rest_framework.routers import DefaultRouter
from notification.views import NotificationViewSet

router = DefaultRouter()

router.register(r'notifications', NotificationViewSet, basename='notifications')
urlpatterns = [
    path('', include(router.urls)),


]
