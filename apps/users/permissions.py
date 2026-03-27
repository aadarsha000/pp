from rest_framework import permissions
from users.models import Role

class IsHRAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == Role.ADMIN

class IsRecruiterOrAdmin(permissions.BasePermission):
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [Role.RECRUITER, Role.ADMIN]

    def has_object_permission(self, request, view, obj):
        if request.user.role == Role.ADMIN:
            return True
        for owner_attr in ['created_by', 'recruiter', 'assigned_recruiter']:
            owner = getattr(obj, owner_attr, None)
            if owner == request.user:
                return True
        return False

class IsAssignedInterviewer(permissions.BasePermission):
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated or request.user.role != Role.INTERVIEWER:
            return False
        if hasattr(obj, 'interviewers'):
            return obj.interviewers.filter(id=request.user.id).exists()
        return getattr(obj, 'interviewer_id', None) == request.user.id


