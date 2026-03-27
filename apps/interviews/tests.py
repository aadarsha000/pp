from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from candidates.models import Application, Candidate
from interviews.models import Interview, InterviewStatus, InterviewType
from jobs.models import Department, EmploymentType, JobPosting, Status as JobStatus
from users.models import CustomUser, Role


class InterviewFlowTests(APITestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="pass12345",
            role=Role.ADMIN,
        )
        self.recruiter = CustomUser.objects.create_user(
            username="recruiter",
            email="recruiter@example.com",
            password="pass12345",
            role=Role.RECRUITER,
        )
        self.interviewer_1 = CustomUser.objects.create_user(
            username="interviewer1",
            email="interviewer1@example.com",
            password="pass12345",
            role=Role.INTERVIEWER,
        )
        self.interviewer_2 = CustomUser.objects.create_user(
            username="interviewer2",
            email="interviewer2@example.com",
            password="pass12345",
            role=Role.INTERVIEWER,
        )

        dept = Department.objects.create(name="Engineering", budget_code="ENG-1", head=self.admin)
        self.job = JobPosting.objects.create(
            title="Backend Engineer",
            department=dept,
            location="Kathmandu",
            employment_type=EmploymentType.FULL_TIME,
            description="desc",
            requirements="req",
            salary_min=1000,
            salary_max=2000,
            status=JobStatus.OPEN,
            created_by=self.recruiter,
            deadline=timezone.now() + timedelta(days=7),
        )
        candidate = Candidate.objects.create(
            full_name="John Doe",
            email="john@example.com",
            phone="9800000000",
            linkedin_url="https://linkedin.com/in/john",
            source="Referral",
        )
        self.application = Application.objects.create(candidate=candidate, job=self.job)
        self.client.force_authenticate(user=self.recruiter)

    def test_schedule_conflict_returns_409(self):
        first = Interview.objects.create(
            application=self.application,
            scheduled_at=timezone.now() + timedelta(days=1, hours=1),
            duration_minutes=60,
            location_or_link="Meet",
            interview_type=InterviewType.TECHNICAL,
            status=InterviewStatus.SCHEDULED,
        )
        first.interviewers.add(self.interviewer_1)

        response = self.client.post(
            "/interviews/",
            {
                "application": self.application.id,
                "interviewers": [self.interviewer_1.id],
                "scheduled_at": (first.scheduled_at + timedelta(minutes=30)).isoformat(),
                "duration_minutes": 60,
                "location_or_link": "Meet 2",
                "interview_type": InterviewType.TECHNICAL,
                "status": InterviewStatus.SCHEDULED,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "CONFLICT")

    def test_complete_requires_assigned_interviewer(self):
        interview = Interview.objects.create(
            application=self.application,
            scheduled_at=timezone.now() + timedelta(days=1),
            duration_minutes=45,
            location_or_link="Meet",
            interview_type=InterviewType.TECHNICAL,
            status=InterviewStatus.SCHEDULED,
        )
        interview.interviewers.add(self.interviewer_1)

        self.client.force_authenticate(user=self.interviewer_2)
        response = self.client.post(f"/interviews/{interview.id}/complete/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "PERMISSION_DENIED")
