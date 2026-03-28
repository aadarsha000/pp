from rest_framework import serializers
from rest_framework.exceptions import APIException
from django.utils import timezone
from .models import (
    Interview,
    InterviewStatus,
    FeedbackRubric,
    InterviewFeedback,
    FeedbackScore,
)
from datetime import timedelta
from django.db import transaction
from users.models import Role


class InterviewConflictException(APIException):
    status_code = 409
    default_detail = "Interviewer schedule conflict."
    default_code = "interview_conflict"


class InterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = "__all__"

    def validate_scheduled_at(self, value):
        if value < timezone.now():
            raise serializers.ValidationError(
                "Interview must be scheduled in the future."
            )
        return value

    def validate(self, data):
        scheduled_at = data.get(
            "scheduled_at", getattr(self.instance, "scheduled_at", None)
        )
        duration = data.get(
            "duration_minutes", getattr(self.instance, "duration_minutes", 60)
        )
        if scheduled_at is None:
            return data

        end_time = scheduled_at + timedelta(minutes=duration)

        interviewers = data.get("interviewers")
        if interviewers is None and self.instance:
            interviewers = self.instance.interviewers.all()
        interviewers = list(interviewers or [])

        for interviewer in interviewers:
            if interviewer.role != Role.INTERVIEWER:
                raise serializers.ValidationError(
                    {"interviewers": f"{interviewer.username} is not an Interviewer."}
                )

        if not interviewers:
            return data

        conflict_qs = (
            Interview.objects.filter(
                interviewers__in=interviewers,
                status=InterviewStatus.SCHEDULED,
            )
            .prefetch_related("interviewers")
            .distinct()
        )
        if self.instance:
            conflict_qs = conflict_qs.exclude(id=self.instance.id)

        interviewer_set = set(interviewers)
        for existing in conflict_qs:
            existing_end = existing.scheduled_at + timedelta(
                minutes=existing.duration_minutes
            )
            if existing.scheduled_at < end_time and existing_end > scheduled_at:
                conflicting_interviewer = next(
                    (iv for iv in existing.interviewers.all() if iv in interviewer_set),
                    None,
                )
                if conflicting_interviewer:
                    raise InterviewConflictException(
                        detail={
                            "interviewer": conflicting_interviewer.username,
                            "conflicting_interview_id": existing.id,
                            "conflicting_start": existing.scheduled_at,
                            "conflicting_end": existing.end_time,
                        }
                    )
        return data


class FeedbackScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackScore
        fields = ["rubric", "score"]

    def validate(self, attrs):
        rubric = attrs["rubric"]
        score = attrs["score"]
        if score > rubric.max_score:
            raise serializers.ValidationError(
                {"score": f"Score cannot exceed rubric max_score ({rubric.max_score})."}
            )
        return attrs


class InterviewFeedbackSerializer(serializers.ModelSerializer):
    scores = FeedbackScoreSerializer(many=True)

    class Meta:
        model = InterviewFeedback
        fields = ["overall_recommendation", "notes", "scores"]

    def validate(self, data):
        interview = self.context["interview"]
        interviewer = self.context["request"].user

        if InterviewFeedback.objects.filter(
            interview=interview, interviewer=interviewer
        ).exists():
            raise serializers.ValidationError(
                "You have already submitted feedback for this interview."
            )

        if not interview.interviewers.filter(id=interviewer.id).exists():
            raise serializers.ValidationError(
                "Only assigned interviewers can submit feedback."
            )

        scores = data.get("scores", [])
        if not scores:
            raise serializers.ValidationError(
                {"scores": "At least one score is required."}
            )
        rubric_ids = [item["rubric"].id for item in scores]
        if len(rubric_ids) != len(set(rubric_ids)):
            raise serializers.ValidationError(
                {"scores": "Duplicate rubric entries are not allowed."}
            )
        required_rubric_ids = set(FeedbackRubric.objects.values_list("id", flat=True))
        submitted_rubric_ids = set(rubric_ids)
        if required_rubric_ids != submitted_rubric_ids:
            missing = sorted(required_rubric_ids - submitted_rubric_ids)
            raise serializers.ValidationError(
                {
                    "scores": f"Scores must include all rubric items. Missing rubric IDs: {missing}"
                }
            )
        return data

    @transaction.atomic
    def create(self, validated_data):
        scores_data = validated_data.pop("scores")
        feedback = InterviewFeedback.objects.create(
            interview=self.context["interview"],
            interviewer=self.context["request"].user,
            **validated_data,
        )

        for score_item in scores_data:
            FeedbackScore.objects.create(feedback=feedback, **score_item)

        return feedback
