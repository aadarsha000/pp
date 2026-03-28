from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from config.utils import api_response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound

from users.permissions import IsHRAdmin, IsRecruiterOrAdmin
from users.models import Role
from .models import JobPosting, Department, Status
from .serializers import (
    BulkJobStatusUpdateSerializer,
    DepartmentSerializer,
    JobPostingListSerializer,
    JobPostingDetailSerializer,
    JobPostingSerializer,
)
from .filters import JobPostingFilter
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema


class JobPostingViewSet(viewsets.ModelViewSet):
    queryset = JobPosting.objects.select_related('department').annotate(
            applicant_count=Count('job_applications') 
        )
    permission_classes = [IsRecruiterOrAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = JobPostingFilter
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'salary_min', 'salary_max', 'deadline', 'status']
    ordering = '-created_at'
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_serializer_class(self):
        if self.action == "bulk_status_update":
            return BulkJobStatusUpdateSerializer
        if self.action == "list":
            return JobPostingListSerializer
        if self.action == "retrieve":
            return JobPostingDetailSerializer
        return JobPostingSerializer


    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(
        summary="Publish Job", 
        description="Moves a Draft job to Open. HR Admin only.", 
        request=None,
        )
    @action(detail=True, methods=['post'], serializer_class=None, permission_classes=[IsHRAdmin] )
    def publish(self, request, pk=None):
        job = self.get_object()
        if job.status != Status.DRAFT:
            raise ValidationError("Only Draft jobs can be published.")

        job.status = Status.OPEN
        job.save()
        return api_response("Job published", status.HTTP_200_OK)


    @extend_schema(
        summary="Close Job", 
        description="Moves an Open job to Closed. HR Admin or owning Recruiter.", 
        request=None
        )
    @action(detail=True, methods=['post'], serializer_class=None, permission_classes=[IsRecruiterOrAdmin])
    def close(self, request, pk=None):
        job = self.get_object()
        if job.status != Status.OPEN:
            raise ValidationError("Only Open jobs can be closed.")

        job.status = Status.CLOSED
        job.save()
        return api_response("Job closed", status.HTTP_200_OK)

    @extend_schema(
        summary="Bulk Status Update",
        description="Update status for multiple jobs by ID. Validates IDs and caller permissions.",
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-status-update",
    )
    def bulk_status_update(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]
        new_status = serializer.validated_data["status"]

        jobs = JobPosting.objects.filter(id__in=ids)
        found_ids = set(jobs.values_list("id", flat=True))
        missing = [pk for pk in ids if pk not in found_ids]
        if missing:
            raise NotFound(f"Jobs not found for IDs: {missing}.")

        user = request.user
        for job in jobs:
            if user.role != Role.ADMIN and job.created_by_id != user.id:
                raise PermissionDenied(f"No permission for job ID {job.id}.")

        updated = jobs.update(status=new_status)
        return api_response(
            f"Updated {updated} job(s) to {new_status}.",
            status.HTTP_200_OK,
            data={"updated_count": updated, "job_ids": ids},
        )


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsRecruiterOrAdmin]
    http_method_names = ['get', 'post', 'patch', 'delete']