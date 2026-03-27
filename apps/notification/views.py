from rest_framework import viewsets
from .models import Notification
from .serializers import NotificationSerializer
from users.permissions import IsRecruiterOrAdmin
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import CursorPagination
from rest_framework.filters import OrderingFilter
from drf_spectacular.utils import extend_schema


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsRecruiterOrAdmin]
    http_method_names = ['get', 'patch']
    pagination_class = CursorPagination
    ordering_fields = ['created_at']
    ordering = 'created_at'

    filter_backends = [OrderingFilter]

    @extend_schema(summary="Mark Notification as Read", description="Marks a notification as read.")
    @action(detail=True, methods=['patch'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True 
        notification.save()
        return Response({"id": notification.id, "is_read": notification.is_read})