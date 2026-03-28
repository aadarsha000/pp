from rest_framework import viewsets, status
from config.utils import api_response
from rest_framework.decorators import action
from django.db.models import Avg
from .models import Interview, InterviewStatus, FeedbackScore, FeedbackRubric   
from .serializers import InterviewSerializer, InterviewFeedbackSerializer, FeedbackRubricSerializer
from users.permissions import IsAssignedInterviewer, IsRecruiterOrAdmin
from django.utils import timezone
from users.models import Role
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import PermissionDenied, ValidationError


class InterviewViewSet(viewsets.ModelViewSet):
    queryset = Interview.objects.select_related(
        "application__candidate"
    ).prefetch_related("interviewers")
    serializer_class = InterviewSerializer
    permission_classes = [IsRecruiterOrAdmin]

    @extend_schema(
        summary="My Schedule",
        description="Returns upcoming scheduled interviews for the authenticated interviewer.",
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="my-schedule",
        permission_classes=[IsAssignedInterviewer],
    )
    def my_schedule(self, request):
        if request.user.role != Role.INTERVIEWER:
            raise PermissionDenied("Only interviewers can access my-schedule.")
        interviews = (
            Interview.objects.filter(
                interviewers=request.user,
                scheduled_at__gte=timezone.now(),
                status=InterviewStatus.SCHEDULED,
            )
            .select_related("application__candidate")
            .order_by("scheduled_at")
        )
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
        return api_response("Success", status.HTTP_200_OK, data=data)

    @extend_schema(
        summary="Cancel Interview",
        description="Cancels an interview. Completed interviews cannot be cancelled.",
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsRecruiterOrAdmin],
    )
    def cancel(self, request, pk=None):
        interview = self.get_object()
        if interview.status == InterviewStatus.COMPLETED:
            raise ValidationError("Cannot cancel a completed interview.")

        interview.status = InterviewStatus.CANCELLED
        interview.save()
        return api_response("Interview cancelled", status.HTTP_200_OK)

    @extend_schema(
        summary="Complete Interview",
        description="Marks an interview as completed. Only assigned interviewers can do this.",
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAssignedInterviewer])
    def complete(self, request, pk=None):
        interview = self.get_object()
        if interview.status == InterviewStatus.CANCELLED:
            raise ValidationError("Cannot complete a cancelled interview.")
        interview.status = InterviewStatus.COMPLETED
        interview.save()
        return api_response("Interview marked as completed", status.HTTP_200_OK)

    @extend_schema(
        summary="Submit Feedback",
        description="Submit interview feedback with scores for all rubric items.",
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="feedback",
        serializer_class=InterviewFeedbackSerializer,
        permission_classes=[IsAssignedInterviewer],
    )
    def feedback(self, request, pk=None):
        interview = self.get_object()
        serializer = InterviewFeedbackSerializer(
            data=request.data, context={"request": request, "interview": interview}
        )
        serializer.is_valid(raise_exception=True)
        feedback = serializer.save()
        return api_response(
            "Feedback submitted",
            status.HTTP_201_CREATED,
            data=InterviewFeedbackSerializer(feedback).data,
        )

    @extend_schema(
        summary="Interview Feedback",
        description="Returns all feedback for the interview along with per-rubric average scores.",
    )
    @action(detail=True, methods=["get"], url_path="feedback")
    def list_feedback(self, request, pk=None):
        interview = self.get_object()

        feedbacks = interview.feedbacks.prefetch_related("scores", "scores__rubric")

        rubric_averages = (
            FeedbackScore.objects.filter(feedback__interview=interview)
            .values("rubric_id", "rubric__label")
            .annotate(average_score=Avg("score"))
            .order_by("rubric_id")
        )

        return api_response(
            "Success",
            status.HTTP_200_OK,
            data={
                "individual_feedback": InterviewFeedbackSerializer(
                    feedbacks, many=True
                ).data,
                "rubric_averages": list(rubric_averages),
            },
        )



class FeedbackRubricViewSet(viewsets.ModelViewSet):
    queryset = FeedbackRubric.objects.all()
    serializer_class = FeedbackRubricSerializer
    permission_classes = [IsRecruiterOrAdmin]
    http_method_names = ['get', 'post', 'patch', 'delete']