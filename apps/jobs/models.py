from django.db import models
from django.conf import settings

class Department(models.Model):
    name = models.CharField(max_length=100)
    budget_code = models.CharField(max_length=50)
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='headed_departments'
    )

    def __str__(self):
        return self.name

class EmploymentType(models.TextChoices):
    FULL_TIME = 'Full-Time', 'Full-Time'
    PART_TIME = 'Part-Time', 'Part-Time'
    CONTRACT = 'Contract', 'Contract'
    REMOTE = 'Remote', 'Remote'

class Status(models.TextChoices):
    DRAFT = 'Draft', 'Draft'
    OPEN = 'Open', 'Open'
    CLOSED = 'Closed', 'Closed'


class JobPosting(models.Model):
    title = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='jobs')
    location = models.CharField(max_length=255)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices)
    description = models.TextField()
    requirements = models.TextField()
    salary_min = models.DecimalField(max_digits=12, decimal_places=2)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='created_jobs'
    )
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
