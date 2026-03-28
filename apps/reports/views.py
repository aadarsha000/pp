from django.shortcuts import render

from django.db.models import (
    Count,
    Avg,
    F,
    Q,
    Case,
    When,
    FloatField,
    Value,
    ExpressionWrapper,
    DurationField,
)
from django.core.cache import cache
from django.utils import timezone
from rest_framework import renderers, status, viewsets
from config.utils import api_response
from rest_framework.decorators import action
from reports.renderer import CSVRenderer
from drf_spectacular.utils import extend_schema
from jobs.models import Department
from users.models import CustomUser
from users.models import Role
from users.permissions import IsHRAdmin, IsRecruiterOrAdmin
from candidates.models import Application, Stage, ApplicationStageLog
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

    @extend_schema(
        summary="Pipeline Funnel",
        description="Returns counts of applications at each pipeline stage for a given job.",
    )
    @action(detail=False, methods=["get"], url_path="pipeline-funnel")
    def pipeline_funnel(self, request):
        job_id = request.query_params.get("job")
        if not job_id:
            raise ValidationError({"job": ["This query param is required."]})

        cache_key = self._cache_key("pipeline_funnel", request, extra=f"job={job_id}")
        cached = cache.get(cache_key)
        if cached is not None:
            return api_response("Success", status.HTTP_200_OK, data=cached)

        # Single query annotated with counts for every stage
        stats = Application.objects.filter(job_id=job_id).aggregate(
            applied=Count("id", filter=Q(stage=Stage.APPLIED)),
            screening=Count("id", filter=Q(stage=Stage.SCREENING)),
            technical=Count("id", filter=Q(stage=Stage.TECHNICAL)),
            hr=Count("id", filter=Q(stage=Stage.HR)),
            offer=Count("id", filter=Q(stage=Stage.OFFER)),
            hired=Count("id", filter=Q(stage=Stage.HIRED)),
            rejected=Count("id", filter=Q(stage=Stage.REJECTED)),
        )
        cache.set(cache_key, stats, timeout=self.REPORTS_CACHE_TTL_SECONDS)
        return api_response("Success", status.HTTP_200_OK, data=stats)

    @extend_schema(
        summary="Time To Hire",
        description="Returns the average number of days from Applied to Hired, broken down by department.",
    )
    @action(detail=False, methods=["get"], url_path="time-to-hire")
    def time_to_hire(self, request):
        cache_key = self._cache_key("time_to_hire", request)
        cached = cache.get(cache_key)
        if cached is not None:
            return api_response("Success", status.HTTP_200_OK, data=cached)

        # Average days from Applied (created_at) to Hired (updated_at)
        qs = (
            ApplicationStageLog.objects.filter(to_stage=Stage.HIRED)
            .annotate(
                days_to_hire=ExpressionWrapper(
                    F("changed_at") - F("application__created_at"),
                    output_field=DurationField(),
                )
            )
            .values("application__job__department__name")
            .annotate(avg_duration=Avg("days_to_hire"))
            .order_by("application__job__department__name")
        )

        stats = [
            {
                "department_name": row["application__job__department__name"],
                "avg_days": (
                    round(row["avg_duration"].total_seconds() / 86400, 1)
                    if row["avg_duration"] is not None
                    else None
                ),
            }
            for row in qs
        ]
        cache.set(cache_key, stats, timeout=self.REPORTS_CACHE_TTL_SECONDS)
        return api_response("Success", status.HTTP_200_OK, data=stats)

    @extend_schema(
        summary="Interviewer Workload",
        description="Returns per-interviewer assigned, completed, and pending interviews for the current month.",
    )
    @action(detail=False, methods=["get"], url_path="interviewer-workload")
    def interviewer_workload(self, request):
        month_start = timezone.now().replace(day=1, hour=0, minute=0)
        cache_key = self._cache_key(
            "interviewer_workload", request, extra=month_start.strftime("%Y-%m")
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return api_response("Success", status.HTTP_200_OK, data=cached)

        # related_name from Interview.interviewers M2M defaults to `interview_set` on User
        stats = (
            CustomUser.objects.filter(role=Role.INTERVIEWER)
            .annotate(
                assigned_interviews=Count(
                    "interview_set",
                    filter=Q(interview_set__scheduled_at__gte=month_start),
                ),
                completed_interviews=Count(
                    "interview_set",
                    filter=Q(
                        interview_set__status=InterviewStatus.COMPLETED,
                        interview_set__scheduled_at__gte=month_start,
                    ),
                ),
                pending_interviews=Count(
                    "interview_set",
                    filter=Q(
                        interview_set__status=InterviewStatus.SCHEDULED,
                        interview_set__scheduled_at__gte=month_start,
                    ),
                ),
            )
            .values(
                "username",
                "assigned_interviews",
                "completed_interviews",
                "pending_interviews",
            )
        )

        cache.set(cache_key, list(stats), timeout=self.REPORTS_CACHE_TTL_SECONDS)
        return api_response("Success", status.HTTP_200_OK, data=list(stats))

    @extend_schema(
        summary="Department Breakdown",
        description="Returns open jobs, total applications, and hire rate per department.",
    )
    @action(detail=False, methods=["get"], url_path="department-breakdown")
    def department_breakdown(self, request):
        cache_key = self._cache_key("department_breakdown", request)
        cached = cache.get(cache_key)
        if cached is not None:
            return api_response("Success", status.HTTP_200_OK, data=cached)

        departments = (
            Department.objects.annotate(
                open_jobs=Count("jobs", filter=Q(jobs__status=JobStatus.OPEN)),
                total_applications=Count("jobs__job_applications"),
                hired_applications=Count(
                    "jobs__job_applications",
                    filter=Q(jobs__job_applications__stage=Stage.HIRED),
                ),
            )
            .annotate(
                hire_rate=ExpressionWrapper(
                    Case(
                        When(total_applications=0, then=Value(0.0)),
                        default=(F("hired_applications") * Value(100.0))
                        / F("total_applications"),
                        output_field=FloatField(),
                    ),
                    output_field=FloatField(),
                )
            )
            .values("name", "open_jobs", "total_applications", "hire_rate")
        )

        cache.set(cache_key, list(departments), timeout=self.REPORTS_CACHE_TTL_SECONDS)
        return api_response("Success", status.HTTP_200_OK, data=list(departments))
