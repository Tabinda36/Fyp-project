"""
alvixapp/certificate_service.py
Core engine for calculating daily and overall course scoring, tracking performance metrics,
evaluating passing criteria, generating targeted AI academic reviews, and maintaining
up-to-date Certificate records for enrolled students.
"""

import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from .models import (
    GeneratedCourse,
    DailyLesson,
    AssignmentSubmission,
    QuizSubmission,
    Certificate
)
from .qr_generator import generate_qr_base64_data_uri

logger = logging.getLogger(__name__)


def calculate_course_performance(user, generated_course):
    """
    Computes strict, transparent course scoring:
    - Course total is 100%.
    - Divided by number of plan days N (7, 10, or 12 days).
    - Each day's share (100 / N) is split:
        * 20% Lesson watch time
        * 40% Assignment marks
        * 40% Quiz marks
      (Weights configurable in settings.DAY_SCORE_WEIGHTS).
    Returns detailed per-day breakdown dictionary and overall course statistics.
    """
    lessons = DailyLesson.objects.filter(generated_course=generated_course).order_by('day_number')
    total_days = lessons.count()
    if total_days == 0:
        norm_type = getattr(generated_course, 'course_type', 'Mixed')
        durations = getattr(settings, 'COURSE_PLAN_DURATIONS', {'Theoretical': 7, 'Practical': 10, 'Mixed': 12})
        total_days = durations.get(norm_type, 10)

    weights = getattr(settings, 'DAY_SCORE_WEIGHTS', {
        'watch_time': 0.20,
        'assignment': 0.40,
        'quiz': 0.40,
    })
    w_watch = weights.get('watch_time', 0.20)
    w_assign = weights.get('assignment', 0.40)
    w_quiz = weights.get('quiz', 0.40)

    day_evaluations = []
    total_day_percentages = 0.0
    completed_days_count = 0
    total_watch_seconds = 0
    total_assignments_submitted = 0
    total_quizzes_submitted = 0

    for lesson in lessons:
        d_num = lesson.day_number
        req_seconds = getattr(lesson, 'required_watch_seconds', 180) or 180
        w_seconds = getattr(lesson, 'watch_time_seconds', 0)
        total_watch_seconds += w_seconds

        # 1. Watch Time Score (0 - 100%)
        # System only counts watch time while tab is visible and narration is actively playing
        watch_pct = min(100.0, (w_seconds / req_seconds * 100.0)) if req_seconds > 0 else 0.0

        # 2. Assignment Score (0 - 100%)
        # Latest submission for this lesson
        ast_sub = AssignmentSubmission.objects.filter(user=user, lesson=lesson).order_by('-submitted_at').first()
        if ast_sub:
            total_assignments_submitted += 1
            max_m = getattr(ast_sub, 'total_marks', 10) or 10
            obt_m = getattr(ast_sub, 'marks', getattr(ast_sub, 'score', 0))
            assign_pct = min(100.0, (obt_m / max_m * 100.0)) if max_m > 0 else 0.0
            ast_remarks = ast_sub.ai_feedback or f"Scored {obt_m}/{max_m} marks on laboratory rubric."
        else:
            assign_pct = 0.0
            obt_m = 0
            max_m = 10
            ast_remarks = "No submission received yet."

        # 3. Quiz Score (0 - 100%)
        quiz_sub = QuizSubmission.objects.filter(user=user, lesson=lesson).order_by('-submitted_at').first()
        if quiz_sub:
            total_quizzes_submitted += 1
            q_tot = getattr(quiz_sub, 'total_questions', 5) or 5
            q_score = getattr(quiz_sub, 'score', 0)
            quiz_pct = min(100.0, (q_score / q_tot * 100.0)) if q_tot > 0 else 0.0
            quiz_remarks = quiz_sub.ai_feedback or f"Scored {q_score}/{q_tot} ({quiz_pct:.0f}% accuracy)."
        else:
            quiz_pct = 0.0
            q_score = 0
            q_tot = 5
            quiz_remarks = "Diagnostic quiz pending."

        # Day total percentage (out of 100% for this day)
        day_score_pct = (watch_pct * w_watch) + (assign_pct * w_assign) + (quiz_pct * w_quiz)
        total_day_percentages += day_score_pct

        # Check if this day is considered completed (watch time met or assignment/quiz submitted)
        is_day_done = (lesson.is_completed or lesson.watch_time_completed or (ast_sub is not None and quiz_sub is not None))
        if is_day_done:
            completed_days_count += 1

        day_max = round(100.0 / total_days, 2)
        day_sc = round((day_score_pct / 100.0) * day_max, 2)
        w_sc = round((watch_pct / 100.0) * (day_max * w_watch), 2)
        a_sc = round((assign_pct / 100.0) * (day_max * w_assign), 2)
        q_sc = round((quiz_pct / 100.0) * (day_max * w_quiz), 2)

        day_evaluations.append({
            'day_number': d_num,
            'lesson_id': lesson.id,
            'title': lesson.title,
            'lesson_title': lesson.title,
            'watch_time_seconds': w_seconds,
            'required_watch_seconds': req_seconds,
            'watch_time_percentage': round(watch_pct, 1),
            'watch_time_pct': round(watch_pct, 1),
            'watch_time_score': w_sc,
            'assignment_submitted': ast_sub is not None,
            'assignment_marks': obt_m,
            'assignment_max_marks': max_m,
            'assignment_percentage': round(assign_pct, 1),
            'assignment_pct': round(assign_pct, 1),
            'assignment_score': a_sc,
            'assignment_remarks': ast_remarks,
            'assignment_copy_risk': getattr(ast_sub, 'copy_risk_level', 'Low') if ast_sub else 'N/A',
            'quiz_submitted': quiz_sub is not None,
            'quiz_score': q_score,
            'quiz_total': q_tot,
            'quiz_percentage': round(quiz_pct, 1),
            'quiz_pct': round(quiz_pct, 1),
            'quiz_score': q_sc,
            'quiz_remarks': quiz_remarks,
            'day_percentage': round(day_score_pct, 1),
            'day_score': day_sc,
            'day_share_of_course': day_max,
            'day_max_score': day_max,
            'remarks': f"{ast_remarks} | {quiz_remarks}" if (ast_sub or quiz_sub) else "No submissions recorded for today.",
            'is_completed': is_day_done
        })

    # Overall course percentage (0 - 100%)
    overall_percentage = round(total_day_percentages / total_days, 1) if total_days > 0 else 0.0

    # Determine Performance Grade
    if overall_percentage >= 90:
        grade = "A+ (Outstanding Honors)"
    elif overall_percentage >= 80:
        grade = "A (High Distinction)"
    elif overall_percentage >= 70:
        grade = "B (Merit Distinction)"
    elif overall_percentage >= 55:
        grade = "C (Satisfactory Competency)"
    elif overall_percentage >= 35:
        grade = "Pass (Certified Competency)"
    else:
        grade = "Needs Improvement"

    pass_mark = getattr(settings, 'COURSE_PASS_MARK', 35)
    is_course_completed = (completed_days_count >= total_days and total_days > 0)
    has_passed = (overall_percentage >= pass_mark)
    certificate_unlocked = (is_course_completed and has_passed)

    return {
        'total_days': total_days,
        'completed_days_count': completed_days_count,
        'is_course_completed': is_course_completed,
        'has_passed': has_passed,
        'is_passed': has_passed,
        'pass_mark': pass_mark,
        'certificate_unlocked': certificate_unlocked,
        'is_unlocked': certificate_unlocked,
        'overall_percentage': overall_percentage,
        'performance_grade': grade,
        'grade': grade,
        'remaining_lessons': max(0, total_days - completed_days_count),
        'score_gap': max(0.0, round(pass_mark - overall_percentage, 1)),
        'total_watch_seconds': total_watch_seconds,
        'total_assignments_submitted': total_assignments_submitted,
        'total_quizzes_submitted': total_quizzes_submitted,
        'day_evaluations': day_evaluations,
        'days': day_evaluations
    }


