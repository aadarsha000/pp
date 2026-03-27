from django.db import models
from django.conf import settings

class Notification(models.Model):
    EVENT_TYPES = [
        ('new_application', 'New Application'),
        ('stage_changed', 'Stage Changed'),
        ('interview_reminder', 'Interview Reminder'),
    ]
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    payload = models.JSONField(default=dict)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['is_read', '-created_at']
        indexes = [
            models.Index(fields=['recipient', '-is_read', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]