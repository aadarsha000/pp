import django_filters
from .models import Application

class ApplicationFilter(django_filters.FilterSet):
    class Meta:
        model = Application
        # fields = ['stage', 'job', 'candidate', 'assigned_recruiter', 'created_at']
        fields = ['stage', 'job', 'candidate', 'created_at']