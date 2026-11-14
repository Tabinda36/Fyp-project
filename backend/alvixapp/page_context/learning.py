"""
Context builders / actions for the learning pages (my course, course content,
generate course, enroll level, current lesson, certificate).

Shared by the legacy template views in views.py and the /api/v1/learning/ API,
so both answer with exactly the same data and side effects.
"""

import logging
import os

from django.conf import settings
from django.shortcuts import get_object_or_404

from ..certificate_service import update_or_create_student_certificate
from ..course_tier_service import create_course_tiers_and_curriculum, fetch_and_enroll_student_in_level
from ..models import (
    AdminCourse,
    AssignmentSubmission,
    Certificate,
    CourseLevel,
    DailyLesson,
    GeneratedCourse,
    QuizSubmission,
    StudentAssessment,
)
from ..permissions import is_alvix_admin

logger = logging.getLogger(__name__)

MYCOURSE_TABS = ['content', 'lessons', 'assignment', 'quiz', 'overview']


def get_course_lessons(course):
    """Safe helper to fetch lessons across model schemas."""
    if not course:
        return []

    # 1. Direct Model Query (Most reliable)
    try:
        lessons = DailyLesson.objects.filter(generated_course=course).order_by('day_number')
        if lessons.exists():
            return lessons
    except Exception:
        pass

    # 2. Reverse Relation Fallbacks
    if hasattr(course, 'daily_lessons'):
        return course.daily_lessons.all().order_by('day_number')
    if hasattr(course, 'dailylesson_set'):
        return course.dailylesson_set.all().order_by('day_number')

    return DailyLesson.objects.none()


# ---------------------------------------------------------------------------
# My Course (/mycourse/ and /course/<id>/)
# ---------------------------------------------------------------------------
def build_mycourse_context(request):
    course_id = request.GET.get('course_id')
    user_courses = GeneratedCourse.objects.filter(user=request.user).select_related('admin_course', 'course_level').order_by('id')

    active_course = None
    if course_id and str(course_id).isdigit():
        active_course = user_courses.filter(id=int(course_id)).first()
    if not active_course:
        active_course = user_courses.first() or GeneratedCourse.objects.filter(user=request.user).order_by('-created_at').first()

    lessons = []
    content_topics = []
    today_lesson = None
    assignment_submissions = []
    quiz_submissions = []
    progress_percentage = 0
    certificate_obj = None

    if active_course:
        lessons = list(active_course.daily_lessons.all().order_by('day_number'))
        if not lessons:
            lessons = list(get_course_lessons(active_course))

        content_topics = active_course.content_topics or (active_course.course_level.content_topics if active_course.course_level else [])
        if not content_topics:
            from ..ai_services import get_curated_level_content_and_plan
            title = active_course.admin_course.title if active_course.admin_course else "Course"
            lvl_name = active_course.level or "Beginner"
            ctype = active_course.course_type or "Mixed"
            curated_topics, _ = get_curated_level_content_and_plan(title, lvl_name, ctype)
            content_topics = curated_topics
            active_course.content_topics = content_topics
            try:
                active_course.save(update_fields=['content_topics'])
            except Exception:
                pass

        for l in lessons:
            if l.is_unlocked and not l.is_completed:
                today_lesson = l
                break
        if not today_lesson:
            today_lesson = (
                active_course.daily_lessons.filter(is_unlocked=True).last()
                or (lessons[0] if lessons else None)
            )

        try:
            assignment_submissions = list(
                AssignmentSubmission.objects.filter(user=request.user, lesson__in=lessons)
                .select_related('lesson')
                .order_by('-submitted_at')
            )
        except Exception:
            assignment_submissions = []

        try:
            quiz_submissions = list(
                QuizSubmission.objects.filter(user=request.user, lesson__in=lessons)
                .select_related('lesson')
                .order_by('-submitted_at')
            )
        except Exception:
            quiz_submissions = []

        total_lessons = len(lessons)
        total_video_duration = 0
        total_watch_time = 0
        total_assignment_score_obtained = 0
        total_assignment_max_score = 0
        total_quiz_score_obtained = 0
        total_quiz_max_score = 0

        watch_time_percentage = 0
        assignment_percentage = 0
        quiz_percentage = 0

        if total_lessons > 0:
            for lesson in lessons:
                vid_len = getattr(lesson, 'duration', 25)
                w_time = getattr(lesson, 'watch_time', 25 if getattr(lesson, 'is_completed', False) else 0)
                total_video_duration += vid_len
                total_watch_time += min(w_time, vid_len)

            watch_time_percentage = (total_watch_time / total_video_duration * 100) if total_video_duration > 0 else 0

            for sub in assignment_submissions:
                obtained = getattr(sub, 'marks', getattr(sub, 'score', 10))
                max_m = getattr(sub, 'total_marks', 10)
                total_assignment_score_obtained += obtained
                total_assignment_max_score += max_m

            if total_assignment_max_score == 0 and len(assignment_submissions) > 0:
                total_assignment_max_score = len(assignment_submissions) * 10
            assignment_percentage = (total_assignment_score_obtained / total_assignment_max_score * 100) if total_assignment_max_score > 0 else 0

            for quiz in quiz_submissions:
                obtained = getattr(quiz, 'score', getattr(quiz, 'marks_obtained', 0))
                max_m = getattr(quiz, 'total_marks', 3)
                total_quiz_score_obtained += obtained
                total_quiz_max_score += max_m

            if total_quiz_max_score == 0 and len(quiz_submissions) > 0:
                total_quiz_max_score = len(quiz_submissions) * 3
            quiz_percentage = (total_quiz_score_obtained / total_quiz_max_score * 100) if total_quiz_max_score > 0 else 0

            weighted_score = (watch_time_percentage * 0.4) + (assignment_percentage * 0.3) + (quiz_percentage * 0.3)
            progress_percentage = int(round(weighted_score))

        certificate_obj = Certificate.objects.filter(user=request.user, course=active_course).first()

    active_tab = request.GET.get('tab', 'content').strip().lower()
    if active_tab not in MYCOURSE_TABS:
        active_tab = 'content'

    return {
        'active_course': active_course,
        'course': active_course,
        'user_courses': user_courses,
        'lessons': lessons,
        'content_topics': content_topics,
        'today_lesson': today_lesson,
        'assignment_submissions': assignment_submissions,
        'quiz_submissions': quiz_submissions,
        'progress_percentage': progress_percentage,
        'certificate': certificate_obj,
        'active_tab': active_tab,
    }


