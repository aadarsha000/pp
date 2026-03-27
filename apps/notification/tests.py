from rest_framework import status
from rest_framework.test import APITestCase

from notification.models import Notification
from users.models import CustomUser, Role


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.user_1 = CustomUser.objects.create_user(
            username="recruiter1",
            email="recruiter1@example.com",
            password="pass12345",
            role=Role.RECRUITER,
        )
        self.user_2 = CustomUser.objects.create_user(
            username="recruiter2",
            email="recruiter2@example.com",
            password="pass12345",
            role=Role.RECRUITER,
        )
        Notification.objects.create(
            recipient=self.user_1,
            event_type="new_application",
            payload={"event": "new_application", "application_id": 1},
        )
        Notification.objects.create(
            recipient=self.user_1,
            event_type="stage_changed",
            payload={"event": "stage_changed", "application_id": 2},
            is_read=True,
        )
        Notification.objects.create(
            recipient=self.user_2,
            event_type="new_application",
            payload={"event": "new_application", "application_id": 3},
        )
        self.client.force_authenticate(user=self.user_1)

    def test_list_returns_only_authenticated_users_notifications(self):
        response = self.client.get("/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        recipient_ids = {item["recipient"] for item in response.data["results"]}
        self.assertEqual(recipient_ids, {self.user_1.id})

    def test_mark_all_read_updates_only_current_users_rows(self):
        response = self.client.post("/notifications/mark-all-read/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["marked_count"], 1)
        self.assertEqual(Notification.objects.filter(recipient=self.user_1, is_read=False).count(), 0)
        self.assertEqual(Notification.objects.filter(recipient=self.user_2, is_read=False).count(), 1)
