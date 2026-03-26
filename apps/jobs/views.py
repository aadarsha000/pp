from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.response import Response

from apps.users.permissions import IsRecruiterOrAdmin
from .models import JobPosting
from .serializers import JobPostingListSerializer, JobPostingDetailSerializer, JobPostingSerializer
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

    def get_serializer_class(self):
        if self.action == 'list':
            return JobPostingListSerializer
        return JobPostingDetailSerializer


    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        job = self.get_object()
        if request.user.role != 'HR_Admin':
            return Response({"error": "Only HR Admin can publish."}, status=status.HTTP_403_FORBIDDEN)
        
        job.status = JobPosting.Status.OPEN
        job.save()
        return Response({"status": "Job published"})


    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        job = self.get_object() 
        job.status = JobPosting.Status.CLOSED
        job.save()
        return Response({"status": "Job closed"})

    @action(detail=False, methods=['post'], url_path='bulk-status-update')
    def bulk_status_update(self, request):
        ids = request.data.get('ids', [])
        new_status = request.data.get('status')
        
        if new_status not in JobPosting.Status.values:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        jobs = JobPosting.objects.filter(id__in=ids)
        
        if jobs.count() != len(ids):
            return Response({"error": "Some IDs were not found"}, status=status.HTTP_404_NOT_FOUND)

        for job in jobs:
            if not self.request.user.role == 'HR_Admin' and job.created_by != self.request.user:
                return Response({"error": f"No permission for job ID {job.id}"}, status=status.HTTP_403_FORBIDDEN)

        jobs.update(status=new_status)
        return Response({"message": f"Updated {jobs.count()} jobs to {new_status}"})
