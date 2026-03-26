from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.jobs.views import JobPostingViewSet

router = DefaultRouter()

router.register(r'jobs', JobPostingViewSet, basename='jobs')


urlpatterns = [
    path('', include(router.urls)),

]
