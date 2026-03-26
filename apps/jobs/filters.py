import django_filters
from .models import JobPosting

class JobPostingFilter(django_filters.FilterSet):
    deadline_before = django_filters.DateTimeFilter(field_name="deadline", lookup_expr='lte')
    deadline_after = django_filters.DateTimeFilter(field_name="deadline", lookup_expr='gte')
    salary_min_gte = django_filters.NumberFilter(field_name="salary_min", lookup_expr='gte')
    salary_max_lte = django_filters.NumberFilter(field_name="salary_max", lookup_expr='lte')

    class Meta:
        model = JobPosting
        fields = ['status', 'department', 'employment_type']
