from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from candidates.models import Application, Candidate
from jobs.models import Department, EmploymentType, JobPosting, Status as JobStatus
from users.models import CustomUser, Role


class JobEndpointsTests(APITestCase):
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
        self.department = Department.objects.create(name="Engineering", budget_code="ENG-1", head=self.admin)
        self.job = JobPosting.objects.create(
            title="Backend Engineer",
            department=self.department,
            location="Kathmandu",
            employment_type=EmploymentType.FULL_TIME,
            description="desc",
            requirements="req",
            salary_min=1000,
            salary_max=2000,
            status=JobStatus.DRAFT,
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
        Application.objects.create(candidate=candidate, job=self.job)
        self.client.force_authenticate(user=self.recruiter)

    def test_list_uses_compact_serializer_fields(self):
        response = self.client.get("/jobs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data["results"][0]
        self.assertIn("department_name", item)
        self.assertIn("applicant_count", item)

    def test_bulk_status_update_validates_missing_ids(self):
        response = self.client.post(
            "/jobs/bulk-status-update/",
            {"ids": [self.job.id, 999999], "status": JobStatus.CLOSED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["status_code"], status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["code"], "NOT_FOUND")

    def test_bulk_status_update_duplicate_ids_succeeds_once(self):
        response = self.client.post(
            "/jobs/bulk-status-update/",
            {"ids": [self.job.id, self.job.id], "status": JobStatus.CLOSED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["updated_count"], 1)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, JobStatus.CLOSED)

    def test_bulk_status_update_permission_denied_for_other_users_job(self):
        other_job = JobPosting.objects.create(
            title="Other",
            department=self.department,
            location="Kathmandu",
            employment_type=EmploymentType.FULL_TIME,
            description="d",
            requirements="r",
            salary_min=1,
            salary_max=2,
            status=JobStatus.OPEN,
            created_by=self.admin,
            deadline=timezone.now() + timedelta(days=7),
        )
        response = self.client.post(
            "/jobs/bulk-status-update/",
            {"ids": [other_job.id], "status": JobStatus.CLOSED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "PERMISSION_DENIED")
