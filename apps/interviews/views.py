from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Avg
from .models import Interview, InterviewStatus, FeedbackScore
from .serializers import InterviewSerializer, InterviewFeedbackSerializer
from users.permissions import IsAssignedInterviewer
from django.utils import timezone
from users.models import Role


class InterviewViewSet(viewsets.ModelViewSet):
    queryset = Interview.objects.select_related('application__candidate').prefetch_related('interviewers')
    serializer_class = InterviewSerializer

    @action(detail=False, methods=['get'], url_path='my-schedule')
    def my_schedule(self, request):
        if request.user.role != Role.INTERVIEWER:
            return Response(
                {"detail": "Only interviewers can access my-schedule."},
                status=status.HTTP_403_FORBIDDEN
            )
        interviews = Interview.objects.filter(
            interviewers=request.user,
            scheduled_at__gte=timezone.now(),
            status=InterviewStatus.SCHEDULED,
        ).select_related('application__candidate').order_by('scheduled_at')
        data = [
            {
                "id": interview.id,
                "scheduled_at": interview.scheduled_at,
                "duration_minutes": interview.duration_minutes,
                "location_or_link": interview.location_or_link,
                "interview_type": interview.interview_type,
                "status": interview.status,
                "application": {
                    "id": interview.application.id,
                    "stage": interview.application.stage,
                    "candidate": {
                        "id": interview.application.candidate.id,
                        "full_name": interview.application.candidate.full_name,
                        "email": interview.application.candidate.email,
                    },
                },
            }
            for interview in interviews
        ]
        return Response(data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        interview = self.get_object()
        if interview.status == InterviewStatus.COMPLETED:
            return Response({"error": "Cannot cancel a completed interview."}, status=status.HTTP_400_BAD_REQUEST)
        
        interview.status = InterviewStatus.CANCELLED
        interview.save()
        return Response({"status": "Interview cancelled"})


    @action(detail=True, methods=['post'], permission_classes=[IsAssignedInterviewer])
    def complete(self, request, pk=None):
        interview = self.get_object()
        if interview.status == InterviewStatus.CANCELLED:
            return Response({"error": "Cannot complete a cancelled interview."}, status=status.HTTP_400_BAD_REQUEST)
        interview.status = InterviewStatus.COMPLETED
        interview.save()
        return Response({"status": "Interview marked as completed"})


    @action(detail=True, methods=['post'], url_path='feedback', permission_classes=[IsAssignedInterviewer])
    def feedback(self, request, pk=None):
        interview = self.get_object()
        serializer = InterviewFeedbackSerializer(
            data=request.data, 
            context={'request': request, 'interview': interview}
        )
        serializer.is_valid(raise_exception=True)
        feedback = serializer.save()
        return Response(
            InterviewFeedbackSerializer(feedback).data,
            status=status.HTTP_201_CREATED
        )


    @action(detail=True, methods=['get'], url_path='feedback')
    def list_feedback(self, request, pk=None):
        interview = self.get_object()
        
        feedbacks = interview.feedbacks.prefetch_related('scores', 'scores__rubric')
        
        rubric_averages = (
            FeedbackScore.objects.filter(feedback__interview=interview)
            .values('rubric_id', 'rubric__label')
            .annotate(average_score=Avg('score'))
            .order_by('rubric_id')
        )

        return Response({
            "individual_feedback": InterviewFeedbackSerializer(feedbacks, many=True).data,
            "rubric_averages": list(rubric_averages),
        })
