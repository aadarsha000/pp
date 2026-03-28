from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta

from notification.services import push_notification


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def task_notify_new_application(self, application_id: int):
    from candidates.models import Application

    application = Application.objects.select_related("job", "candidate").get(
        id=application_id
    )
    recipient = application.job.created_by
    if not recipient:
        return

    payload = {
        "event": "new_application",
        "job_title": application.job.title,
        "candidate_name": application.candidate.full_name,
        "application_id": application.id,
    }
    push_notification(recipient.id, "new_application", payload)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def task_notify_stage_changed(
    self, application_id: int, from_stage: str, to_stage: str
):
    from candidates.models import Application

    application = Application.objects.select_related("job", "candidate").get(
        id=application_id
    )
    recipient = application.job.created_by
    if not recipient:
        return

    payload = {
        "event": "stage_changed",
        "candidate_name": application.candidate.full_name,
        "from_stage": from_stage,
        "to_stage": to_stage,
        "application_id": application.id,
    }
    push_notification(recipient.id, "stage_changed", payload)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def task_notify_interview_reminder(self, interview_id: int):
    from interviews.models import Interview

    interview = (
        Interview.objects.select_related("application__candidate")
        .prefetch_related("interviewers")
        .get(id=interview_id)
    )
    candidate_name = interview.application.candidate.full_name
    payload = {
        "event": "interview_reminder",
        "interview_id": interview.id,
        "scheduled_at": interview.scheduled_at.isoformat(),
        "candidate_name": candidate_name,
    }
    for user in interview.interviewers.all():
        body = (
            f"Reminder: you have an interview with {candidate_name} "
            f"at {interview.scheduled_at.isoformat()}."
        )
        send_mail(
            subject="Interview reminder",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        push_notification(user.id, "interview_reminder", payload)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def dispatch_interview_reminders(self):
    from interviews.models import Interview, InterviewStatus

    now = timezone.now()
    window_end = now + timedelta(hours=24)
    interviews = Interview.objects.filter(
        status=InterviewStatus.SCHEDULED,
        scheduled_at__gte=now,
        scheduled_at__lt=window_end,
    ).values_list("id", flat=True)
    for interview_id in interviews:
        task_notify_interview_reminder.delay(interview_id)
