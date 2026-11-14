"""Shared context builders / actions for the admin core pages.

Used by both the legacy template views in ``views.py`` and the JSON API in
``api/admin.py`` so the two never drift apart.
"""

from django.contrib.auth.models import User
from django.db.models import Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone

from ..models import (
    AdminCourse,
    AssignmentSubmission,
    GeneratedCourse,
    Notification,
    Profile,
    QuizSubmission,
    Report,
    StudentNotificationStatus,
)


# ---------------------------------------------------------------------------
# Admin dashboard home
# ---------------------------------------------------------------------------
def build_admin_dashboard_context():
    return {
        'total_courses': AdminCourse.objects.count(),
        'total_students': User.objects.filter(is_staff=False).count(),
        'total_enrollments': GeneratedCourse.objects.count(),
        'recent_courses': AdminCourse.objects.all().order_by('-id')[:6],
        'recent_enrollments': GeneratedCourse.objects.select_related('user', 'admin_course', 'course_level').order_by('-created_at')[:8],
        'pending_reports_count': Report.objects.filter(status='pending').count(),
    }


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------
def build_user_management_context():
    users = list(User.objects.all().order_by('-date_joined'))
    for u in users:
        u.custom_generated_courses = list(
            GeneratedCourse.objects.filter(user=u)
            .select_related('admin_course')
            .values_list('admin_course__title', flat=True)
            .distinct()
        )
    return {'users': users}


class UserActionError(Exception):
    """A user-management edit that can't be applied (e.g. username already taken)."""


def user_management_action(data):
    """POST `action=edit|delete` + `user_id` (+ edit fields). Returns the success
    message, or None when the action/user_id is missing (the view then just renders
    the page). Raises Http404 for an unknown user and UserActionError for a username
    or email that belongs to another account (previously an IntegrityError / 500)."""
    action = (data.get('action') or '').strip()
    user_id = data.get('user_id')
    if action == 'edit' and user_id:
        target_user = get_object_or_404(User, id=user_id)
        new_username = (data.get('username') or '').strip()
        new_email = (data.get('email') or '').strip()
        new_phone = (data.get('phone') or '').strip()
        new_dob = (data.get('dob') or '').strip()
        new_password = (data.get('password') or '').strip()

        others = User.objects.exclude(id=target_user.id)
        if new_username and others.filter(username__iexact=new_username).exists():
            raise UserActionError("That username is already taken. Please choose another one.")
        if new_email and others.filter(email__iexact=new_email).exists():
            raise UserActionError("Another account already uses this email address.")

        if new_username:
            target_user.username = new_username
        if new_email:
            target_user.email = new_email
        if new_password:
            target_user.set_password(new_password)
        target_user.save()

        profile_obj, _ = Profile.objects.get_or_create(user=target_user)
        if new_phone:
            profile_obj.phone = new_phone
        if new_dob:
            try:
                profile_obj.dob = new_dob
            except Exception:
                pass
        profile_obj.save()
        return f"User {target_user.username} updated successfully!"

    if action == 'delete' and user_id:
        return delete_user_by_id(user_id)
    return None


