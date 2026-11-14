"""/api/v1/student/ endpoints (see api/urls.py).

Student pages rendered inside StudentLayout: dashboard home, assessment, profile,
notifications, reports, performance and settings. Business logic is shared with the legacy
template views through page_context/student.py.
"""

from django.template.defaultfilters import floatformat, truncatechars, truncatewords
from django.urls import path
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..certificate_service import generate_certificate_ai_review, topic_highlights
from ..forms import ReportForm, StudentProfileAssessmentForm, UserSettingsForm
from ..models import GeneratedCourse, Profile
from ..page_context import student as ctx
from .common import display, dt, file_url, form_errors, ok, user_payload

SETTINGS_SUCCESS_MESSAGE = "Settings updated successfully!"
SETTINGS_ERROR_MESSAGE = "Please correct the errors below."


def _text(value):
    """What `{{ value }}` printed for a number (e.g. 35.0 -> '35.0', 12 -> '12')."""
    return '' if value is None else str(value)


# ---------------------------------------------------------------------------
# Dashboard home
# ---------------------------------------------------------------------------
def _generated_course_payload(course):
    admin_course = course.admin_course
    course_level = course.course_level
    first_lesson = course.daily_lessons.first()
    benchmark = getattr(course_level, 'benchmark', '') if course_level else ''
    return {
        'id': course.id,
        # GeneratedCourse has no image field: `course.image` was always empty in the template.
        'image': file_url(getattr(course, 'image', None)),
        'admin_course': {
            'title': admin_course.title,
            'image': file_url(admin_course.image),
            'course_code': admin_course.course_code,
        },
        'course_level': {'benchmark': benchmark} if course_level else None,
        # {{ course.course_level.benchmark|default:"University Benchmark"|truncatechars:28 }}
        'tier_display': truncatechars(benchmark or "University Benchmark", 28),
        'pace': course.pace,
        'daily_lessons_count': course.daily_lessons.count(),
        'first_lesson_id': first_lesson.id if first_lesson else None,
    }


def _suggested_course_payload(course):
    if not course:
        return None
    return {
        'id': course.id,
        'title': course.title,
        'image': file_url(course.image),
        'course_code': course.course_code,
        'description': course.description,
        # {{ suggested_course.description|default:"..."|truncatewords:25 }}
        'description_display': truncatewords(course.description or "Curated from database based on your learning goals.", 25),
    }


def _notification_payload(notification):
    if not notification:
        return None
    return {
        'id': notification.id,
        'category_type': notification.category_type,
        'category_type_display': display(notification, 'category_type'),
        'created_at': dt(notification.created_at),
        'subject_heading': notification.subject_heading,
        'notification_body': notification.notification_body,
    }


class DashboardView(APIView):
    def get(self, request):
        if ctx.dashboard_requires_assessment(request.user):
            return Response({'redirect': '/assessment/'})
        c = ctx.build_dashboard_context(request)
        return Response({
            'user': user_payload(request.user),
            'generated_courses': [_generated_course_payload(g) for g in c['generated_courses']],
            'overall_progress': c['overall_progress'],
            'grade': c['grade'],
            'ai_remarks': c['ai_remarks'],
            'popup_notification': _notification_payload(c['popup_notification']),
            'suggested_course': _suggested_course_payload(c['suggested_course']),
            'certificate_unlocked': c.get('certificate_unlocked', False),
            'active_course': {'id': c['active_course'].id} if c.get('active_course') else None,
        })


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------
def _profile_payload(profile_obj):
    return {
        'student_id': profile_obj.student_id,
        'full_name': profile_obj.full_name,
        'phone': profile_obj.phone,
        'goal': profile_obj.goal,
        'dob': dt(profile_obj.dob),
        'gender': profile_obj.gender,
        'profile_picture': file_url(profile_obj.profile_picture),
        'interest_area': profile_obj.interest_area,
        'expectations': profile_obj.expectations,
        'assessment_completed': profile_obj.assessment_completed,
        'user': {'username': profile_obj.user.username, 'email': profile_obj.user.email},
    }


