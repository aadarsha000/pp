from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from candidates.models import Application, Candidate, Stage
from jobs.models import Department, EmploymentType, JobPosting, Status as JobStatus
from users.models import CustomUser, Role


class ReportsTests(APITestCase):
    def setUp(self):
        self.recruiter = CustomUser.objects.create_user(
            username="recruiter",
            email="recruiter@example.com",
            password="pass12345",
            role=Role.RECRUITER,
        )
        department = Department.objects.create(name="Engineering", budget_code="ENG-1", head=self.recruiter)
        self.job = JobPosting.objects.create(
            title="Backend Engineer",
            department=department,
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
        Application.objects.create(candidate=candidate, job=self.job, stage=Stage.APPLIED)
        self.client.force_authenticate(user=self.recruiter)

    def test_pipeline_funnel_json(self):
        response = self.client.get(f"/reports/pipeline-funnel/?job={self.job.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("applied", response.data)

    def test_pipeline_funnel_csv(self):
        response = self.client.get(f"/reports/pipeline-funnel/?job={self.job.id}&format=csv")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"].split(";")[0], "text/csv")
