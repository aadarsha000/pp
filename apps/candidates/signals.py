from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.cache import cache
import uuid

from .models import Application, Stage, ApplicationStageLog
from notification.models import Notification


@receiver(pre_save, sender=Application)
def capture_previous_stage(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_stage = None
        return
    instance._previous_stage = (
        Application.objects.filter(pk=instance.pk)
        .values_list('stage', flat=True)
        .first()
    )


@receiver(post_save, sender=Application)
def notify_offer_stage(sender, instance, created, **kwargs):
    if created:
        return

    previous_stage = getattr(instance, "_previous_stage", None)
    if instance.stage == Stage.OFFER and previous_stage != Stage.OFFER:
        Notification.objects.create(
            user=instance.job.created_by,
            message=f"Candidate {instance.candidate.full_name} has reached the Offer stage!",
        )


@receiver(post_save, sender=ApplicationStageLog)
def invalidate_reports_cache(sender, instance, created, **kwargs):

    if not created:
        return
    cache.set("reports_cache_version", uuid.uuid4().hex, None)