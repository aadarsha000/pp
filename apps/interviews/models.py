from django.db import models
from django.conf import settings
from datetime import timedelta
from django.core.validators import MinValueValidator, MaxValueValidator

class InterviewType(models.TextChoices):
    TECHNICAL = 'Technical', 'Technical'
    BEHAVIOURAL = 'Behavioural', 'Behavioural'
    HR = 'HR', 'HR'
    FINAL = 'Final', 'Final'

class InterviewStatus(models.TextChoices):
    SCHEDULED = 'Scheduled', 'Scheduled'
    COMPLETED = 'Completed', 'Completed'
    CANCELLED = 'Cancelled', 'Cancelled'

class Interview(models.Model):
    application = models.ForeignKey('Application', on_delete=models.CASCADE, related_name='interviews')
    interviewers = models.ManyToManyField(settings.AUTH_USER_MODEL, limit_choices_to={'role': 'Interviewer'})
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    location_or_link = models.CharField(max_length=255)
    interview_type = models.CharField(max_length=20, choices=InterviewType.choices)
    status = models.CharField(max_length=20, choices=InterviewStatus.choices, default=InterviewStatus.SCHEDULED)
    notes = models.TextField(blank=True)

    @property
    def end_time(self):
        return self.scheduled_at + timedelta(minutes=self.duration_minutes)
    
    def __str__(self):
        return f"Interview for {self.application.candidate.name} on {self.scheduled_at}"


class FeedbackRubric(models.Model):
    label = models.CharField(max_length=100)
    max_score = models.PositiveIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])

    def __str__(self):
        return self.label



class InterviewFeedback(models.Model):
    RECOMMENDATION_CHOICES = (
        ('Hire', 'Hire'), 
        ('No Hire', 'No Hire'), 
        ('Maybe', 'Maybe')
    )
    
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='feedbacks')
    interviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    overall_recommendation = models.CharField(max_length=10, choices=RECOMMENDATION_CHOICES)
    notes = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('interview', 'interviewer')



class FeedbackScore(models.Model):
    feedback = models.ForeignKey(InterviewFeedback, on_delete=models.CASCADE, related_name='scores')
    rubric = models.ForeignKey(FeedbackRubric, on_delete=models.CASCADE)
    score = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
