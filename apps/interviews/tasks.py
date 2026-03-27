from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .models import Interview, InterviewStatus
from django.conf import settings



@shared_task
def send_interviewer_reminders():
    now = timezone.now()
    next_24h = now + timedelta(hours=24)
    interviews = Interview.objects.filter(
        scheduled_at__gte=now,
        scheduled_at__lte=next_24h,
        status=InterviewStatus.SCHEDULED
    ).prefetch_related('interviewers')

    for interview in interviews:
        emails = [i.email for i in interview.interviewers.all() if i.email]
        send_mail(
            subject="Reminder: Upcoming Interview Tomorrow",
            message=f"You have a {interview.interview_type} interview at {interview.scheduled_at}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=emails
        )
