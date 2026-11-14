"""
Context builders / actions for the student pages (dashboard home, assessment, profile,
notifications, reports, performance, settings).

Shared by the legacy template views in views.py and the JSON API in api/student.py, so the
business logic lives in exactly one place.
"""

import logging

from django.conf import settings

from ..certificate_service import calculate_course_performance, update_or_create_student_certificate
from ..models import (
    AdminCourse,
    AssignmentSubmission,
    DailyLesson,
    GeneratedCourse,
    Profile,
    QuizSubmission,
    Report,
    StudentAssessment,
    StudentNotificationStatus,
    UserSettings,
    generate_unique_student_id,
)

logger = logging.getLogger('alvixapp.views')


# ---------------------------------------------------------------------------
# Dashboard home
# ---------------------------------------------------------------------------
def dashboard_requires_assessment(user):
    """Non-staff students must finish the assessment before seeing the dashboard."""
    profile_obj, _ = Profile.objects.get_or_create(user=user)
    if not user.is_staff and not user.is_superuser:
        if not profile_obj.assessment_completed:
            return True
    return False


def build_dashboard_context(request):
    # Fetch only the courses specifically chosen/enrolled by this student
    generated_courses = GeneratedCourse.objects.filter(user=request.user).select_related('admin_course', 'course_level').order_by('id')
    # Same course as the Performance page (the newest enrolment), so both pages agree.
    active_course = GeneratedCourse.objects.filter(user=request.user).select_related('admin_course').order_by('-created_at').first()

    # Performance comes from the same scoring engine as the Performance page and the certificate
    # (certificate_service.calculate_course_performance: 20% watch time, 40% assignment, 40% quiz
    # per day). It used to be a separate 40/30/30 estimate that never matched the student's record.
    perf = None
    if active_course:
        try:
            perf = calculate_course_performance(request.user, active_course)
        except Exception:  # scoring must never break the dashboard
            logger.exception('Course performance failed for user %s', request.user.pk)

    if perf:
        overall_score = perf['overall_percentage']  # same value (1 decimal) as the Performance page
        grade = perf['performance_grade']
        certificate_unlocked = bool(perf['certificate_unlocked'])
        days = perf['day_evaluations']
        total_days = perf['total_days'] or 1
        weights = getattr(settings, 'DAY_SCORE_WEIGHTS', {'watch_time': 0.20, 'assignment': 0.40, 'quiz': 0.40})

        def contribution(key, weight_key):
            return sum(d[key] for d in days) / total_days * weights.get(weight_key, 0)

        course_title = active_course.admin_course.title if active_course.admin_course else "your course"
        ai_remarks = (
            f"Progress status for {course_title}: Watch Time contributed {contribution('watch_time_percentage', 'watch_time'):.1f}%, "
            f"Assignments contributed {contribution('assignment_percentage', 'assignment'):.1f}%, and Quizzes contributed "
            f"{contribution('quiz_percentage', 'quiz'):.1f}%. Your overall course score is {perf['overall_percentage']}% "
            f"({perf['completed_days_count']} of {perf['total_days']} days completed)."
        )
    else:
        overall_score = 0
        grade = "Needs Improvement" if active_course else "Beginner"
        certificate_unlocked = False
        ai_remarks = "No active course found. Generate a course to begin tracking your analytics."

    # Ensure student has profile and student_id
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    if not profile_obj.student_id:
        profile_obj.student_id = generate_unique_student_id()
        profile_obj.save()

    # Recommended course for dashboard banner/alert if no course started yet
    suggested_course = None
    latest_assessment = StudentAssessment.objects.filter(user=request.user).order_by('-created_at').first()
    if latest_assessment and latest_assessment.interest:
        suggested_course = latest_assessment.interest
    elif not generated_courses.exists():
        suggested_course = AdminCourse.objects.filter(is_active=True).first()

    # Newest unread announcement for this student (shown as the dashboard announcement card).
    popup_status = (
        StudentNotificationStatus.objects
        .filter(user=request.user, is_read=False, notification__is_dispatched=True)
        .select_related('notification')
        .order_by('-notification__created_at')
        .first()
    )
    popup_notification = popup_status.notification if popup_status else None

    return {
        'active_course': active_course,
        'certificate_unlocked': certificate_unlocked,
        'generated_courses': generated_courses,
        'overall_progress': overall_score,
        'grade': grade,
        'ai_remarks': ai_remarks,
        'popup_notification': popup_notification,
        'suggested_course': suggested_course,
        'latest_assessment': latest_assessment,
    }


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------
ASSESSMENT_ERROR_MESSAGE = "Please ensure all fields are filled out correctly (Expectations requires at least 20 characters)."


def assessment_is_retake(request, profile_obj):
    return request.GET.get('retake') == 'true' or profile_obj.assessment_completed


def assessment_initial(profile_obj):
    """Pre-populate with existing values if retaking or already set."""
    initial_data = {}
    if profile_obj.interest_area:
        initial_data['interest_area'] = profile_obj.interest_area
    if profile_obj.goal:
        initial_data['goal'] = profile_obj.goal
    if profile_obj.expectations:
        initial_data['expectations'] = profile_obj.expectations
    return initial_data