def build_course_detail_context(request, course_id):
    """Context of /course/<id>/ (same template, less context). None when the course is not the user's."""
    course = GeneratedCourse.objects.filter(id=course_id, user=request.user).first()
    if not course:
        return None

    lessons = get_course_lessons(course)

    return {
        'active_course': course,
        'course': course,
        'lessons': lessons,
    }


# ---------------------------------------------------------------------------
# Course content (/course_content/, /course-content/)
# ---------------------------------------------------------------------------
def build_course_content_context(request):
    """
    Renders active course syllabus and lessons.
    Self-healing: If an active course exists with 0 lessons, it automatically generates
    the 7-day curriculum via Gemini AI so the user never gets an empty screen.
    """
    course_id = request.GET.get('course_id')
    active_course = None

    if course_id and course_id.isdigit():
        active_course = GeneratedCourse.objects.filter(id=int(course_id), user=request.user).first()

    if not active_course:
        user_courses = GeneratedCourse.objects.filter(user=request.user).order_by('-created_at')
        for gc in user_courses:
            if gc.daily_lessons.exists():
                active_course = gc
                break
        if not active_course:
            active_course = user_courses.first()

    # Self-healing: If course has 0 lessons, fetch pre-generated curriculum directly from database
    if active_course and not active_course.daily_lessons.exists():
        try:
            target_level = active_course.course_level
            if not target_level and active_course.admin_course:
                target_level = CourseLevel.objects.filter(
                    parent_course=active_course.admin_course,
                    level__iexact=active_course.level or 'Beginner'
                ).first()
                if not target_level:
                    create_course_tiers_and_curriculum(active_course.admin_course)
                    target_level = CourseLevel.objects.filter(
                        parent_course=active_course.admin_course,
                        level__iexact=active_course.level or 'Beginner'
                    ).first() or CourseLevel.objects.filter(parent_course=active_course.admin_course).first()
            if target_level:
                fetch_and_enroll_student_in_level(request.user, target_level)
        except Exception as e:
            logger.error(f"Instant fetch lessons failed: {e}")

    lessons = []
    content_topics = []
    course_type = "Mixed"
    durations = getattr(settings, 'COURSE_PLAN_DURATIONS', {
        'Theoretical': 7,
        'Theory': 7,
        'Practical': 10,
        'Mixed': 12,
    })
    plan_duration = 12

    if active_course:
        course_type = active_course.course_type or (active_course.admin_course.course_type if active_course.admin_course else 'Mixed')
        plan_duration = durations.get(course_type, durations.get('Mixed', 12))

        content_topics = active_course.content_topics or (active_course.course_level.content_topics if active_course.course_level else [])
        if not content_topics and active_course.course_level:
            from ..course_tier_service import sync_student_lessons_from_canonical
            sync_student_lessons_from_canonical(active_course)
            active_course.refresh_from_db()
            content_topics = active_course.content_topics or (active_course.course_level.content_topics if active_course.course_level else [])

        if not content_topics:
            from ..ai_services import get_curated_level_content_and_plan
            title = active_course.admin_course.title if active_course.admin_course else "Course"
            lvl_name = active_course.level or "Beginner"
            curated_topics, _ = get_curated_level_content_and_plan(title, lvl_name, course_type)
            content_topics = curated_topics
            active_course.content_topics = content_topics
            try:
                active_course.save(update_fields=['content_topics'])
            except Exception:
                pass

        lessons = list(active_course.daily_lessons.all().order_by('day_number'))
        videos_dir = os.path.join(settings.MEDIA_ROOT, "videos")
        for l in lessons:
            v_name = f"lesson_{l.id}.mp4"
            p = os.path.join(videos_dir, v_name)
            l.has_real_video = os.path.exists(p) and os.path.getsize(p) > 10000
            if l.has_real_video and l.video_url != f"{settings.MEDIA_URL}videos/{v_name}":
                l.video_url = f"{settings.MEDIA_URL}videos/{v_name}"

    return {
        'active_course': active_course,
        'content_topics': content_topics,
        'course_type': course_type,
        'plan_duration': plan_duration,
        'lessons': lessons,
    }


