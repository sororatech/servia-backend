import os
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.db.models import F
import requests, time
from .models import SystemMetric

logger = logging.getLogger(__name__)


@shared_task
def send_html_email(subject, recipient_list, template_name, context):
    """Generic task to send an HTML email (now used directly)."""
    try:
        html_message = render_to_string(template_name, context)
        send_mail(
            subject,
            '',
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Failed to send HTML email to {recipient_list}: {str(e)}")
        raise


@shared_task
def send_welcome_email(user_id):
    """Send welcome email to new user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found for welcome email")
        return
    
    try:
        context = {'user': user}
        html_message = render_to_string('email/welcome.html', context)
        send_mail(
            subject="Welcome to ServiaAI",
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Welcome email sent to user {user.email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")


@shared_task
def send_shortlisted_email(candidate_id):
    """Send shortlisted notification to candidate."""
    from apps.candidate.models import Candidate
    
    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        logger.error(f"Candidate with ID {candidate_id} not found for shortlisted email")
        return
    
    try:
        base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        video_upload_url = f"{base_url}/dashboard/video-upload"
        context = {'candidate': candidate, 'video_upload_url': video_upload_url}
        html_message = render_to_string('email/shortlisted.html', context)
        send_mail(
            subject="You've been shortlisted!",
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[candidate.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Shortlisted email sent to candidate {candidate_id}")
    except Exception as e:
        logger.error(f"Failed to send shortlisted email to candidate {candidate_id}: {str(e)}")

@shared_task
def send_rejected_cv_email(candidate_id):
    """Send CV rejection notification to candidate."""
    from apps.candidate.models import Candidate
    
    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        logger.error(f"Candidate with ID {candidate_id} not found for rejection email")
        return
    
    try:
        context = {'candidate': candidate}
        html_message = render_to_string('email/rejected_cv.html', context)
        send_mail(
            subject="Application Update",
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[candidate.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Rejection email sent to candidate {candidate_id}")
    except Exception as e:
        logger.error(f"Failed to send rejection email to candidate {candidate_id}: {str(e)}")


@shared_task
def send_offered_email(candidate_id):
    """Send job offer notification to candidate."""
    from apps.candidate.models import Candidate
    
    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        logger.error(f"Candidate with ID {candidate_id} not found for offer email")
        return
    
    try:
        context = {'candidate': candidate}
        html_message = render_to_string('email/offered.html', context)
        send_mail(
            subject="Job Offer",
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[candidate.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Offer email sent to candidate {candidate_id}")
    except Exception as e:
        logger.error(f"Failed to send offer email to candidate {candidate_id}: {str(e)}")


@shared_task
def send_rejected_interview_email(candidate_id):
    """Send interview rejection notification to candidate."""
    from apps.candidate.models import Candidate
    
    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        logger.error(f"Candidate with ID {candidate_id} not found for interview rejection email")
        return
    
    try:
        context = {'candidate': candidate}
        html_message = render_to_string('email/rejected_interview.html', context)
        send_mail(
            subject="Application Update",
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[candidate.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Interview rejection email sent to candidate {candidate_id}")
    except Exception as e:
        logger.error(f"Failed to send interview rejection email to candidate {candidate_id}: {str(e)}")


@shared_task
def send_interview_invite_email(interview_id):
    """Send interview invitation with confirmation links."""
    from apps.interview.models import Interview
    
    try:
        interview = Interview.objects.select_related('candidate__user').get(id=interview_id)
    except Interview.DoesNotExist:
        logger.error(f"Interview with ID {interview_id} not found for invitation email")
        return
    
    try:
        base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        confirm_url = f"{base_url}/interview/confirm/{interview.confirmation_token}"
        decline_url = f"{base_url}/interview/decline/{interview.confirmation_token}"
        context = {
            'interview': interview,
            'confirm_url': confirm_url,
            'decline_url': decline_url
        }
        html_message = render_to_string('email/interview_invite.html', context)
        send_mail(
            subject="Interview Scheduled",
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[interview.candidate.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Interview invitation sent for interview {interview_id}")
    except Exception as e:
        logger.error(f"Failed to send interview invitation for interview {interview_id}: {str(e)}")


@shared_task
def send_cv_analyzed_email(candidate_id):
    """Send CV analysis completion notification."""
    from apps.candidate.models import Candidate
    
    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        logger.error(f"Candidate with ID {candidate_id} not found for CV analysis email")
        return
    
    try:
        context = {'candidate': candidate}
        html_message = render_to_string('email/cv_analyzed.html', context)
        send_mail(
            subject="CV Analysis Complete",
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[candidate.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"CV analysis email sent to candidate {candidate_id}")
    except Exception as e:
        logger.error(f"Failed to send CV analysis email to candidate {candidate_id}: {str(e)}")


@shared_task
def send_password_reset_email(user_email, reset_url):
    """
    Send password reset email with reset link.
    
    Args:
        user_email (str): Recipient email address
        reset_url (str): Full password reset URL with token
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    user_name = ""
    try:
        user = User.objects.get(email=user_email)
        if hasattr(user, 'first_name') and user.first_name:
            user_name = user.first_name
        elif hasattr(user, 'name') and user.name:
            user_name = user.name
    except User.DoesNotExist:
        logger.warning(f"Password reset requested for non-existent email: {user_email}")
    
    try:
        context = {
            'reset_url': reset_url,
            'user_name': user_name,
        }
        html_message = render_to_string('email/password_reset.html', context)
        send_mail(
            subject="Reset your ServiaAI password",
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Password reset email sent to {user_email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user_email}: {str(e)}")


@shared_task
def cleanup_unverified_users():
    """Clean up unverified users older than 2 hours."""
    from django.utils import timezone
    from datetime import timedelta
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    cutoff = timezone.now() - timedelta(hours=2)
    
    try:
        deleted_count, _ = User.objects.filter(
            is_active=False,
            date_joined__lt=cutoff
        ).delete()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} unverified users older than 2 hours")
        
        return deleted_count
    except Exception as e:
        logger.error(f"Failed to cleanup unverified users: {str(e)}")
        return 0


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email(self, user_email, verification_code, user_name=""):
    """Send verification code email with retry logic."""
    try:
        context = {
            'user_name': user_name,
            'verification_code': verification_code,
        }
        html_message = render_to_string('email/verification_code.html', context)
        send_mail(
            subject="Verify Your ServiaAI Account",
            message=f'Your verification code is: {verification_code}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Verification email sent to {user_email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {user_email}: {str(e)}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def check_system_health():
    key_date = timezone.now().strftime('%Y-%m-%d')
    
    health_url = os.getenv('HEALTH_CHECK_URL', 'http://localhost:8000/health/')
    
    try:
        start = time.time()
        r = requests.get(health_url, timeout=10)
        key = f"health_ok_{key_date}" if r.status_code == 200 else f"health_fail_{key_date}"
        if not SystemMetric.objects.filter(key=key).update(value=F('value') + 1):
            SystemMetric.objects.create(key=key, value=1)
        logger.info(f"✓ Health check logged: {key}")
    except Exception as e:
        key = f"health_fail_{key_date}"
        if not SystemMetric.objects.filter(key=key).update(value=F('value') + 1):
            SystemMetric.objects.create(key=key, value=1)
        logger.error(f"✗ Health check failed: {e}")