from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound

from users.permissions import IsRecruiterOrAdmin
from users.models import Role
from .models import JobPosting, Department, Status
from .serializers import (
    DepartmentSerializer,
    JobPostingListSerializer,
    JobPostingListSerializerV2,
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
    serializer_class = JobPostingSerializer
    permission_classes = [IsRecruiterOrAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = JobPostingFilter
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'salary_min', 'salary_max', 'deadline', 'status']
    ordering = '-created_at'
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_serializer_class(self):
        if self.action == 'list':
            if getattr(self.request, "version", None) == "v2":
                return JobPostingListSerializerV2
            return JobPostingListSerializer
        return JobPostingDetailSerializer


    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(summary="Publish Job", description="Moves a Draft job to Open. HR Admin only.")
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        job = self.get_object()
        if request.user.role != Role.ADMIN:
            raise PermissionDenied("Only HR Admin can publish.")
        if job.status != Status.DRAFT:
            raise ValidationError("Only Draft jobs can be published.")

        job.status = Status.OPEN
        job.save()
        return Response({"status": "Job published"})


    @extend_schema(summary="Close Job", description="Moves an Open job to Closed. HR Admin or owning Recruiter.")
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        job = self.get_object()
        is_hr_admin = request.user.role == Role.ADMIN
        is_owner_recruiter = request.user.role == Role.RECRUITER and job.created_by_id == request.user.id
        if not (is_hr_admin or is_owner_recruiter):
            raise PermissionDenied("Only HR Admin or owning Recruiter can close this job.")
        if job.status != Status.OPEN:
            raise ValidationError("Only Open jobs can be closed.")

        job.status = Status.CLOSED
        job.save()
        return Response({"status": "Job closed"})

    @extend_schema(summary="Bulk Status Update", description="Update status for multiple jobs by ID. Validates IDs and caller permissions.")
    @action(detail=False, methods=['post'], url_path='bulk-status-update')
    def bulk_status_update(self, request):
        ids = request.data.get('ids', [])
        new_status = request.data.get('status')

        if not isinstance(ids, list) or not ids:
            raise ValidationError({"ids": ["ids must be a non-empty list."]})

        if new_status not in Status.values:
            raise ValidationError({"status": ["Invalid status"]})

        jobs = JobPosting.objects.filter(id__in=ids)
        
        if jobs.count() != len(ids):
            raise NotFound("Some IDs were not found.")

        for job in jobs:
            if self.request.user.role != Role.ADMIN and job.created_by != self.request.user:
                raise PermissionDenied(f"No permission for job ID {job.id}")

        jobs.update(status=new_status)
        return Response({"message": f"Updated {jobs.count()} jobs to {new_status}"})


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsRecruiterOrAdmin]
    http_method_names = ['get', 'post', 'patch', 'delete']