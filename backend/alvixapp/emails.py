"""Transactional emails (HTML + plain-text fallback) sent through the configured EMAIL_BACKEND.

SMTP settings come from .env (DJANGO_EMAIL_*), see settings.py.
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

VERIFICATION_EXPIRY_MINUTES = 10


def send_verification_email(full_name, email, code):
    """Send the signup verification code. Raises on SMTP failure (caller decides how to handle)."""
    context = {
        'full_name': full_name or 'there',
        'code': code,
        'expiry_minutes': VERIFICATION_EXPIRY_MINUTES,
        'year': timezone.now().year,
    }
    message = EmailMultiAlternatives(
        subject=f'{code} is your ALVIX verification code',
        body=render_to_string('emails/verification_code.txt', context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    message.attach_alternative(render_to_string('emails/verification_code.html', context), 'text/html')
    message.send(fail_silently=False)
