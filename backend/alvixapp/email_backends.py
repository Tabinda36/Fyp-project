"""Email backends that send over HTTPS instead of SMTP.

Railway (Free/Trial/Hobby) blocks outbound SMTP ports, so on the live server the
verification email must go through an HTTP API. Enable with:

    DJANGO_EMAIL_BACKEND=alvixapp.email_backends.BrevoEmailBackend
    BREVO_API_KEY=<key from Brevo > SMTP & API > API keys>
    DJANGO_DEFAULT_FROM_EMAIL=ALVIX <a-sender-you-verified-in-brevo@example.com>
"""

import logging
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

BREVO_SEND_URL = 'https://api.brevo.com/v3/smtp/email'


def _contact(address):
    name, email = parseaddr(address)
    return {'email': email, 'name': name} if name else {'email': email}


class BrevoEmailBackend(BaseEmailBackend):
    """Sends EmailMessage / EmailMultiAlternatives through Brevo's transactional API."""

    def send_messages(self, email_messages):
        api_key = getattr(settings, 'BREVO_API_KEY', '')
        if not api_key:
            if not self.fail_silently:
                raise RuntimeError('BREVO_API_KEY is not set.')
            return 0

        timeout = getattr(settings, 'EMAIL_TIMEOUT', None) or 10
        sent = 0
        for message in email_messages:
            recipients = message.recipients()
            if not recipients:
                continue
            payload = {
                'sender': _contact(message.from_email or settings.DEFAULT_FROM_EMAIL),
                'to': [_contact(addr) for addr in message.to] or [_contact(addr) for addr in recipients],
                'subject': message.subject,
                'textContent': message.body,
            }
            if message.cc:
                payload['cc'] = [_contact(addr) for addr in message.cc]
            if message.bcc:
                payload['bcc'] = [_contact(addr) for addr in message.bcc]
            if message.reply_to:
                payload['replyTo'] = _contact(message.reply_to[0])
            for content, mimetype in getattr(message, 'alternatives', []) or []:
                if mimetype == 'text/html':
                    payload['htmlContent'] = content
            try:
                response = requests.post(
                    BREVO_SEND_URL,
                    json=payload,
                    headers={'api-key': api_key, 'accept': 'application/json'},
                    timeout=timeout,
                )
                if response.status_code >= 400:
                    raise RuntimeError(f'Brevo API error {response.status_code}: {response.text[:300]}')
                sent += 1
            except Exception:
                logger.exception('Brevo email send failed')
                if not self.fail_silently:
                    raise
        return sent
