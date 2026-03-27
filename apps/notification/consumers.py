import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.notification.utils import get_validated_user_from_token
from apps.notification.models import Notification
from users.models import Role


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Personal WebSocket channel for HR Admins/Recruiters.
    Connect: ws://host/ws/notifications/?token=<jwt_access_token>
    Close code 4001 = invalid/expired token or unauthorized role
    """

    async def connect(self):
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        self.group_name = f"notifications_user_{self.user.id}"

        # Join user-specific channel group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Optional: Send initial unread count
        unread_count = await self._get_unread_count()
        await self.send(
            text_data=json.dumps(
                {"event": "connection_established", "unread_count": unread_count}
            )
        )

    async def disconnect(self, close_code):
        """Clean up: leave the user group"""
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Handle client messages (e.g., mark notification as read via WS)
        Expected: {"action": "mark_read", "notification_id": 123}
        """
        try:
            data = json.loads(text_data)
            if data.get("action") == "mark_read" and data.get("notification_id"):
                success = await self._mark_notification_read(data["notification_id"])
                if success:
                    await self.send(
                        text_data=json.dumps(
                            {
                                "event": "acknowledgement",
                                "notification_id": data["notification_id"],
                                "status": "read",
                            }
                        )
                    )
        except (json.JSONDecodeError, KeyError):
            pass  # Silently ignore malformed messages

    async def send_notification(self, event):
        """
        Channel layer handler: sends notification payload to connected client.
        Called via: channel_layer.group_send(group_name, {'type': 'send_notification', 'payload': {...}})
        """
        payload = event.get("payload", {})
        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def _get_unread_count(self):
        """Get count of unread notifications for connected user"""
        return Notification.objects.filter(recipient=self.user, is_read=False).count()

    @database_sync_to_async
    def _mark_notification_read(self, notification_id):
        """Mark a specific notification as read (owner check included)"""
        return (
            Notification.objects.filter(
                id=notification_id, recipient=self.user, is_read=False
            ).update(is_read=True)
            > 0
        )
