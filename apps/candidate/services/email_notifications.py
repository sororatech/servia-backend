from apps.users.tasks import (
    send_shortlisted_email,
    send_rejected_cv_email,
    send_offered_email,
    send_rejected_interview_email,
)

def send_status_email(candidate, new_status, old_status=None):
    if new_status == old_status:
        return
    if new_status == 'shortlisted':
        send_shortlisted_email.delay(candidate.id)
    elif new_status == 'rejected_cv':
        send_rejected_cv_email.delay(candidate.id)
    elif new_status == 'offered':
        send_offered_email.delay(candidate.id)
    elif new_status == 'rejected_interview':
        send_rejected_interview_email.delay(candidate.id)