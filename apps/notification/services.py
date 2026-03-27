from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from apps.notification.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()
channel_layer = get_channel_layer()


def push_notification(user_id: int, event_type: str, payload: dict):
    """
    Create Notification in DB + push to WebSocket via channel_layer.

    Args:
        user_id: ID of HR Admin/Recruiter recipient
        event_type: One of ['new_application', 'stage_changed', 'interview_reminder']
        payload: Dict matching event schema (see docstring below)

    Payload schemas:
    - new_application: {
        'event': 'new_application',
        'job_title': str,
        'candidate_name': str,
        'application_id': int
      }
    - stage_changed: {
        'event': 'stage_changed',
        'candidate_name': str,
        'from_stage': str,
        'to_stage': str,
        'application_id': int
      }
    - interview_reminder: {
        'event': 'interview_reminder',
        'interview_id': int,
        'scheduled_at': str (ISO 8601),
        'candidate_name': str
      }
    """
    # 1. Persist to database
    Notification.objects.create(
        recipient_id=user_id, event_type=event_type, payload=payload
    )

    # 2. Push to WebSocket group
    group_name = f"notifications_user_{user_id}"

    # Use async_to_sync because Celery tasks are synchronous
    async_to_sync(channel_layer.group_send)(
        group_name,
        {"type": "send_notification", "payload": payload},  # Maps to consumer method
    )


def push_notification_to_multiple_users(
    user_ids: list[int], event_type: str, payload: dict
):
    """
    Send same notification to multiple HR Admins/Recruiters.
    Useful for broadcasting to a team.
    """
    # Save individual records for each recipient
    notifications = [
        Notification(recipient_id=uid, event_type=event_type, payload=payload)
        for uid in user_ids
    ]
    Notification.objects.bulk_create(notifications)

    # Push to each user's WebSocket group
    for user_id in user_ids:
        group_name = f"notifications_user_{user_id}"
        async_to_sync(channel_layer.group_send)(
            group_name, {"type": "send_notification", "payload": payload}
        )
