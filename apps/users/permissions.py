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
    Allows access to:
    - Superusers (Django superusers)
    - Recruiters with role='admin'
    """
    def has_permission(self, request, view):
        
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return hasattr(user, 'recruiter_profile') and user.recruiter_profile.role == 'admin'