from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from candidates.models import Application, ApplicationStageLog, Candidate, Document, Stage
from jobs.models import Department, EmploymentType, JobPosting, Status as JobStatus
from users.models import CustomUser, Role


class ApplicationAndDocumentTests(APITestCase):
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
            status=JobStatus.OPEN,
            created_by=self.recruiter,
            deadline=timezone.now() + timedelta(days=7),
        )
        self.candidate = Candidate.objects.create(
            full_name="John Doe",
            email="john@example.com",
            phone="9800000000",
            linkedin_url="https://linkedin.com/in/john",
            source="Referral",
        )
        self.application = Application.objects.create(candidate=self.candidate, job=self.job, stage=Stage.APPLIED)
        self.client.force_authenticate(user=self.recruiter)

    def test_stage_update_requires_sequential_progression(self):
        response = self.client.patch(
            f"/applications/{self.application.id}/stage/",
            {"stage": Stage.TECHNICAL},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "VALIDATION_ERROR")

    def test_stage_update_logs_transition(self):
        response = self.client.patch(
            f"/applications/{self.application.id}/stage/",
            {"stage": Stage.SCREENING, "note": "Initial CV screen passed"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stage_log = ApplicationStageLog.objects.get(application=self.application)
        self.assertEqual(stage_log.from_stage, Stage.APPLIED)
        self.assertEqual(stage_log.to_stage, Stage.SCREENING)
        self.assertEqual(stage_log.changed_by, self.recruiter)

    def test_document_upload_rejects_invalid_mime(self):
        bad_file = SimpleUploadedFile("bad.txt", b"bad", content_type="text/plain")
        response = self.client.post(
            f"/applications/{self.application.id}/documents/",
            {"document_type": "CV", "file": bad_file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "VALIDATION_ERROR")

    def test_document_upload_rejects_when_more_than_three(self):
        for i in range(3):
            Document.objects.create(
                application=self.application,
                document_type="CV",
                file=SimpleUploadedFile(f"ok-{i}.pdf", b"%PDF-1.4", content_type="application/pdf"),
                uploaded_by=self.recruiter,
            )

        response = self.client.post(
            f"/applications/{self.application.id}/documents/",
            {
                "document_type": "Cover Letter",
                "file": SimpleUploadedFile("cover.pdf", b"%PDF-1.4", content_type="application/pdf"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "VALIDATION_ERROR")
