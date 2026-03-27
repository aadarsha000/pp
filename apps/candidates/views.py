from django.shortcuts import render

from candidates.models import Application, Candidate, Notification, Document
from candidates.serializers import (
    ApplicationSerializer,
    ApplicationStageUpdateSerializer,
    CandidateSerializer,
    ApplicationCreateSerializer,
    NotificationSerializer,
    DocumentSerializer
)
from candidates.filters import ApplicationFilter
from users.permissions import IsRecruiterOrAdmin
from rest_framework import viewsets, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.decorators import action

# Create your views here.
class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [IsRecruiterOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ApplicationFilter
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        if 'job_pk' in self.kwargs:
            return Application.objects.filter(job_id=self.kwargs['job_pk'])
        return Application.objects.select_related('candidate', 'job').prefetch_related('logs')


    def get_serializer_class(self):
        if self.action == 'create':
            return ApplicationCreateSerializer
        if self.action == 'update_stage':
            return ApplicationStageUpdateSerializer
        return ApplicationSerializer

    @action(detail=True, methods=['patch'])
    def update_stage(self, request, pk=None):
        application = self.get_object()
        serializer = self.get_serializer(application, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='documents')
    def upload_document(self, request, pk=None):
        application = self.get_object()
        serializer = DocumentSerializer(
            data=request.data,
            context={"request": request, "application": application}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(application=application, uploaded_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='documents/(?P<doc_id>[^/.]+)')
    def delete_document(self, request, pk=None, doc_id=None):
        application = self.get_object()
        try:
            document = application.documents.get(id=doc_id)
        except Document.DoesNotExist:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        is_hr_admin = request.user.role == 'HR_Admin'
        if not is_hr_admin and document.uploaded_by_id != request.user.id:
            return Response(
                {"detail": "Only HR Admin or the uploader can delete this document."},
                status=status.HTTP_403_FORBIDDEN
            )

        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)





class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.prefetch_related('applications')
    serializer_class = CandidateSerializer
    permission_classes = [IsRecruiterOrAdmin]
    http_method_names = ['get', 'post', 'patch', 'delete']

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsRecruiterOrAdmin]
    http_method_names = ['get', 'patch']

    @action(detail=True, methods=['patch'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True 
        notification.save()
        return Response({"id": notification.id, "is_read": notification.is_read})