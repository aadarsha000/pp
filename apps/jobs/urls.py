from django.urls import path, include
from rest_framework.routers import DefaultRouter

from jobs.views import JobPostingViewSet, DepartmentViewSet

router = DefaultRouter()

router.register(r'jobs', JobPostingViewSet, basename='jobs')
router.register(r'departments', DepartmentViewSet, basename='departments')


urlpatterns = [
    path('', include(router.urls)),

]