# ---------------------------------------------------------------------------
# Generate course (/generate_course/)
# ---------------------------------------------------------------------------
def _available_courses():
    available_courses = AdminCourse.objects.filter(is_active=True).prefetch_related('course_levels')
    if not available_courses.exists():
        available_courses = AdminCourse.objects.all().prefetch_related('course_levels')
    return available_courses


def build_generate_course_context(request):
    available_courses = _available_courses()

    assessment = StudentAssessment.objects.filter(user=request.user).order_by('-created_at').first()
    if not assessment and request.user.is_authenticated:
        assessment = StudentAssessment.objects.filter(email__iexact=request.user.email).order_by('-created_at').first()

    suggested_courses = []
    if assessment and getattr(assessment, 'interest', None):
        suggested_courses = [assessment.interest]
    elif assessment and getattr(assessment, 'interest_topic', None):
        suggested_courses = list(AdminCourse.objects.filter(title__icontains=assessment.interest_topic)[:2])
    if not suggested_courses and available_courses.exists():
        suggested_courses = [available_courses.first()]

    for ac in available_courses:
        if not ac.course_levels.exists():
            create_course_tiers_and_curriculum(ac)

    all_course_levels = CourseLevel.objects.select_related('parent_course').filter(is_active=True).order_by('parent_course__title', 'id')

    return {
        'available_courses': available_courses,
        'suggested_courses': suggested_courses,
        'all_course_levels': all_course_levels,
        'assessment': assessment
    }


def perform_generate_course(user, data):
    """
    POST action of /generate_course/. `data` is request.POST (legacy) or request.data (API).
    Returns (ok, level, message, redirect_url) exactly like the original view's messages/redirects.
    """
    available_courses = _available_courses()

    level_slug = data.get('level_slug')
    level_id = data.get('level_id')
    user_level = data.get('level', 'Beginner')
    user_pace = data.get('pace', 'Standard (3-5 hours/week)')
    user_objective = data.get('objective', 'Skill Improvement')

    course_level = None
    if level_slug:
        course_level = CourseLevel.objects.select_related('parent_course').filter(slug=level_slug).first()
    elif level_id and str(level_id).isdigit():
        course_level = CourseLevel.objects.select_related('parent_course').filter(id=int(level_id)).first()

    if not course_level:
        course_input = (
            data.get('course_topic')
            or data.get('topic')
            or data.get('course_slug')
            or data.get('slug')
            or data.get('course_id')
            or data.get('course')
        )
        admin_course_instance = None
        if course_input:
            clean_input = str(course_input).strip()
            if clean_input.isdigit():
                admin_course_instance = AdminCourse.objects.filter(id=int(clean_input)).first()
            if not admin_course_instance:
                admin_course_instance = AdminCourse.objects.filter(course_code__iexact=clean_input).first()
            if not admin_course_instance:
                admin_course_instance = AdminCourse.objects.filter(slug__iexact=clean_input).first()
            if not admin_course_instance:
                admin_course_instance = AdminCourse.objects.filter(title__iexact=clean_input).first()

        if not admin_course_instance and available_courses.exists():
            admin_course_instance = available_courses.first()

        if admin_course_instance:
            clean_level = user_level.lower()
            if 'inter' in clean_level:
                target_level_name = 'Intermediate'
            elif 'adv' in clean_level:
                target_level_name = 'Advanced'
            else:
                target_level_name = 'Beginner'

            course_level = CourseLevel.objects.filter(parent_course=admin_course_instance, level__iexact=target_level_name).first()
            if not course_level:
                create_course_tiers_and_curriculum(admin_course_instance)
                course_level = CourseLevel.objects.filter(parent_course=admin_course_instance, level__iexact=target_level_name).first()

            if not course_level:
                course_level = CourseLevel.objects.filter(parent_course=admin_course_instance).first()

    if not course_level:
        return False, 'error', "Valid course level not found. Please choose a university-benchmarked course.", '/generate_course/'

    try:
        new_course = fetch_and_enroll_student_in_level(
            user=user,
            course_level=course_level,
            pace=user_pace,
            objective=user_objective
        )
        return (
            True,
            'success',
            f"Instant Access: Loaded '{course_level.title}' [{course_level.benchmark}] from database!",
            f"/course_content/?course_id={new_course.id}",
        )
    except Exception as e:
        logger.error(f"Course Fetch Enrollment Error: {str(e)}")
        return False, 'error', f"Enrollment Error: {str(e)}", '/generate_course/'


