import django_filters
from .models import Application

class ApplicationFilter(django_filters.FilterSet):
    assigned_recruiter = django_filters.NumberFilter(field_name='job__created_by_id')
    created_at_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_at_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Application
        fields = ['stage', 'job', 'candidate', 'assigned_recruiter', 'created_at_after', 'created_at_before']