def delete_user_by_id(user_id):
    target_user = get_object_or_404(User, id=user_id)
    username = target_user.username
    target_user.delete()
    return f"User {username} deleted successfully."


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
def build_analytics_context():
    total_assignments = AssignmentSubmission.objects.count()

    top_performing_courses = []
    for c in AdminCourse.objects.all():
        enrollments = GeneratedCourse.objects.filter(admin_course=c)
        # Rating (0-5): average QuizSubmission.percentage over every quiz submitted in this
        # course's generated instances, scaled to 5 and rounded to 1 decimal (0.0 = no quizzes yet).
        avg_quiz = QuizSubmission.objects.filter(
            lesson__generated_course__admin_course=c
        ).aggregate(avg=Avg('percentage'))['avg']
        top_performing_courses.append({
            'title': c.title,
            'enrolled_count': enrollments.count(),
            'student_count': enrollments.values('user').distinct().count(),
            'rating': round((avg_quiz or 0) / 20.0, 1),
            'completion_rate': 85.0,
        })
    # "Top performing": highest rating first, then most students (stable for ties).
    top_performing_courses.sort(key=lambda t: (t['rating'], t['student_count']), reverse=True)
    top_performing_courses = top_performing_courses[:5]

    recent_activities = []
    for sub in AssignmentSubmission.objects.select_related('user', 'lesson').order_by('-submitted_at')[:6]:
        recent_activities.append({
            'user': sub.user,
            'action_description': f"submitted assignment for {sub.lesson.title if sub.lesson else 'Lesson'}",
            'timestamp': sub.submitted_at,
        })

    return {
        'total_courses': AdminCourse.objects.count(),
        'total_students': User.objects.filter(is_staff=False).count(),
        'total_enrollments': GeneratedCourse.objects.count(),
        'total_assignments': total_assignments,
        'total_quizzes': QuizSubmission.objects.count(),
        'completion_rate': 82.5,
        # Plain numbers: the template appends "%" to build the bar width ("96%%" was invalid).
        'student_satisfaction': 96,
        'top_performing_courses': top_performing_courses,
        'assignment_submissions': total_assignments,
        'quiz_performance': 84,
        'recent_activities': recent_activities,
    }


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
def build_admin_notifications_context():
    return {
        'students_list': User.objects.filter(is_staff=False).order_by('username'),
        'dispatch_history': Notification.objects.all().order_by('-created_at')[:20],
    }


def dispatch_admin_notification(data):
    """Returns the success message, or None when there is no body (nothing sent)."""
    target_recipient = data.get('target_recipient', 'all_students')
    category_type = data.get('category_type', 'announcement')
    subject_heading = (data.get('subject_heading') or '').strip() or (data.get('title') or 'Admin Notice').strip()
    notification_body = (data.get('notification_body') or '').strip() or (data.get('message') or '').strip()
    specific_student_id = data.get('specific_student_id') or data.get('student_id')

    if not notification_body:
        return None

    recipient_user = None
    if target_recipient == 'specific_student' and specific_student_id and str(specific_student_id).isdigit():
        recipient_user = User.objects.filter(id=int(specific_student_id)).first()

    notification = Notification.objects.create(
        target_recipient=target_recipient,
        category_type=category_type,
        subject_heading=subject_heading or 'Notice from ALVIX Administration',
        notification_body=notification_body,
        recipient_user=recipient_user,
        is_dispatched=True
    )

    if target_recipient == 'enrolled_students':
        enrolled_user_ids = GeneratedCourse.objects.values_list('user_id', flat=True).distinct()
        for uid in enrolled_user_ids:
            u = User.objects.filter(id=uid).first()
            if u:
                StudentNotificationStatus.objects.get_or_create(user=u, notification=notification)

    if target_recipient == 'specific_student' and recipient_user:
        return f"Notification sent to {recipient_user.username}!"
    return "Broadcast notification dispatched to students!"


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def build_admin_reports_context():
    reports = Report.objects.select_related('student').order_by('-created_at')
    today = timezone.now().date()
    return {
        'reports': reports,
        'total_submissions': reports.count(),
        'pending_reports': reports.filter(status='pending').count(),
        'reviewed_reports': reports.filter(status='resolved').count(),
        'active_today': reports.filter(created_at__date=today).count(),
    }


def respond_to_report(report_id, data):
    """Returns the success message, or None when the response text is empty."""
    report = get_object_or_404(Report, id=report_id)
    response_text = (data.get('feedback') or '').strip() or (data.get('response') or '').strip()
    if not response_text:
        return None
    report.status = 'resolved'
    report.save()
    if report.student:
        Notification.objects.create(
            target_recipient='specific_student',
            recipient_user=report.student,
            category_type='announcement',
            subject_heading=f'Response to Report #{report.id}',
            notification_body=f'Admin Response: {response_text}\n\nYour issue has been marked as resolved.',
            is_dispatched=True
        )
    return f'Response delivered to student for Report #{report.id}!'


def delete_report_by_id(report_id):
    report = get_object_or_404(Report, id=report_id)
    report.delete()
    return f'Report #{report_id} deleted successfully.'


# ---------------------------------------------------------------------------
# Avatar settings
# ---------------------------------------------------------------------------
def build_avatar_settings_context(form, avatar_settings):
    from ..views import get_avatar_asset_status  # lazy: views imports this module

    return {
        'form': form,
        'avatar_settings': avatar_settings,
        'asset_status': get_avatar_asset_status(),
    }
