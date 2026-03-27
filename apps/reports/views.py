from django.shortcuts import render

from django.db.models import Count, Avg, F, Q, Case, When
from django.utils import timezone
from rest_framework import viewsets, response, renderers
from rest_framework.decorators import action
from reports.renderer import CSVRenderer
from jobs.models import Department
from users.models import CustomUser
from users.permissions import IsHRAdmin, IsRecruiterOrAdmin
from candidates.models import Application, Stage
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class ReportingViewSet(viewsets.ViewSet):
    permission_classes = [IsHRAdmin | IsRecruiterOrAdmin]
    renderer_classes = [renderers.JSONRenderer, CSVRenderer]


    @method_decorator(cache_page(60 * 10, key_prefix="reports"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


    @action(detail=False, methods=['get'], url_path='pipeline-funnel')
    def pipeline_funnel(self, request):
        job_id = request.query_params.get('job')
        # Single query annotated with counts for every stage
        stats = Application.objects.filter(job_id=job_id).aggregate(
            applied=Count('id', filter=Q(stage=Stage.APPLIED)),
            screening=Count('id', filter=Q(stage=Stage.SCREENING)),
            technical=Count('id', filter=Q(stage=Stage.TECHNICAL)),
            hr=Count('id', filter=Q(stage=Stage.HR)),
            offer=Count('id', filter=Q(stage=Stage.OFFER)),
            hired=Count('id', filter=Q(stage=Stage.HIRED)),
            rejected=Count('id', filter=Q(stage=Stage.REJECTED)),
        )
        return response.Response(stats)

    @action(detail=False, methods=['get'], url_path='time-to-hire')
    def time_to_hire(self):
        # Average days from Applied (created_at) to Hired (updated_at)
        stats = Department.objects.annotate(
            avg_days=Avg(
                F('jobs__applications__updated_at') - F('jobs__applications__created_at'),
                filter=Q(jobs__applications__stage=Stage.HIRED)
            )
        ).values('name', 'avg_days')
        return response.Response(stats)

    @action(detail=False, methods=['get'], url_path='interviewer-workload')
    def interviewer_workload(self, request):
        month_start = timezone.now().replace(day=1, hour=0, minute=0)
        stats = CustomUser.objects.filter(role='Interviewer').annotate(
            assigned=Count('interview', filter=Q(interview__scheduled_at__gte=month_start)),
            completed=Count('interview', filter=Q(interview__status='Completed', interview__scheduled_at__gte=month_start)),
            pending=Count('interview', filter=Q(interview__status='Scheduled', interview__scheduled_at__gte=month_start)),
        ).values('username', 'assigned', 'completed', 'pending')
        return response.Response(stats)
