from celery import shared_task

from notification.services import push_notification


@shared_task
def task_notify_interview_reminder(interview_id: int):
    """
    Scheduled via Celery Beat to run 24h before interview.
    Notifies interviewers + assigned recruiter.
    """
    from users.models import Role
    from interviews.models import Interview

    
    interview = Interview.objects.select_related(
        'application__candidate__user',
        'application__assigned_recruiter'
    ).prefetch_related('interviewers').get(id=interview_id)
    
    recipients = []
    
    # Add all interviewers for this interview
    interviewer_ids = interview.interviewers.filter(
        is_active=True,
        role=Role.INTERVIEWER  # Only notify actual interviewers
    ).values_list('id', flat=True)
    recipients.extend(interviewer_ids)
    
    # Add assigned recruiter if exists
    if interview.application.assigned_recruiter:
        recipients.append(interview.application.assigned_recruiter.id)
    
    payload = {
        'event': 'interview_reminder',
        'interview_id': interview.id,
        'scheduled_at': interview.scheduled_at.isoformat(),
        'candidate_name': interview.application.candidate.get_full_name()
    }
    
    for recipient_id in set(recipients):
        push_notification(recipient_id, 'interview_reminder', payload)