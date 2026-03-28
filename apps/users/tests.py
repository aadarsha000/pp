from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from jobs.models import Department, JobPosting, EmploymentType, Status as JobStatus
from users.models import CustomUser, Role


class ErrorResponseShapeTests(APITestCase):
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
        self.dept = Department.objects.create(name="Engineering", budget_code="ENG-1", head=self.admin)
        self.job = JobPosting.objects.create(
            title="Backend Engineer",
            department=self.dept,
            location="Kathmandu",
            employment_type=EmploymentType.FULL_TIME,
            description="desc",
            requirements="req",
            salary_min=1000,
            salary_max=2000,
            status=JobStatus.DRAFT,
            created_by=self.admin,
            deadline=timezone.now() + timedelta(days=7),
        )

    def test_not_found_uses_custom_error_shape(self):
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.get("/jobs/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            set(response.data.keys()), {"message", "status_code", "code", "details"}
        )
        self.assertEqual(response.data["status_code"], status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["code"], "NOT_FOUND")

    def test_permission_denied_uses_custom_error_shape(self):
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.post(f"/jobs/{self.job.id}/publish/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            set(response.data.keys()), {"message", "status_code", "code", "details"}
        )
        self.assertEqual(response.data["status_code"], status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "PERMISSION_DENIED")
