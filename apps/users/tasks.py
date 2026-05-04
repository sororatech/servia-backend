import os
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

@shared_task
def send_html_email(subject, recipient_list, template_name, context):
    """Generic task to send an HTML email (now used directly)."""
    html_message = render_to_string(template_name, context)
    send_mail(
        subject,
        '',
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
        html_message=html_message,
        fail_silently=False,
    )

@shared_task
def send_welcome_email(user_id):
    from django.contrib.auth.models import User
    user = User.objects.get(id=user_id)
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

@shared_task
def send_shortlisted_email(candidate_id):
    from apps.candidate.models import Candidate
    candidate = Candidate.objects.get(id=candidate_id)
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

@shared_task
def send_rejected_cv_email(candidate_id):
    from apps.candidate.models import Candidate
    candidate = Candidate.objects.get(id=candidate_id)
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

@shared_task
def send_offered_email(candidate_id):
    from apps.candidate.models import Candidate
    candidate = Candidate.objects.get(id=candidate_id)
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

@shared_task
def send_rejected_interview_email(candidate_id):
    from apps.candidate.models import Candidate
    candidate = Candidate.objects.get(id=candidate_id)
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

@shared_task
def send_interview_invite_email(interview_id):
    from apps.interview.models import Interview
    interview = Interview.objects.get(id=interview_id)
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

@shared_task
def send_cv_analyzed_email(candidate_id):
    from apps.candidate.models import Candidate
    candidate = Candidate.objects.get(id=candidate_id)
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
        # Handle both CandidateUser and RecruiterUser models
        if hasattr(user, 'first_name') and user.first_name:
            user_name = user.first_name
        elif hasattr(user, 'name') and user.name:
            user_name = user.name
    except User.DoesNotExist:
        pass  # User might not exist yet, or email might be invalid
    
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