def topic_highlights(perf_data):
    """(strong_topics, weak_topics): titles of the best-scoring days (>= 60%) and the
    lowest-scoring days (< 65%), at most two each. Shared by the AI review and the
    Performance page's strengths / topics-to-review lists."""
    day_evals = perf_data.get('day_evaluations', [])
    sorted_days = sorted(day_evals, key=lambda d: d.get('day_percentage', 0), reverse=True)
    strong_topics = [d.get('title') for d in sorted_days[:2] if d.get('day_percentage', 0) >= 60]
    weak_topics = [d.get('title') for d in sorted_days[-2:] if d.get('day_percentage', 0) < 65]
    return [t for t in strong_topics if t], [t for t in weak_topics if t]


def generate_certificate_ai_review(user, generated_course, perf_data) -> str:
    """
    Synthesizes a short, actionable academic review paragraph highlighting
    student strengths, weak topics, and concrete forward-looking advice.
    """
    student_name = user.get_full_name() or user.username
    course_title = generated_course.admin_course.title if generated_course.admin_course else "Engineering Masterclass"

    # Identify strong and weak topics
    strong_topics, weak_topics = topic_highlights(perf_data)

    strengths_phrase = f"demonstrated strong mastery in {', '.join(strong_topics)}" if strong_topics else "exhibited steady commitment to computational foundations"
    weakness_phrase = f"boundary conditions and advanced nuances in {', '.join(weak_topics)}" if weak_topics else "further low-level architectural optimizations"

    overall_pct = perf_data.get('overall_percentage', 0)
    grade = perf_data.get('performance_grade', 'Pass')

    review = (
        f"Academic Review for {student_name}: Throughout {course_title}, {student_name} has achieved an overall "
        f"performance score of {overall_pct:.1f}% ({grade}). "
        f"Strengths: The student has {strengths_phrase}, evidencing clean problem deconstruction and defensive implementation practices. "
        f"Weak Topics: Opportunities for growth remain in {weakness_phrase}. "
        f"Advice: To prepare for elite industry environments, prioritize building automated regression suites before writing production code, "
        f"and rigorously benchmark memory profiles against heavy concurrent workloads."
    )
    return review


