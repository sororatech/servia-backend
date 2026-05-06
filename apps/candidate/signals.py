"""
Signal handlers for Candidate model.
"""
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Candidate
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Candidate)
def update_job_openings_on_hire(sender, instance, **kwargs):
    """
    When a candidate's status changes to HIRED, decrement the job's openings_count.
    
    This ensures:
    1. openings_count accurately reflects available positions
    2. Jobs auto-deactivate when fully filled
    3. Recruiters can't over-hire beyond openings_count
    """
    # Skip if this is a new candidate (not an update)
    if not instance.pk:
        logger.debug(f"Signal skipped: new candidate {instance.id}")
        return
    
    # Get the old status from database
    try:
        old_instance = Candidate.objects.select_related('job').get(pk=instance.pk)
        old_status = old_instance.status
        job = old_instance.job
    except Candidate.DoesNotExist:
        logger.error(f"Signal error: Could not fetch old instance for candidate {instance.pk}")
        return
    
    new_status = instance.status
    
    # Only act when status changes TO hired (not FROM hired, and not other changes)
    if new_status == Candidate.Status.HIRED and old_status != Candidate.Status.HIRED:
        logger.info(
            f"🎯 Candidate {instance.id} hired for job {job.id}. "
            f"Current openings: {job.openings_count}"
        )
        
        # Decrement openings if available
        if job.openings_count > 0:
            job.openings_count -= 1
            job.save(update_fields=['openings_count'])
            
            logger.info(
                f"✅ Job {job.id} openings decremented: "
                f"{job.openings_count + 1} → {job.openings_count}"
            )
            
            # Auto-deactivate job when no openings remain
            if job.openings_count == 0 and job.is_active:
                job.is_active = False
                job.save(update_fields=['is_active'])
                logger.info(f"🔕 Job {job.id} auto-deactivated (no openings remaining)")
                
                # Optional: Notify recruiter
                # from apps.users.tasks import send_html_email
                # send_html_email.delay(
                #     recipient_list=[job.posted_by.user.email] if job.posted_by else [],
                #     subject=f"Job Filled: {job.title}",
                #     template_name="emails/job_filled.html",
                #     context={'job': job}
                # )
        else:
            logger.warning(
                f"⚠️ Job {job.id} already at 0 openings, but candidate {instance.id} was hired. "
                f"This may indicate a data inconsistency."
            )