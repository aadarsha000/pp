from django.contrib.auth.models import AbstractUser
from django.db import models

class Role(models.TextChoices):
    ADMIN = 'HR_Admin', 'HR_Admin'
    RECRUITER = 'Recruiter', 'Recruiter'
    INTERVIEWER = 'Interviewer', 'Interviewer'


class CustomUser(AbstractUser):

    
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices)

   

    def __str__(self):
        return self.email


