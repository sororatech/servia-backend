"""
Custom email backend for Resend API.
Replaces SMTP for more reliable email delivery.
"""
import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage, EmailMultiAlternatives
from typing import List


class ResendBackend(BaseEmailBackend):
    """
    Email backend that sends emails via Resend API.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize Resend with API key from settings
        resend.api_key = getattr(settings, 'RESEND_API_KEY', '')
        if not resend.api_key:
            raise ValueError("RESEND_API_KEY is required for ResendBackend")
    
    def send_messages(self, email_messages: List[EmailMessage]) -> int:
        """
        Send one or more EmailMessage objects and return the number sent.
        """
        if not email_messages:
            return 0
        
        num_sent = 0
        
        for message in email_messages:
            try:
                # Prepare email payload for Resend
                payload = {
                    "from": message.from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@servia-client.com'),
                    "to": message.to,
                    "subject": message.subject,
                }
                
                # Add reply-to if specified
                if message.reply_to:
                    payload["reply_to"] = ", ".join(message.reply_to)
                
                # Add CC/BCC if present
                if message.cc:
                    payload["cc"] = message.cc
                if message.bcc:
                    payload["bcc"] = message.bcc
                
                # Handle HTML vs plain text content
                if hasattr(message, 'alternatives') and message.alternatives:
                    # Check for HTML alternative
                    for alt_content, alt_type in message.alternatives:
                        if alt_type == 'text/html':
                            payload["html"] = alt_content
                            break
                
                # Fallback to plain text body
                if "html" not in payload:
                    payload["text"] = message.body
                elif message.body:
                    # Include plain text version if HTML is present
                    payload["text"] = message.body
                
                # Add custom headers if any
                if message.extra_headers:
                    payload["headers"] = message.extra_headers
                
                # Send via Resend API
                email = resend.Emails.send(payload)
                
                # Log success if in debug mode
                if getattr(settings, 'DEBUG', False):
                    print(f"Email sent via Resend: {email.id if hasattr(email, 'id') else 'OK'}")
                
                num_sent += 1
                
            except Exception as e:
                # Log error but don't fail silently if not fail_silently
                if not self.fail_silently:
                    # Re-raise with context for debugging
                    raise type(e)(f"ResendBackend failed to send email to {message.to}: {str(e)}") from e
                # If fail_silently, just continue to next message
        
        return num_sent