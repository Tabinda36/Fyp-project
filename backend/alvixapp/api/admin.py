"""/api/v1/admin/ endpoints (see api/urls.py): admin dashboard, users, reports,
notifications, analytics and avatar settings.

All logic is shared with the legacy template views through
``alvixapp.page_context.admin``.
"""

from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..forms import AvatarSettingsForm
from ..models import AvatarSettings
from ..page_context import admin as ctx
from .common import IsAlvixAdmin, display, dt, form_errors, ok


class AdminAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAlvixAdmin]


def _profile(user):
    try:
        return user.profile
    except Exception:  # RelatedObjectDoesNotExist: the template treated it as falsy
        return None


# ---------------------------------------------------------------------------
# Dashboard home  (admin_db/admindashboard.html default block)
# ---------------------------------------------------------------------------
class DashboardView(AdminAPIView):
    def get(self, request):
        c = ctx.build_admin_dashboard_context()
        return Response({
            'total_courses': c['total_courses'],
            'total_students': c['total_students'],
            'pending_reports_count': c['pending_reports_count'],
            'total_enrollments': c['total_enrollments'],
        })


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------
def _user_row(u):
    profile = _profile(u)
    return {
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'is_active': u.is_active,
        'profile': {'phone': profile.phone, 'dob': dt(profile.dob)} if profile else None,
        # `{{ gc }}` printed None for a course without an admin_course
        'custom_generated_courses': ['None' if t is None else str(t) for t in u.custom_generated_courses],
    }


class UsersView(AdminAPIView):
    def get(self, request):
        return Response({'users': [_user_row(u) for u in ctx.build_user_management_context()['users']]})

    def post(self, request):
        try:
            message = ctx.user_management_action(request.data)
        except ctx.UserActionError as exc:
            return Response({'ok': False, 'error': str(exc)}, status=400)
        if not message:
            return Response({'ok': False, 'error': 'Invalid action.'}, status=400)
        return Response(ok(message, redirect='/user_management/'))


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def _report_row(r):
    student = r.student
    return {
        'id': r.id,
        'student_name': (student.get_full_name() or student.username) if student else '',
        'course_name': r.course_name,
        'problem_type': r.problem_type,
        'problem_type_display': display(r, 'problem_type') or r.problem_type,
        'problem_title': r.problem_title,
        'problem_description': r.problem_description,
        'status': r.status,
        'created_at': dt(r.created_at),
    }


class ReportsView(AdminAPIView):
    def get(self, request):
        c = ctx.build_admin_reports_context()
        return Response({
            'reports': [_report_row(r) for r in c['reports']],
            'total_submissions': c['total_submissions'],
            'pending_reports': c['pending_reports'],
            'reviewed_reports': c['reviewed_reports'],
            'active_today': c['active_today'],
        })


class ReportRespondView(AdminAPIView):
    def post(self, request, report_id):
        message = ctx.respond_to_report(report_id, request.data)
        return Response(ok(message, redirect='/admin_reports/'))


class ReportDeleteView(AdminAPIView):
    def post(self, request, report_id):
        return Response(ok(ctx.delete_report_by_id(report_id), redirect='/admin_reports/'))


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
class NotificationsView(AdminAPIView):
    def get(self, request):
        c = ctx.build_admin_notifications_context()
        return Response({
            'students_list': [
                {'id': s.id, 'username': s.username, 'get_full_name': s.get_full_name()}
                for s in c['students_list']
            ],
            'dispatch_history': [
                {
                    'id': n.id,
                    'subject_heading': n.subject_heading,
                    'get_target_recipient_display': display(n, 'target_recipient'),
                    'get_category_type_display': display(n, 'category_type'),
                    'created_at': dt(n.created_at),
                }
                for n in c['dispatch_history']
            ],
        })

    def post(self, request):
        message = ctx.dispatch_admin_notification(request.data)
        if not message:
            # The template view re-rendered the page without sending anything.
            return Response({'ok': False, 'errors': {'notification_body': ['This field is required.']}}, status=400)
        return Response(ok(message, redirect='/admin_notifications/'))


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
class AnalyticsView(AdminAPIView):
    def get(self, request):
        c = ctx.build_analytics_context()
        data = {k: v for k, v in c.items() if k != 'recent_activities'}
        data['recent_activities'] = [
            {
                'user': {'username': a['user'].username},
                'action_description': a['action_description'],
                'timestamp': dt(a['timestamp']),
            }
            for a in c['recent_activities']
        ]
        return Response(data)


