"""Tests for the HTTPS email backend (network is always mocked)."""

from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.test import SimpleTestCase, override_settings

BACKEND = 'alvixapp.email_backends.BrevoEmailBackend'


@override_settings(BREVO_API_KEY='test-key', EMAIL_TIMEOUT=7,
                   DEFAULT_FROM_EMAIL='ALVIX <sender@example.com>')
class BrevoEmailBackendTests(SimpleTestCase):
    def _message(self, connection):
        msg = EmailMultiAlternatives('Subject', 'plain body', None, ['Student <s@example.com>'],
                                     connection=connection)
        msg.attach_alternative('<b>html</b>', 'text/html')
        return msg

    @patch('alvixapp.email_backends.requests.post')
    def test_sends_html_and_text_over_https_with_timeout(self, post):
        post.return_value = MagicMock(status_code=201, text='{}')
        sent = self._message(get_connection(BACKEND)).send()
        self.assertEqual(sent, 1)
        args, kwargs = post.call_args
        self.assertEqual(args[0], 'https://api.brevo.com/v3/smtp/email')
        self.assertEqual(kwargs['timeout'], 7)
        self.assertEqual(kwargs['headers']['api-key'], 'test-key')
        payload = kwargs['json']
        self.assertEqual(payload['sender'], {'email': 'sender@example.com', 'name': 'ALVIX'})
        self.assertEqual(payload['to'], [{'email': 's@example.com', 'name': 'Student'}])
        self.assertEqual(payload['textContent'], 'plain body')
        self.assertEqual(payload['htmlContent'], '<b>html</b>')

    @patch('alvixapp.email_backends.requests.post')
    def test_api_error_raises_unless_fail_silently(self, post):
        post.return_value = MagicMock(status_code=401, text='unauthorized')
        with self.assertRaises(RuntimeError):
            self._message(get_connection(BACKEND)).send()
        self.assertEqual(self._message(get_connection(BACKEND, fail_silently=True)).send(), 0)

    @override_settings(BREVO_API_KEY='')
    @patch('alvixapp.email_backends.requests.post')
    def test_missing_key_raises_without_network(self, post):
        with self.assertRaises(RuntimeError):
            self._message(get_connection(BACKEND)).send()
        post.assert_not_called()


class EmailTimeoutSettingTests(SimpleTestCase):
    def test_smtp_has_a_timeout(self):
        self.assertTrue(settings.EMAIL_TIMEOUT and settings.EMAIL_TIMEOUT <= 30)
