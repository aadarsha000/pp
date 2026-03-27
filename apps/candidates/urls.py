from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApplicationViewSet, CandidateViewSet

router = DefaultRouter()
router.register(r'applications', ApplicationViewSet, basename='applications')
# router.register(r'stages', StageViewSet, basename='stages')
# router.register(r'documents', DocumentViewSet, basename='documents')
router.register(r'candidates', CandidateViewSet, basename='candidates')
urlpatterns = [
    path('', include(router.urls)),
    path('jobs/<int:job_pk>/applications/', ApplicationViewSet.as_view({'get': 'list'}), name='job-applications-list'),


]
