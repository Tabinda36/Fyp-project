"""Shared context/action builders for the admin course-management pages.

Used by both the legacy template views in `views.py` and the JSON API in
`api/admin_courses.py`, so the two always produce the same data.
"""

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.text import slugify

from ..course_tier_service import create_course_tiers_and_curriculum
from ..models import (
    AcademicLesson,
    AdminCourse,
    CourseLevel,
    CourseModule,
    DailyLesson,
    GeneratedCourse,
    PresentationSlide,
    Profile,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def course_plan_duration(course_type):
    """'7 Days' / '10 Days' / '12 Days' from settings.COURSE_PLAN_DURATIONS (Mixed when unknown)."""
    durations = getattr(settings, 'COURSE_PLAN_DURATIONS', {'Theoretical': 7, 'Theory': 7, 'Practical': 10, 'Mixed': 12})
    days = durations.get(course_type or 'Mixed') or durations.get('Mixed', 12)
    return f"{days} Days"


def enrollment_row(generated_course):
    """One student row of the enrollment tables (course_details, level_users_telemetry).

    Counts come from `certificate_service.calculate_course_performance`, i.e. the student's
    own DailyLessons plus their AssignmentSubmission/QuizSubmission records. `progress` is the
    share of plan days completed (int 0-100), matching the "(completed/total)" shown next to it.
    """
    from ..certificate_service import calculate_course_performance

    user = generated_course.user
    perf = calculate_course_performance(user, generated_course)
    total_days = perf['total_days']
    completed = min(perf['completed_days_count'], total_days)
    progress = int(round(completed / total_days * 100)) if total_days else 0
    profile = Profile.objects.filter(user=user).first()

    return {
        'id': generated_course.id,
        'user': user,
        'full_name': (profile.full_name if profile and profile.full_name else '') or user.get_full_name() or user.username,
        'student_id': (profile.student_id if profile else '') or '',
        'email': user.email or '',
        'attempted_assignments': perf['total_assignments_submitted'],
        'total_assignments': total_days,
        'attempted_quizzes': perf['total_quizzes_submitted'],
        'total_quizzes': total_days,
        'progress': progress,
        'completed_lessons': completed,
        'total_lessons': total_days,
        'status': 'Completed' if perf['is_course_completed'] else 'Active',
        'enrolled_at': generated_course.created_at,
    }


# ---------------------------------------------------------------------------
# courses_info
# ---------------------------------------------------------------------------
def build_courses_info_context(request):
    search_query = request.GET.get('search', '').strip()
    tier_filter = request.GET.get('tier', '').strip()

    levels = CourseLevel.objects.select_related('parent_course').filter(is_active=True)
    if search_query:
        levels = levels.filter(Q(title__icontains=search_query) | Q(parent_course__title__icontains=search_query))
    if tier_filter:
        levels = levels.filter(level__iexact=tier_filter)

    level_cards = []
    for lvl in levels:
        parent = lvl.parent_course
        enrolled_count = GeneratedCourse.objects.filter(course_level=lvl).values('user').distinct().count()
        total_lessons = AcademicLesson.objects.filter(course_level=lvl).count()
        # Levels without a deep curriculum yet still have their canonical day-by-day lessons.
        lessons_count = total_lessons or DailyLesson.objects.filter(
            course_level=lvl, generated_course__isnull=True
        ).count()
        level_cards.append({
            'level': lvl.level,  # the tier string the template compares with 'Beginner'/'Intermediate'
            'title': lvl.title,
            'course_title': parent.title if parent else '',
            'parent_title': parent.title if parent else '',
            'image': parent.image if parent and parent.image else None,
            'level_code': lvl.level_code or '',
            'description': lvl.description or (parent.description if parent else ''),
            'duration': course_plan_duration(parent.course_type if parent else None),
            'lessons_count': lessons_count,
            'slug': lvl.slug,
            'tier': lvl.level,
            'benchmark': lvl.benchmark,
            'enrolled_count': enrolled_count,
            'total_modules': lvl.academic_modules.count(),
            'total_lessons': total_lessons,
            'total_slides': PresentationSlide.objects.filter(course_level=lvl).count(),
        })

    return {
        'level_cards': level_cards,
        'total_courses': AdminCourse.objects.count(),
        'total_cards': len(level_cards),
        'search_query': search_query,
        'tier_filter': tier_filter,
    }


# ---------------------------------------------------------------------------
# add_course (POST action)
# ---------------------------------------------------------------------------
def create_admin_course(post, files):
    """Create the master course + its 3 tiers. Returns (admin_course, message) or (None, None)
    when no title was given (the original view then just re-rendered the empty form)."""
    title = post.get('title', '').strip()
    course_code = post.get('course_code', '').strip()
    description = post.get('description', '').strip()
    image_file = files.get('image')

    if not title:
        return None, None

    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    while AdminCourse.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    admin_course = AdminCourse(
        title=title,
        slug=slug,
        description=description,
        is_active=True
    )
    if course_code:
        admin_course.course_code = course_code
    if image_file:
        admin_course.image = image_file
    admin_course.save()

    create_course_tiers_and_curriculum(admin_course)
    return admin_course, f"Course '{admin_course.title}' created and university tiers initialized!"


# ---------------------------------------------------------------------------
# course_details
# ---------------------------------------------------------------------------
def build_course_detail_context(slug):
    course = get_object_or_404(AdminCourse, slug=slug)
    if not course.course_levels.exists():
        create_course_tiers_and_curriculum(course)
    course_tiers = course.course_levels.all().order_by('id')
    enrollments = GeneratedCourse.objects.filter(admin_course=course).select_related('user', 'course_level').order_by('-created_at')
    enrolled_count = enrollments.values('user').distinct().count()

    total_modules = CourseModule.objects.filter(course_level__parent_course=course).count()
    total_lessons = AcademicLesson.objects.filter(course_level__parent_course=course).count()

    return {
        'course': course,
        'course_tiers': course_tiers,
        'enrollments': [enrollment_row(e) for e in enrollments],
        'enrolled_count': enrolled_count,
        'total_modules': total_modules,
        'total_lessons': total_lessons,
    }


# ---------------------------------------------------------------------------
# level_course_view (+ regenerate)
# ---------------------------------------------------------------------------
def get_course_level(slug):
    return get_object_or_404(CourseLevel.objects.select_related('parent_course'), slug=slug)


def regenerate_message(course_level):
    return f"Deep university curriculum regenerated for {course_level.title} [{course_level.benchmark}]!"


def regenerate_level_curriculum(course_level):
    """Body of `admin_regenerate_deep_curriculum`. Returns the success message."""
    from ..deep_curriculum_service import generate_deep_university_curriculum
    generate_deep_university_curriculum(course_level, force=True, use_ai=True)
    return regenerate_message(course_level)


def prepare_level_detail(course_level, force_regen):
    """First half of `admin_course_level_detail`: (re)generate deep content when needed.
    Returns the success message when a forced regeneration happened (caller redirects to itself)."""
    has_deep_content = (
        CourseModule.objects.filter(course_level=course_level).exists() and
        PresentationSlide.objects.filter(course_level=course_level).exists()
    )

    if not has_deep_content or force_regen:
        from ..deep_curriculum_service import generate_deep_university_curriculum
        generate_deep_university_curriculum(course_level, force=force_regen, use_ai=True)
        if force_regen:
            return regenerate_message(course_level)
    return None


def build_level_detail_context(course_level):
    modules = CourseModule.objects.filter(course_level=course_level).prefetch_related('lessons').order_by('order')
    all_lessons = AcademicLesson.objects.filter(course_level=course_level).select_related('module').order_by('module__order', 'order')
    all_slides = PresentationSlide.objects.filter(course_level=course_level).order_by('slide_number')
    daily_lessons = DailyLesson.objects.filter(course_level=course_level).order_by('day_number').select_related('task')
    enrolled_count = GeneratedCourse.objects.filter(
        Q(course_level=course_level) | (Q(admin_course=course_level.parent_course) & Q(level__iexact=course_level.level))
    ).values('user').distinct().count()

    return {
        'course_level': course_level,
        'parent_course': course_level.parent_course,
        'modules': modules,
        'total_modules': modules.count(),
        'all_lessons': all_lessons,
        'total_lessons': all_lessons.count(),
        'all_slides': all_slides,
        'total_slides': all_slides.count(),
        'daily_lessons': daily_lessons,
        'enrolled_count': enrolled_count,
    }


# ---------------------------------------------------------------------------
# level_users_telemetry
# ---------------------------------------------------------------------------
def build_level_users_context(slug):
    course_level = get_course_level(slug)
    enrollments = GeneratedCourse.objects.filter(
        Q(course_level=course_level) | (Q(admin_course=course_level.parent_course) & Q(level__iexact=course_level.level))
    ).select_related('user').order_by('-created_at')

    rows = [enrollment_row(e) for e in enrollments]

    # KPI cards: original definitions from the legacy view (unchanged semantics).
    # Completed = every daily lesson completed; In-Progress = at least one, not all;
    # Avg Cohort Progress = completed / enrolled * 100.
    total_enrolled = len(rows)
    completed_count = 0
    active_count = 0
    for e in enrollments:
        comp = e.daily_lessons.filter(is_completed=True).count()
        tot = e.daily_lessons.count()
        if tot > 0 and comp == tot:
            completed_count += 1
        elif comp > 0:
            active_count += 1
    avg_progress = round((completed_count / total_enrolled * 100), 1) if total_enrolled > 0 else 0.0

    return {
        'course_level': course_level,
        'parent_course': course_level.parent_course,
        'enrollments': rows,
        'total_enrolled': total_enrolled,
        'completed_count': completed_count,
        'active_count': active_count,
        'avg_progress': avg_progress,
    }


# ---------------------------------------------------------------------------
# admin_upload_lesson_ppt (POST action)
# ---------------------------------------------------------------------------
def upload_lesson_ppt(lesson, uploaded_file):
    """Returns (level, message) for the Django message the view shows.

    `process_lesson_ppt_upload` returns a dict ({'success', 'slides_count', ...}) and raises
    ValueError when nothing can be extracted; the old view unpacked it as a `(success, msg)`
    tuple, which crashed. Both shapes are accepted here.
    """
    from ..ppt_service import process_lesson_ppt_upload

    if not uploaded_file:
        return 'error', "Please select a PPTX file to upload."
    try:
        result = process_lesson_ppt_upload(lesson, uploaded_file)
    except ValueError as exc:
        return 'error', str(exc)

    if isinstance(result, tuple) and len(result) == 2:
        success, msg = result
    else:
        success = bool(result.get('success', True)) if isinstance(result, dict) else bool(result)
        count = result.get('slides_count', 0) if isinstance(result, dict) else 0
        msg = f"PPT uploaded and processed successfully ({count} slides)." if success else "PPT processing failed."
    return ('success' if success else 'error'), msg


def ppt_upload_redirect_url(lesson):
    if lesson.generated_course and lesson.generated_course.course_level and lesson.generated_course.course_level.slug:
        return reverse('admin_course_level_detail', kwargs={'slug': lesson.generated_course.course_level.slug})
    return reverse('admin_dashboard')
