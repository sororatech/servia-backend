# from apps.users.tasks import (
#     send_shortlisted_email,
#     send_rejected_cv_email,
#     send_offered_email,
#     send_rejected_interview_email,
# )

# def send_status_email(candidate, new_status, old_status=None):
#     if new_status == old_status:
#         return
#     if new_status == 'shortlisted':
#         send_shortlisted_email.delay(candidate.id)
#     elif new_status == 'rejected_cv':
#         send_rejected_cv_email.delay(candidate.id)
#     elif new_status == 'offered':
#         send_offered_email.delay(candidate.id)
#     elif new_status == 'rejected_interview':
#         send_rejected_interview_email.delay(candidate.id)

"""
Email notification service for candidate status changes.
"""

import logging
from apps.users.tasks import (
    send_shortlisted_email,
    send_rejected_cv_email,
    send_offered_email,
    send_rejected_interview_email,
)

logger = logging.getLogger(__name__)


def send_status_email(candidate, new_status, old_status=None):
    """
    Send email notification based on candidate status change.
    
    Args:
        candidate: Candidate instance
        new_status: New status value
        old_status: Old status value (optional)
    """
    if new_status == old_status:
        return
    
    logger.info(f"Sending status email for candidate {candidate.id}: {old_status} -> {new_status}")
    
    try:
        if new_status == 'shortlisted':
            send_shortlisted_email.delay(candidate.id)
        elif new_status == 'rejected_cv':
            send_rejected_cv_email.delay(candidate.id)
        elif new_status == 'offered':
            send_offered_email.delay(candidate.id)
        elif new_status == 'rejected_interview':
            send_rejected_interview_email.delay(candidate.id)
    except Exception as e:
        logger.error(f"Failed to send status email for candidate {candidate.id}: {str(e)}")