from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

from jobs.models import JobPosting

class Stage(models.TextChoices):
    APPLIED = 'Applied', 'Applied'
    SCREENING = 'Screening', 'Screening'
    TECHNICAL = 'Technical Interview', 'Technical Interview'
    HR = 'HR Interview', 'HR Interview'
    OFFER = 'Offer', 'Offer'
    HIRED = 'Hired', 'Hired'
    REJECTED = 'Rejected', 'Rejected'

class Candidate(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    linkedin_url = models.URLField(blank=True)
    source = models.CharField(max_length=50, choices=[
        ('Job Board','Job Board'), 
        ('Referral','Referral'), 
        ('Direct','Direct'), 
        ('Agency','Agency')
        ])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


'''
Application
'''
class Application(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='candidate_applications')
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='job_applications')
    stage = models.CharField(max_length=30, choices=Stage.choices, default=Stage.APPLIED)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

class ApplicationStageLog(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='logs')
    from_stage = models.CharField(max_length=30)
    to_stage = models.CharField(max_length=30)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)


'''
Documents
'''
class Document(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=[
        ('CV','CV'), 
        ('Cover Letter','Cover Letter'), 
        ('Portfolio','Portfolio'), ('Other','Other')
        ])
    file = models.FileField(upload_to='docs/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)