# ---------------------------------------------------------------------------
# Enroll level (/enroll-level/<slug>/)
# ---------------------------------------------------------------------------
def perform_enroll_level(user, slug):
    """Returns (message, redirect_url). Raises Http404 for an unknown slug."""
    course_level = get_object_or_404(CourseLevel, slug=slug)
    new_course = fetch_and_enroll_student_in_level(user=user, course_level=course_level)
    return (
        f"Successfully enrolled in {course_level.title} [{course_level.benchmark}]!",
        f"/course_content/?course_id={new_course.id}",
    )


# ---------------------------------------------------------------------------
# Current lesson (/daily_lesson/)
# ---------------------------------------------------------------------------
def resolve_current_lesson(request):
    """Returns (lesson_id, error_message). Exactly one of them is set."""
    lesson_id = request.GET.get('lesson_id')
    if lesson_id:
        return lesson_id, None
    active_course = GeneratedCourse.objects.filter(user=request.user).order_by('-created_at').first()
    if active_course:
        lesson = active_course.daily_lessons.filter(is_unlocked=True).last() or active_course.daily_lessons.first()
        if lesson:
            return lesson.id, None
    return None, "No active lesson found."


# ---------------------------------------------------------------------------
# Certificate (/certificate/, /certificate/<course_id>/)
# ---------------------------------------------------------------------------
def build_certificate_context(request, course_id=None):
    """
    Official ALVIX Certificate of Completion & Excellence.
    Unlocks when the student completes the course and overall percentage reaches pass mark (35%).
    Returns (locked, context): locked=True -> certificate_locked.html, else certificate.html.
    """
    if course_id:
        active_course = get_object_or_404(GeneratedCourse, id=course_id) if is_alvix_admin(request.user) else get_object_or_404(GeneratedCourse, id=course_id, user=request.user)
    else:
        active_course = GeneratedCourse.objects.filter(user=request.user).order_by('-created_at').first()

    if not active_course:
        return True, {
            'error': 'No active course found. Please enroll in a course to view your certificate.'
        }

    # The certificate always belongs to the course's student (an admin previewing someone
    # else's course must not get a certificate issued in the admin's own name).
    cert, perf = update_or_create_student_certificate(active_course.user, active_course, request=request)

    # `?preview=1` shows a locked certificate; only administrators may preview.
    is_staff_or_preview = is_alvix_admin(request.user)

    if not cert.is_unlocked and not is_staff_or_preview:
        remaining_lessons = max(0, perf['total_days'] - perf['completed_days_count'])
        score_gap = max(0.0, round(perf['pass_mark'] - perf['overall_percentage'], 1))
        return True, {
            'active_course': active_course,
            'performance': perf,
            'remaining_lessons': remaining_lessons,
            'score_gap': score_gap,
            'pass_mark': perf['pass_mark'],
            'current_score': perf['overall_percentage'],
        }

    return False, {
        'active_course': active_course,
        'certificate': cert,
        'performance': perf,
        # certificate.html also reads a bare `certificate_id` (security code + verify links);
        # it was never provided, which made the unlocked page raise NoReverseMatch.
        'certificate_id': cert.certificate_id,
        # bare names used as `|default:` fallbacks by certificate.html (must resolve)
        'student_name': cert.student_name,
        'student_email': cert.student_email,
        'student_id': getattr(getattr(active_course.user, 'profile', None), 'student_id', '') or '',
        'course_title': cert.course_name,
        'percentage': cert.overall_percentage,
        'grade': cert.performance_grade,
        'ai_remarks': cert.ai_review,
    }