def update_or_create_student_certificate(user, generated_course, request=None):
    """
    Updates or creates the student's Certificate record.
    Reflects the latest duration, performance grade, and AI review.
    Can be run daily via scheduled background cron or on every submission.
    """
    perf = calculate_course_performance(user, generated_course)

    course_title = (
        generated_course.admin_course.title
        if generated_course.admin_course
        else generated_course.level + " Course"
    )
    course_level_str = generated_course.level or "All Levels"
    student_name = user.get_full_name() or user.username
    student_email = user.email or f"{user.username}@alvix.edu"

    # Dates & Duration
    start_date = generated_course.created_at.date()
    current_date = timezone.now().date()
    duration_days = max(1, (current_date - start_date).days + 1)

    # Unique Certificate ID: ALV-CERT-YEAR-COURSEID-USERID
    year = timezone.now().year
    cert_id = f"ALV-CERT-{year}-{generated_course.id:04d}-{user.id:04d}"

    # Build verification URL
    if request:
        base_url = request.build_absolute_uri('/')[:-1]
    else:
        base_url = "http://127.0.0.1:8000"
    verification_url = f"{base_url}/verify-certificate/{cert_id}/"

    # QR Code Data URI
    qr_data_uri = generate_qr_base64_data_uri(verification_url)

    # AI Academic Review
    ai_review = generate_certificate_ai_review(user, generated_course, perf)

    cert, _ = Certificate.objects.update_or_create(
        user=user,
        course=generated_course,
        defaults={
            'certificate_id': cert_id,
            'is_unlocked': perf['certificate_unlocked'],
            'is_valid': True,
            'student_name': student_name,
            'student_email': student_email,
            'course_name': course_title,
            'level': course_level_str,
            'start_date': start_date,
            'current_date': current_date,
            'duration_days': duration_days,
            'overall_percentage': perf['overall_percentage'],
            'performance_grade': perf['performance_grade'],
            'ai_review': ai_review,
            'qr_code_data_uri': qr_data_uri,
            'verification_url': verification_url,
        }
    )
    return cert, perf
