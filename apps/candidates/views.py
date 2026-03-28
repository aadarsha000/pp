from django.shortcuts import render
from rest_framework.permissions import AllowAny

from candidates.models import Application, ApplicationStageLog, Candidate, Document, Stage
from candidates.serializers import (
    ApplicationSerializer,
    ApplicationStageUpdateSerializer,
    CandidateSerializer,
    ApplicationCreateSerializer,
    DocumentSerializer,
    ApplicationStageLogSerializer
)
from candidates.filters import ApplicationFilter, CandidateFilter
from users.permissions import IsRecruiterOrAdmin
from users.models import Role
from rest_framework import viewsets, status
from django_filters.rest_framework import DjangoFilterBackend
from config.utils import api_response
from rest_framework.decorators import action
from candidates.throttles import ApplicationsPostIPThrottle
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.exceptions import NotFound, PermissionDenied
from django.db.models import OuterRef, Subquery
from drf_spectacular.utils import extend_schema
from notification.tasks import task_notify_new_application, task_notify_stage_changed

# Create your views here.
class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [IsRecruiterOrAdmin]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ApplicationFilter
    ordering_fields = ['created_at', 'updated_at', 'stage']
    ordering = '-created_at'
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_throttles(self):
        throttles = super().get_throttles()
        if self.action == 'create' and self.request.method == 'POST':
            throttles.append(ApplicationsPostIPThrottle())
        return throttles

    def get_queryset(self):
        if 'job_pk' in self.kwargs:
            return Application.objects.filter(job_id=self.kwargs['job_pk'])
        return Application.objects.select_related('candidate', 'job').prefetch_related('logs')


    def get_serializer_class(self):
        if self.action == 'create':
            return ApplicationCreateSerializer
        if self.action == 'stage':
            return ApplicationStageUpdateSerializer
        return ApplicationSerializer

    def perform_create(self, serializer):
        application = serializer.save()
        task_notify_new_application.delay(application.id)

    @extend_schema(summary="Update Application Stage", description="Advance application stage sequentially and logs the transition.")
    @action(detail=True, methods=['patch'], url_path='stage', permission_classes=[IsRecruiterOrAdmin])
    def stage(self, request, pk=None):
        application = self.get_object()
        from_stage = application.stage
        serializer = self.get_serializer(application, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        new_stage = serializer.instance.stage
        # Trigger notification asynchronously
        if from_stage != new_stage and new_stage == Stage.OFFER and application.job.created_by_id:
            task_notify_stage_changed.delay(
                application_id=application.id,
                from_stage=from_stage,
                to_stage=new_stage
            )
        return api_response("Stage updated", status.HTTP_200_OK, data=serializer.data)

    @extend_schema(summary="Upload Application Document", description="Upload a document to an application with MIME/size and document-count validation.")
    @action(detail=True, methods=['post'], url_path='documents')
    def upload_document(self, request, pk=None):
        application = self.get_object()
        serializer = DocumentSerializer(
            data=request.data,
            context={"request": request, "application": application}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(application=application, uploaded_by=request.user)
        return api_response(
            "Document uploaded",
            status.HTTP_201_CREATED,
            data=serializer.data,
        )

    @extend_schema(summary="Delete Application Document", description="Delete an application document. Allowed for HR Admin or the uploader.")
    @action(detail=True, methods=['delete'], url_path='documents/(?P<doc_id>[^/.]+)')
    def delete_document(self, request, pk=None, doc_id=None):
        application = self.get_object()
        try:
            document = application.documents.get(id=doc_id)
        except Document.DoesNotExist:
            raise NotFound("Document not found.")

        is_hr_admin = request.user.role == Role.ADMIN
        if not is_hr_admin and document.uploaded_by_id != request.user.id:
            raise PermissionDenied("Only HR Admin or the uploader can delete this document.")

        document.delete()
        return api_response("Document deleted", status.HTTP_200_OK)


class ApplicationStageLogViewSet(viewsets.ModelViewSet):
    queryset = ApplicationStageLog.objects.all()
    # permission_classes = [AllowAny]
    serializer_class = ApplicationStageLogSerializer
    permission_classes = [IsRecruiterOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['application']
    http_method_names = ['get']


class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
    permission_classes = [IsRecruiterOrAdmin]
    http_method_names = ['get', 'post', 'patch', 'delete']

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CandidateFilter
    search_fields = ['full_name', 'email']
    ordering_fields = ['created_at', 'full_name', 'email', 'source']
    ordering = '-created_at'

    def get_queryset(self):
        latest_application = Application.objects.filter(candidate=OuterRef('pk')).order_by('-created_at', '-id')
        return (
            Candidate.objects.annotate(
                latest_stage=Subquery(latest_application.values('stage')[:1]),
                latest_job_id=Subquery(latest_application.values('job_id')[:1]),
            )
            .prefetch_related('candidate_applications')
        )
