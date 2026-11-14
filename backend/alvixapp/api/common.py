"""Shared helpers for the ALVIX JSON API (used by every api/*.py module)."""

from django.contrib import messages as django_messages
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission

from ..permissions import is_alvix_admin


class CsrfSessionAuthentication(SessionAuthentication):
    """
    Session auth that enforces CSRF on every unsafe request, including anonymous ones
    (login, signup, OTP). DRF's stock SessionAuthentication only checks CSRF once a user
    is logged in; the original Django views were always CSRF-protected.
    """

    def authenticate(self, request):
        result = super().authenticate(request)  # enforces CSRF for logged-in users
        if result is None:
            self.enforce_csrf(request)
        return result


class IsAlvixAdmin(BasePermission):
    message = 'Administrator access required.'

    def has_permission(self, request, view):
        return is_alvix_admin(request.user)


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------
def file_url(field):
    """URL of a FileField/ImageField or None (templates used `{% if x %}{{ x.url }}`)."""
    try:
        return field.url if field else None
    except (ValueError, AttributeError):
        return None


def dt(value):
    """ISO string in the server time zone (Asia/Karachi) so the frontend can format wall-clock time
    exactly like Django's |date filter did. Dates (not datetimes) are returned as YYYY-MM-DD."""
    if value is None:
        return None
    if hasattr(value, 'tzinfo'):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.isoformat()
    return value.isoformat()


def display(instance, field):
    """Equivalent of `{{ obj.get_<field>_display }}`."""
    getter = getattr(instance, f'get_{field}_display', None)
    return getter() if callable(getter) else getattr(instance, field, None)


def pick(instance, *fields):
    """Plain dict of simple attributes."""
    return {f: getattr(instance, f, None) for f in fields}


# ---------------------------------------------------------------------------
# Common payloads
# ---------------------------------------------------------------------------
def user_payload(user):
    """Everything the templates read from `request.user` (+ profile/settings)."""
    if not user or not user.is_authenticated:
        return {'is_authenticated': False}

    profile = getattr(user, 'profile', None)
    settings_obj = getattr(user, 'settings', None)
    return {
        'is_authenticated': True,
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'full_name': user.get_full_name(),
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'is_admin': is_alvix_admin(user),
        'profile': {
            'student_id': profile.student_id,
            'full_name': profile.full_name,
            'phone': profile.phone,
            'goal': profile.goal,
            'dob': dt(profile.dob),
            'gender': profile.gender,
            'profile_picture': file_url(profile.profile_picture),
            'interest_area': profile.interest_area,
            'expectations': profile.expectations,
            'assessment_completed': profile.assessment_completed,
        } if profile else None,
        'settings': {
            'theme': settings_obj.theme,
            'email_notifications': settings_obj.email_notifications,
            'ai_notifications': settings_obj.ai_notifications,
            'public_profile': settings_obj.public_profile,
        } if settings_obj else None,
    }


def collect_messages(request):
    """Drain Django messages added by shared service/view code into API JSON."""
    return [{'tags': m.tags.split()[-1] if m.tags else 'info', 'message': str(m)} for m in django_messages.get_messages(request)]


def ok(message=None, level='success', **data):
    """Standard success payload for actions: {ok, messages:[...], ...data}."""
    payload = {'ok': True}
    if message:
        payload['messages'] = [{'tags': level, 'message': message}]
    payload.update(data)
    return payload


def form_errors(form):
    return {field: [str(e) for e in errs] for field, errs in form.errors.items()}
