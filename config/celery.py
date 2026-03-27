import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

from celery.schedules import crontab

beat_schedule = {
    'send-interview-reminders-daily': {
        'task': 'notification.tasks.task_notify_interview_reminder',
        'schedule': crontab(hour=9, minute=0),  # Run daily at 9 AM
        # Note: The task itself filters interviews scheduled for next 24h
    },
}