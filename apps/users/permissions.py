from rest_framework import permissions

class IsHRAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'HR_Admin'

class IsRecruiterOrAdmin(permissions.BasePermission):
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['Recruiter', 'HR_Admin']

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'HR_Admin':
            return True
        return obj.created_by == request.user

class IsAssignedInterviewer(permissions.BasePermission):
    
    def has_object_permission(self, request, view, obj):
        return obj.interviewer == request.user