# ---------------------------------------------------------------------------
# Avatar settings  (admin_db/admin_settings.html)
# ---------------------------------------------------------------------------
def _form_widgets(form):
    """The exact attributes Django rendered for each `{{ form.<field> }}` widget."""
    out = {}
    for name in form.fields:
        bf = form[name]
        widget = bf.field.widget
        attrs = bf.build_widget_attrs(widget.attrs, widget)
        if bf.auto_id and 'id' not in widget.attrs:
            attrs.setdefault('id', bf.auto_id)
        w = widget.get_context(bf.html_name, bf.value(), attrs)['widget']
        out[name] = {
            'name': w['name'],
            'type': w['type'],
            'value': w['value'],
            'attrs': {k: v for k, v in w['attrs'].items() if v is not False},
            'id_for_label': bf.id_for_label,
        }
    return out


def _avatar_payload(form, avatar_settings):
    c = ctx.build_avatar_settings_context(form, avatar_settings)
    s = c['avatar_settings']
    asset = c['asset_status']
    return {
        'form': _form_widgets(form),
        'avatar_settings': {
            'avatar_name': s.avatar_name,
            'developer_name': s.developer_name,
            'university_or_department': s.university_or_department,
            'get_spoken_name': s.get_spoken_name(),
        },
        'asset_status': {
            'avatar_dir': asset['avatar_dir'],
            'all_exist': asset['all_exist'],
            'none_exist': asset['none_exist'],
            'has_idle': asset['has_idle'],
            'present_count': asset['present_count'],
            'total_required': asset['total_required'],
            'missing_files': asset['missing_files'],
            'file_status': {
                k: {'filename': v['filename'], 'exists': v['exists'], 'url': v['url']}
                for k, v in asset['file_status'].items()
            },
        },
    }


class AvatarSettingsView(AdminAPIView):
    def get(self, request):
        avatar_settings = AvatarSettings.get_settings()
        return Response(_avatar_payload(AvatarSettingsForm(instance=avatar_settings), avatar_settings))

    def post(self, request):
        avatar_settings = AvatarSettings.get_settings()
        form = AvatarSettingsForm(request.data, instance=avatar_settings)
        if form.is_valid():
            form.save()
            return Response(ok(
                f"Avatar settings for '{avatar_settings.avatar_name}' updated successfully!",
                redirect='/admindashboard/avatar-settings/',
            ))
        payload = _avatar_payload(form, avatar_settings)
        payload.update({
            'ok': False,
            'errors': form_errors(form),
            'messages': [{'tags': 'error', 'message': 'Please correct the errors in the form below.'}],
        })
        return Response(payload, status=400)


urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='api_admin_dashboard'),
    path('users/', UsersView.as_view(), name='api_admin_users'),
    path('reports/', ReportsView.as_view(), name='api_admin_reports'),
    path('reports/<int:report_id>/respond/', ReportRespondView.as_view(), name='api_admin_report_respond'),
    path('reports/<int:report_id>/delete/', ReportDeleteView.as_view(), name='api_admin_report_delete'),
    path('notifications/', NotificationsView.as_view(), name='api_admin_notifications'),
    path('analytics/', AnalyticsView.as_view(), name='api_admin_analytics'),
    path('avatar-settings/', AvatarSettingsView.as_view(), name='api_admin_avatar_settings'),
]
