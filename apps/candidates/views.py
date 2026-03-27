from django.shortcuts import render

from candidates.models import Application, Candidate
from candidates.serializers import ApplicationSerializer, ApplicationStageUpdateSerializer, CandidateSerializer, ApplicationCreateSerializer
from candidates.filters import ApplicationFilter
from users.permissions import IsRecruiterOrAdmin
from rest_framework import viewsets
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





class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.prefetch_related('applications')
    serializer_class = CandidateSerializer
    permission_classes = [IsRecruiterOrAdmin]
    http_method_names = ['get', 'post', 'patch', 'delete']

