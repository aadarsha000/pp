import django_filters
from .models import Application, Candidate, Stage

class ApplicationFilter(django_filters.FilterSet):
    assigned_recruiter = django_filters.NumberFilter(field_name='job__created_by_id')
    created_at_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_at_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Application
        fields = ['stage', 'job', 'candidate', 'assigned_recruiter', 'created_at_after', 'created_at_before']


class CandidateFilter(django_filters.FilterSet):
    stage = django_filters.ChoiceFilter(field_name="latest_stage", choices=Stage.choices)
    job = django_filters.NumberFilter(field_name="latest_job_id")
    source = django_filters.ChoiceFilter(
        field_name="source",
        choices=Candidate._meta.get_field("source").choices,
    )
    created_at_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    # Friendly aliases for date range filtering
    date_from = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    date_to = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Candidate
        fields = ['source', 'stage', 'job', 'created_at_after', 'created_at_before', 'date_from', 'date_to']