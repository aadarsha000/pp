from django.shortcuts import render

from django.db.models import Count, Avg, F, Q, Case, When, FloatField, Value, ExpressionWrapper
from django.core.cache import cache
from django.utils import timezone
from rest_framework import viewsets, response, renderers
from rest_framework.decorators import action
from reports.renderer import CSVRenderer
from drf_spectacular.utils import extend_schema
from jobs.models import Department
from users.models import CustomUser
from users.models import Role
from users.permissions import IsHRAdmin, IsRecruiterOrAdmin
from candidates.models import Application, Stage
from rest_framework.exceptions import ValidationError

from jobs.models import Status as JobStatus
from interviews.models import InterviewStatus


class ReportingViewSet(viewsets.ViewSet):
    permission_classes = [IsHRAdmin | IsRecruiterOrAdmin]
    renderer_classes = [renderers.JSONRenderer, CSVRenderer]

    REPORTS_CACHE_TTL_SECONDS = 60 * 10

    def _cache_version(self):
        return cache.get("reports_cache_version", "0")

    def _cache_key(self, action_name, request, extra=""):
        query = request.query_params.urlencode()
        return f"reports:{self._cache_version()}:{action_name}:{extra}:{query}"


    @extend_schema(summary="Pipeline Funnel", description="Returns counts of applications at each pipeline stage for a given job.")
    @action(detail=False, methods=['get'], url_path='pipeline-funnel')
    def pipeline_funnel(self, request):
        job_id = request.query_params.get('job')
        if not job_id:
            raise ValidationError({"job": ["This query param is required."]})

        cache_key = self._cache_key("pipeline_funnel", request, extra=f"job={job_id}")
        cached = cache.get(cache_key)
        if cached is not None:
            return response.Response(cached)

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
        cache.set(cache_key, stats, timeout=self.REPORTS_CACHE_TTL_SECONDS)
        return response.Response(stats)

    @extend_schema(summary="Time To Hire", description="Returns the average number of days from Applied to Hired, broken down by department.")
    @action(detail=False, methods=['get'], url_path='time-to-hire')
    def time_to_hire(self, request):
        cache_key = self._cache_key("time_to_hire", request)
        cached = cache.get(cache_key)
        if cached is not None:
            return response.Response(cached)

        # Average days from Applied (created_at) to Hired (updated_at)
        stats_qs = Department.objects.annotate(
            avg_days=Avg(
                F('jobs__job_applications__updated_at') - F('jobs__job_applications__created_at'),
                filter=Q(jobs__job_applications__stage=Stage.HIRED),
            )
        ).values('name', 'avg_days')
        stats = list(stats_qs)
        cache.set(cache_key, stats, timeout=self.REPORTS_CACHE_TTL_SECONDS)
        return response.Response(stats)

    @extend_schema(summary="Interviewer Workload", description="Returns per-interviewer assigned, completed, and pending interviews for the current month.")
    @action(detail=False, methods=['get'], url_path='interviewer-workload')
    def interviewer_workload(self, request):
        month_start = timezone.now().replace(day=1, hour=0, minute=0)
        cache_key = self._cache_key("interviewer_workload", request, extra=month_start.strftime("%Y-%m"))
        cached = cache.get(cache_key)
        if cached is not None:
            return response.Response(cached)

        # related_name from Interview.interviewers M2M defaults to `interview_set` on User
        stats = CustomUser.objects.filter(role=Role.INTERVIEWER).annotate(
            assigned_interviews=Count('interview_set', filter=Q(interview_set__scheduled_at__gte=month_start)),
            completed_interviews=Count(
                'interview_set',
                filter=Q(
                    interview_set__status=InterviewStatus.COMPLETED,
                    interview_set__scheduled_at__gte=month_start,
                ),
            ),
            pending_interviews=Count(
                'interview_set',
                filter=Q(
                    interview_set__status=InterviewStatus.SCHEDULED,
                    interview_set__scheduled_at__gte=month_start,
                ),
            ),
        ).values('username', 'assigned_interviews', 'completed_interviews', 'pending_interviews')

        cache.set(cache_key, list(stats), timeout=self.REPORTS_CACHE_TTL_SECONDS)
        return response.Response(stats)

    @extend_schema(summary="Department Breakdown", description="Returns open jobs, total applications, and hire rate per department.")
    @action(detail=False, methods=['get'], url_path='department-breakdown')
    def department_breakdown(self, request):
        cache_key = self._cache_key("department_breakdown", request)
        cached = cache.get(cache_key)
        if cached is not None:
            return response.Response(cached)

        departments = Department.objects.annotate(
            open_jobs=Count('jobs', filter=Q(jobs__status=JobStatus.OPEN)),
            total_applications=Count('jobs__job_applications'),
            hired_applications=Count(
                'jobs__job_applications',
                filter=Q(jobs__job_applications__stage=Stage.HIRED),
            ),
        ).annotate(
            hire_rate=ExpressionWrapper(
                Case(
                    When(total_applications=0, then=Value(0.0)),
                    default=(F('hired_applications') * Value(100.0)) / F('total_applications'),
                    output_field=FloatField(),
                ),
                output_field=FloatField(),
            )
        ).values('name', 'open_jobs', 'total_applications', 'hire_rate')

        cache.set(cache_key, list(departments), timeout=self.REPORTS_CACHE_TTL_SECONDS)
        return response.Response(departments)
