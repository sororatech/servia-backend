from rest_framework import permissions

class IsRecruiter(permissions.BasePermission):
    """
    Allows access only to users with a RecruiterUser profile.
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and
                hasattr(request.user, 'recruiter_profile'))


class IsAdminRecruiter(permissions.BasePermission):
    """
    Allows access only to recruiters with role='admin'.
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and
                hasattr(request.user, 'recruiter_profile') and
                request.user.recruiter_profile.role == 'admin')