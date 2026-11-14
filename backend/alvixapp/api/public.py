"""/api/v1/public/ endpoints (see api/urls.py): signup + verification, suggested courses, certificate verify.

The logic is shared with the legacy template views through page_context/public.py.
"""

from django.urls import path
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..page_context import public as public_ctx
from .common import collect_messages, dt, user_payload


def _saved(data):
    """Only the fields signup.html re-fills (`saved_data.full_name|username|email`)."""
    return {k: data.get(k) or '' for k in ('full_name', 'username', 'email')}


class SignupView(APIView):
    """Step 1: registration form -> verification code sent."""
    permission_classes = [AllowAny]

    def post(self, request):
        result = public_ctx.signup_start(request, request.data)
        if not result['ok']:
            return Response({'ok': False, 'error': result['error'], 'saved_data': _saved(result['saved_data'])},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'ok': True,
            'step': result['step'],
            'email': result['email'],
            'verification_code_debug': result['verification_code_debug'],
        })


class SignupVerifyView(APIView):
    """Step 2. `verification_code` = signup page semantics; `otp_code` = legacy /verify-otp/ page semantics."""
    permission_classes = [AllowAny]

    def get(self, request):
        """What /verify-otp/ needs on load: redirect to /signup/ when nothing is pending."""
        pending = public_ctx.pending_signup(request)
        if not pending:
            return Response({'redirect': '/signup/'})
        return Response({'email': pending.get('email')})

    def post(self, request):
        data = request.data
        if 'otp_code' in data and 'verification_code' not in data:
            # verify_otp_view semantics
            if not public_ctx.pending_signup(request):
                return Response({'ok': False, 'redirect': '/signup/'}, status=status.HTTP_400_BAD_REQUEST)
            result = public_ctx.verify_otp(request, str(data.get('otp_code') or ''))
            if not result['ok']:
                return Response({'ok': False, 'error': result['error'], 'email': result['email']},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            result = public_ctx.signup_verify(request, str(data.get('verification_code') or data.get('otp_code') or ''))
            if not result['ok']:
                return Response({'ok': False, 'error': result['error'], 'step': result['step'], 'email': result['email']},
                                status=status.HTTP_400_BAD_REQUEST)
        return Response({'ok': True, 'redirect': '/assessment/', 'user': user_payload(result['user'])})


def _course(c):
    return {'id': c.id, 'title': c.title, 'course_code': getattr(c, 'course_code', None), 'description': c.description}


class SuggestedCoursesView(APIView):
    permission_classes = [IsAuthenticated]

    def _payload(self, request, ctx):
        context = public_ctx.build_suggested_courses_context(request, ctx)
        sc = context['suggested_course']
        return {
            'student_name': context['student_name'],
            'student_id': context['student_id'],
            'interest_area': context['interest_area'],
            'goal': context['goal'],
            'expectations': context['expectations'],
            'suggested_course': _course(sc) if sc else None,
            'ai_reason': context['ai_reason'],
            'suggested_level': context['suggested_level'],
            'available_levels': [
                {'id': lv.id, 'level': lv.level, 'benchmark': getattr(lv, 'benchmark', None)}
                for lv in context['available_levels']
            ],
            'other_courses': [_course(c) for c in context['other_courses']],
            'messages': collect_messages(request),
        }

    def get(self, request):
        ctx = public_ctx.resolve_course_suggestion(request)
        return Response(self._payload(request, ctx))

    def post(self, request):
        ctx = public_ctx.resolve_course_suggestion(request)
        target = public_ctx.handle_suggested_courses_action(request, request.data, ctx)
        if target:
            return Response({'ok': True, 'redirect': target, 'messages': collect_messages(request)})
        # The view fell through and re-rendered the page (with any messages).
        payload = self._payload(request, ctx)
        payload['ok'] = True
        return Response(payload)


class CertificateVerifyView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, cert_id):
        context = public_ctx.build_certificate_verify_context(cert_id)
        cert = context['certificate']
        return Response({
            'cert_id': context['cert_id'],
            'is_valid': context['is_valid'],
            'verification_time': dt(context['verification_time']),
            'certificate': {
                'certificate_id': cert.certificate_id,
                'student_name': cert.student_name,
                'student_email': cert.student_email,
                'course_name': cert.course_name,
                'level': cert.level,
                # str() keeps the template rendering of the float (e.g. "92.5", "85.0")
                'overall_percentage': str(cert.overall_percentage),
                'performance_grade': cert.performance_grade,
                'start_date': dt(cert.start_date),
                'current_date': dt(cert.current_date),
                'duration_days': cert.duration_days,
                'ai_review': cert.ai_review,
            } if cert and context['is_valid'] else None,
        })


urlpatterns = [
    path('signup/', SignupView.as_view(), name='api_public_signup'),
    path('signup/verify/', SignupVerifyView.as_view(), name='api_public_signup_verify'),
    path('suggested-courses/', SuggestedCoursesView.as_view(), name='api_public_suggested_courses'),
    path('certificates/<str:cert_id>/verify/', CertificateVerifyView.as_view(), name='api_public_certificate_verify'),
]
