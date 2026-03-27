from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.response import Response

from users.permissions import IsRecruiterOrAdmin
from users.models import Role
from .models import JobPosting, Department, Status
from .serializers import DepartmentSerializer, JobPostingListSerializer, JobPostingDetailSerializer, JobPostingSerializer
from .filters import JobPostingFilter
from rest_framework.decorators import action


class JobPostingViewSet(viewsets.ModelViewSet):
    queryset = JobPosting.objects.select_related('department').annotate(
            applicant_count=Count('job_applications') 
        )
    serializer_class = JobPostingSerializer
    permission_classes = [IsRecruiterOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = JobPostingFilter
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_serializer_class(self):
        if self.action == 'list':
            return JobPostingListSerializer
        return JobPostingDetailSerializer


    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        job = self.get_object()
        if request.user.role != Role.ADMIN:
            return Response({"error": "Only HR Admin can publish."}, status=status.HTTP_403_FORBIDDEN)
        if job.status != Status.DRAFT:
            return Response(
                {"error": "Only Draft jobs can be published."},
                status=status.HTTP_400_BAD_REQUEST
            )

        job.status = Status.OPEN
        job.save()
        return Response({"status": "Job published"})


    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        job = self.get_object()
        is_hr_admin = request.user.role == Role.ADMIN
        is_owner_recruiter = request.user.role == Role.RECRUITER and job.created_by_id == request.user.id
        if not (is_hr_admin or is_owner_recruiter):
            return Response(
                {"error": "Only HR Admin or owning Recruiter can close this job."},
                status=status.HTTP_403_FORBIDDEN
            )
        if job.status != Status.OPEN:
            return Response(
                {"error": "Only Open jobs can be closed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        job.status = Status.CLOSED
        job.save()
        return Response({"status": "Job closed"})

    @action(detail=False, methods=['post'], url_path='bulk-status-update')
    def bulk_status_update(self, request):
        ids = request.data.get('ids', [])
        new_status = request.data.get('status')

        if not isinstance(ids, list) or not ids:
            return Response({"error": "ids must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)

        if new_status not in Status.values:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        jobs = JobPosting.objects.filter(id__in=ids)
        
        if jobs.count() != len(ids):
            return Response({"error": "Some IDs were not found"}, status=status.HTTP_404_NOT_FOUND)

        for job in jobs:
            if self.request.user.role != Role.ADMIN and job.created_by != self.request.user:
                return Response({"error": f"No permission for job ID {job.id}"}, status=status.HTTP_403_FORBIDDEN)

        jobs.update(status=new_status)
        return Response({"message": f"Updated {jobs.count()} jobs to {new_status}"})


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsRecruiterOrAdmin]
    http_method_names = ['get', 'post', 'patch', 'delete']