"""Session authentication endpoints: csrf, me, login, logout."""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Profile
from ..permissions import is_alvix_admin
from .common import user_payload


def post_login_path(user):
    """Same routing as the old login_view."""
    if is_alvix_admin(user):
        return '/admindashboard/'
    profile, _ = Profile.objects.get_or_create(user=user)
    if not profile.assessment_completed:
        return '/assessment/'
    return '/dashboard/'


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'ok': True})


@method_decorator(ensure_csrf_cookie, name='dispatch')
class MeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(user_payload(request.user))


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email_input = str(request.data.get('email') or '').strip()
        password = request.data.get('password') or ''

        # emails are matched case-insensitively and without surrounding spaces
        user_obj = User.objects.filter(email__iexact=email_input).first() if email_input else None
        username = user_obj.username if user_obj else email_input
        user = authenticate(request, username=username, password=password)

        if user is None:
            return Response({'ok': False, 'error': 'Invalid email or password.'}, status=status.HTTP_400_BAD_REQUEST)

        login(request, user)
        return Response({'ok': True, 'redirect': post_login_path(user), 'user': user_payload(user)})


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response({'ok': True, 'redirect': '/login/'})
