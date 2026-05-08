from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Candidate

@receiver(pre_save, sender=Candidate)
def update_job_openings_on_hire(sender, instance, **kwargs):
    """
    When candidate status changes to HIRED, decrement job openings_count.
    """
    if not instance.pk:
        return
    
    try:
        old_instance = Candidate.objects.select_related('job').get(pk=instance.pk)
        old_status = old_instance.status
        job = old_instance.job
    except Candidate.DoesNotExist:
        return
    
    new_status = instance.status
    
    if new_status == Candidate.Status.HIRED and old_status != Candidate.Status.HIRED:
        if job.openings_count > 0:
            job.openings_count -= 1
            job.save(update_fields=['openings_count'])
            
            # Auto-deactivate job when no openings remain
            if job.openings_count == 0 and job.is_active:
                job.is_active = False
                job.save(update_fields=['is_active'])