def _assessment_form_values(form):
    return {name: form[name].value() for name in ('interest_area', 'goal', 'expectations')}


class AssessmentView(APIView):
    def get(self, request):
        profile_obj, _ = Profile.objects.get_or_create(user=request.user)
        is_retake = ctx.assessment_is_retake(request, profile_obj)
        form = StudentProfileAssessmentForm(initial=ctx.assessment_initial(profile_obj))
        return Response({
            'form': _assessment_form_values(form),
            'errors': {},
            'profile': _profile_payload(profile_obj),
            'is_retake': is_retake,
        })

    def post(self, request):
        profile_obj, _ = Profile.objects.get_or_create(user=request.user)
        is_retake = ctx.assessment_is_retake(request, profile_obj)
        form = StudentProfileAssessmentForm(request.data)
        if form.is_valid():
            message = ctx.save_student_assessment(request, form, profile_obj, is_retake)
            return Response(ok(message, 'success', redirect='/suggested_courses/'))
        return Response({
            'ok': False,
            'errors': form_errors(form),
            'form': _assessment_form_values(form),
            'is_retake': is_retake,
            'messages': [{'tags': 'error', 'message': ctx.ASSESSMENT_ERROR_MESSAGE}],
        }, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
def _enrolled_course(user):
    """The student's most recent enrolment, shown on the profile ("Python Masterclass (Beginner)")."""
    course = (GeneratedCourse.objects.filter(user=user, admin_course__isnull=False)
              .select_related('admin_course').order_by('-created_at', '-id').first())
    if not course:
        return None
    title = course.admin_course.title
    return {'id': course.id, 'title': f'{title} ({course.level})' if course.level else title}


class ProfileView(APIView):
    def get(self, request):
        profile_obj, _ = Profile.objects.get_or_create(user=request.user)
        return Response({
            'profile': _profile_payload(profile_obj),
            'user': {'email': request.user.email},
            'enrolled_course': _enrolled_course(request.user),
        })

    def post(self, request):
        from ..upload_safety import UploadRejected
        try:
            profile_obj = ctx.save_profile(request, request.data, request.FILES)
        except UploadRejected as exc:
            return Response({'ok': False, 'error': str(exc)}, status=400)
        profile_obj.refresh_from_db()
        return Response(ok(None, redirect='/profile/', profile=_profile_payload(profile_obj),
                           user={'email': request.user.email}))


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
class NotificationsView(APIView):
    def get(self, request):
        c = ctx.build_notifications_context(request)
        return Response({
            'notifications': [
                {
                    'id': item.id,
                    'is_read': item.is_read,
                    'read_at': dt(item.read_at),
                    'notification': _notification_payload(item.notification),
                }
                for item in c['notifications']
            ],
        })


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def _report_payload(report):
    return {
        'id': report.id,
        'course_name': report.course_name,
        'problem_type': report.problem_type,
        'problem_type_display': display(report, 'problem_type'),
        'problem_title': report.problem_title,
        'problem_description': report.problem_description,
        'status': report.status,
        'status_display': display(report, 'status'),
        'created_at': dt(report.created_at),
    }


class ReportsView(APIView):
    def get(self, request):
        form = ReportForm()
        return Response({
            'form': {'problem_type_choices': [[str(v), str(label)] for v, label in form.fields['problem_type'].choices]},
            'reports': [_report_payload(r) for r in ctx.student_reports(request.user)],
        })

    def post(self, request):
        form = ReportForm(request.data, request.FILES or None)
        if form.is_valid():
            report = ctx.save_report(request, form)
            return Response(ok(ctx.REPORT_SUCCESS_MESSAGE, 'success', redirect='/reports/', report=_report_payload(report)))
        return Response({'ok': False, 'errors': form_errors(form)}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------
def _ff(value, arg):
    return floatformat(value, arg)


def _day_payload(day):
    data = dict(day)
    # Pre-rendered `|floatformat` values so the page prints exactly what Django printed.
    data['fmt'] = {
        'watch_time_pct': _ff(day['watch_time_pct'], 0),
        'watch_time_score': _ff(day['watch_time_score'], 1),
        'assignment_pct': _ff(day['assignment_pct'], 0),
        'assignment_score': _ff(day['assignment_score'], 1),
        'quiz_pct': _ff(day['quiz_pct'], 0),
        'quiz_score': _ff(day['quiz_score'], 1),
        'day_score': _ff(day['day_score'], 1),
        'day_max_score': _ff(day['day_max_score'], 1),
        'day_percentage': _ff(day['day_percentage'], 1),
    }
    return data


def _first_of(*values):
    for v in values:
        if v:
            return str(v)
    return ''


class PerformanceView(APIView):
    def get(self, request):
        c = ctx.build_performance_context(request)
        perf = c['performance']
        if perf is None:
            return Response({'performance': None, 'active_course': None, 'certificate': None,
                             'remaining_lessons': None, 'score_gap': None, 'score_gap_text': ''})

        active_course = c['active_course']
        cert = c['certificate']
        days = [_day_payload(d) for d in perf['days']]
        performance = {k: v for k, v in perf.items() if k not in ('days', 'day_evaluations')}
        performance.update({
            'days': days,
            'overall_percentage_text': _text(perf['overall_percentage']),
            'pass_mark_text': _text(perf['pass_mark']),
            # {{ performance.days.0.day_max_score|floatformat:1 }}
            'first_day_max_score_text': days[0]['fmt']['day_max_score'] if days else '',
        })
        # AI review card on the Performance page (the template expected these but never got them).
        strengths, weak_topics = topic_highlights(perf)
        performance.update({
            'ai_review': (getattr(cert, 'ai_review', '') or '') or generate_certificate_ai_review(request.user, active_course, perf),
            'strengths': strengths,
            'weak_topics': weak_topics,
        })
        admin_course = active_course.admin_course
        return Response({
            'performance': performance,
            'active_course': {
                'id': active_course.id,
                'level': active_course.level,
                # {% firstof active_course.admin_course.title active_course.title ... active_course %}
                'display_title': _first_of(
                    admin_course.title if admin_course else '',
                    getattr(active_course, 'title', ''),
                    getattr(active_course, 'course_title', ''),
                    getattr(active_course, 'course_name', ''),
                    getattr(active_course, 'topic', ''),
                    active_course,
                ),
            },
            'certificate': {'certificate_id': cert.certificate_id, 'is_unlocked': cert.is_unlocked} if cert else None,
            'remaining_lessons': c['remaining_lessons'],
            'score_gap': c['score_gap'],
            'score_gap_text': _text(c['score_gap']),
        })


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
def _settings_payload(form):
    return {name: form[name].value() for name in ('theme', 'email_notifications', 'ai_notifications', 'public_profile')}


class SettingsView(APIView):
    def get(self, request):
        form = UserSettingsForm(instance=ctx.get_user_settings(request.user))
        return Response({'form': _settings_payload(form), 'errors': {}})

    def post(self, request):
        form = UserSettingsForm(request.data, instance=ctx.get_user_settings(request.user))
        if form.is_valid():
            form.save()
            return Response(ok(SETTINGS_SUCCESS_MESSAGE, 'success', redirect='/settings/', user=user_payload(request.user)))
        return Response({
            'ok': False,
            'errors': form_errors(form),
            'form': _settings_payload(form),
            'messages': [{'tags': 'error', 'message': SETTINGS_ERROR_MESSAGE}],
        }, status=status.HTTP_400_BAD_REQUEST)


urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='api_student_dashboard'),
    path('assessment/', AssessmentView.as_view(), name='api_student_assessment'),
    path('profile/', ProfileView.as_view(), name='api_student_profile'),
    path('notifications/', NotificationsView.as_view(), name='api_student_notifications'),
    path('reports/', ReportsView.as_view(), name='api_student_reports'),
    path('performance/', PerformanceView.as_view(), name='api_student_performance'),
    path('settings/', SettingsView.as_view(), name='api_student_settings'),
]