def save_student_assessment(request, form, profile_obj, is_retake):
    """Runs the valid-form branch of the assessment view. Returns the success message."""
    from ..views import find_best_matching_admin_course

    interest_area = form.cleaned_data['interest_area']
    goal = form.cleaned_data['goal']
    expectations = form.cleaned_data['expectations']

    # Save directly into student profile
    profile_obj.interest_area = interest_area
    profile_obj.goal = goal
    profile_obj.expectations = expectations
    profile_obj.assessment_completed = True
    profile_obj.save()

    # Find 1 best matching course from database
    suggested_course = find_best_matching_admin_course(interest_area, purpose=goal)

    # Synchronize with StudentAssessment record for backward compatibility
    StudentAssessment.objects.create(
        user=request.user,
        student_id=profile_obj.student_id,
        full_name=profile_obj.full_name or request.user.get_full_name() or request.user.username,
        email=request.user.email,
        interest=suggested_course,
        interest_topic=interest_area,
        learning_goal=goal,
        expectations=expectations,
        selected_course=suggested_course.title if suggested_course else None
    )

    # Set session parameters
    request.session['student_name'] = profile_obj.full_name
    request.session['student_id'] = profile_obj.student_id
    request.session['assessment_interest'] = interest_area
    request.session['assessment_purpose'] = goal
    if suggested_course:
        request.session['recommended_course_id'] = suggested_course.id

    # Generate AI Recommendation using ALL assessment answers
    from ..course_recommendation import suggest_best_fit_course_with_ai
    suggested_course, reason, suggested_level = suggest_best_fit_course_with_ai(
        user=request.user,
        interest_area=interest_area,
        goal=goal,
        expectations=expectations
    )
    if suggested_course:
        request.session['recommended_course_id'] = suggested_course.id
        request.session['ai_suggestion_reason'] = reason
        request.session['ai_suggested_level'] = suggested_level

    if is_retake:
        return "Assessment updated successfully! Review your AI-suggested learning paths below."
    return "Assessment complete! Review your AI-suggested learning paths below."


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
def save_profile(request, data, files):
    """POST branch of the profile view.

    `goal` is only updated when the form actually sends it: the profile template has no goal
    input, and assigning None to the NOT NULL column made every save crash.
    """
    from django.contrib.auth.models import User
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email
    from ..upload_safety import UploadRejected, validate_image

    # Validate before changing anything (raises UploadRejected with a user-facing message).
    new_email = (data.get("email") or "").strip()
    if new_email:
        try:
            validate_email(new_email)
        except ValidationError:
            raise UploadRejected("Please enter a valid email address.")
        if User.objects.filter(email__iexact=new_email).exclude(pk=request.user.pk).exists():
            raise UploadRejected("An account with this email already exists.")
    if files.get("profile_picture"):
        validate_image(files["profile_picture"])

    profile_obj, _ = Profile.objects.get_or_create(user=request.user)

    profile_obj.full_name = data.get("full_name")
    if "phone" in data:  # NOT NULL column: only update when the form sends it
        profile_obj.phone = data.get("phone") or ""
    if "goal" in data:
        profile_obj.goal = data.get("goal")
    profile_obj.gender = data.get("gender")

    dob = data.get("dob")
    if dob:
        profile_obj.dob = dob

    if files.get("profile_picture"):
        profile_obj.profile_picture = files["profile_picture"]

    profile_obj.save()

    if new_email:  # an empty/missing email keeps the current one (it used to be set to None)
        request.user.email = new_email
        request.user.save(update_fields=['email'])
    return profile_obj


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
def build_notifications_context(request):
    # Fetch all dispatched notifications for the logged-in student via StudentNotificationStatus
    notifications = StudentNotificationStatus.objects.filter(
        user=request.user,
        notification__is_dispatched=True
    ).select_related('notification').order_by('-notification__created_at')
    return {'notifications': notifications}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
REPORT_SUCCESS_MESSAGE = "Aapki report successfully submit ho gayi hai!"


def save_report(request, form):
    report = form.save(commit=False)
    report.student = request.user
    report.save()
    return report


def student_reports(user):
    return Report.objects.filter(student=user).order_by('-created_at')


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------
def build_performance_context(request):
    active_course = GeneratedCourse.objects.filter(user=request.user).order_by('-created_at').first()
    if not active_course:
        return {'performance': None}

    perf = calculate_course_performance(request.user, active_course)

    # Ensure certificate record is synchronized
    cert, _ = update_or_create_student_certificate(request.user, active_course, request=request)

    # Remaining requirement calculations
    remaining_lessons = max(0, perf['total_days'] - perf['completed_days_count'])
    score_gap = max(0.0, round(perf['pass_mark'] - perf['overall_percentage'], 1))

    return {
        'performance': perf,
        'active_course': active_course,
        'certificate': cert,
        'remaining_lessons': remaining_lessons,
        'score_gap': score_gap,
    }


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
def get_user_settings(user):
    user_settings, _ = UserSettings.objects.get_or_create(user=user)
    return user_settings
