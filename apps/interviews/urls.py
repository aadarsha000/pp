from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InterviewViewSet, FeedbackRubricViewSet

router = DefaultRouter()
router.register(r'interviews', InterviewViewSet, basename='interviews') 
router.register(r'feedback-rubrics', FeedbackRubricViewSet, basename='feedback-rubrics')

urlpatterns = [
    path('', include(router.urls)),
]   