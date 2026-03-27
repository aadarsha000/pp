from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Application, Stage, Notification
from django.utils import timezone

@receiver(post_save, sender=Application)
def notify_offer_stage(sender, instance, created, **kwargs):
    if not created and instance.stage == Stage.OFFER:
        Notification.objects.create(
            user=instance.job.created_by,
            message=f"Candidate {instance.candidate.full_name} has reached the Offer stage!",
            created_at=timezone.now(),
            is_read=False
        )