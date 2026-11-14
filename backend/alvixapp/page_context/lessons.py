"""
Shared context builders for the lesson player, assignment and quiz pages.

Used by both the legacy template views (`views.single_lesson_view`, `views.assignment_view`,
`views.quiz_view`) and the JSON API (`api/lessons.py`), so the two stay identical.

The helpers that fetch/generate tasks (`get_saved_or_generated_assignment`,
`get_saved_or_generated_quiz`, `get_avatar_asset_status`) still live in `views.py`; they are
imported lazily to avoid a circular import (views imports this module).
"""

import json
import logging
import os
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from ..assignment_grading import evaluate_submission_with_ai
from ..certificate_service import update_or_create_student_certificate
from ..copy_detection import evaluate_submission_copy_risk
from ..models import AssignmentSubmission, AvatarSettings, DailyLesson, GeneratedCourse, QuizSubmission
from ..permissions import can_access_lesson

logger = logging.getLogger('alvixapp.views')


def _views():
    from .. import views
    return views


# ---------------------------------------------------------------------------
# Daily lesson player (/daily-lesson/<lesson_id>/)
# ---------------------------------------------------------------------------
def build_lesson_player_context(request, lesson_id):
    """Context of `course_data/daily_lesson.html`. Raises Http404 when the lesson is not accessible."""
    lesson = get_object_or_404(DailyLesson, id=lesson_id)
    if not can_access_lesson(request.user, lesson):
        raise Http404("Lesson not found")
    active_course = lesson.generated_course

    if active_course and active_course.admin_course:
        course_title = active_course.admin_course.title
    else:
        course_title = "Custom Course"

    # Built-in dynamic AI video simulation script based on lesson content
    ai_video_script = (
        f"Module Overview: Introduction to {lesson.title}.\n"
        f"• Core Concept Breakdown: {lesson.content[:150]}...\n"
        f"• Practical Application & Analysis: Exploring key principles for {course_title}.\n"
        f"• Summary & Key Takeaways: Mastering daily objectives efficiently."
    )

    presentation_data = None
    presentation_json = "{}"
    slides_list = []
    lesson_video_url = None
    lesson_poster_url = None

    try:
        from ..ppt_generator import build_dynamic_slides_from_content, enrich_lecture_with_narrations
        pdata = lesson.presentation_data if isinstance(lesson.presentation_data, dict) else {}
        slides_list = pdata.get('slides_list', [])
        # Ensure all dynamic slides (13+ slides) from content/syllabus are generated & matched with PPT
        if not pdata or len(slides_list) < 10:
            lecture_data = build_dynamic_slides_from_content(lesson)
            pdata = enrich_lecture_with_narrations(lecture_data, lesson)
            try:
                lesson.presentation_data = pdata
                lesson.save(update_fields=['presentation_data'])
            except Exception:
                pass
            slides_list = pdata.get('slides_list', [])
        presentation_data = pdata
        presentation_json = json.dumps(presentation_data)
    except Exception as e:
        logger.error(f"Error preparing topic slide deck for lesson {lesson.id}: {e}")
        try:
            from ..ppt_service import ensure_lesson_slides_and_explanations
            presentation_data = ensure_lesson_slides_and_explanations(lesson)
            presentation_json = json.dumps(presentation_data)
            slides_list = presentation_data.get('slides_list', [])
        except Exception as fallback_err:
            logger.error(f"Fallback ppt_service failed: {fallback_err}")

    try:
        video_filename = f"lesson_{lesson.id}.mp4"
        disk_path = os.path.join(settings.MEDIA_ROOT, "videos", video_filename)
        if os.path.exists(disk_path) and os.path.getsize(disk_path) > 10000:
            lesson_video_url = f"{settings.MEDIA_URL}videos/{video_filename}"
            if lesson.video_url != lesson_video_url:
                lesson.video_url = lesson_video_url
                try:
                    lesson.save(update_fields=['video_url'])
                except Exception:
                    pass
        elif lesson.generated_course and lesson.course_level:
            canonical_lesson = DailyLesson.objects.filter(
                course_level=lesson.course_level,
                day_number=lesson.day_number,
                generated_course__isnull=True
            ).first()
            if canonical_lesson and canonical_lesson.video_url:
                c_rel = canonical_lesson.video_url.replace(settings.MEDIA_URL, '').lstrip('/')
                c_path = os.path.join(settings.MEDIA_ROOT, c_rel)
                if os.path.exists(c_path) and os.path.getsize(c_path) > 10000:
                    lesson_video_url = canonical_lesson.video_url
                    if lesson.video_url != lesson_video_url:
                        lesson.video_url = lesson_video_url
                        try:
                            lesson.save(update_fields=['video_url'])
                        except Exception:
                            pass
        lesson_poster_url = None
    except Exception as e:
        logger.error(f"Error checking video for lesson {lesson.id}: {e}")

    avatar_settings = AvatarSettings.get_settings()
    asset_status = _views().get_avatar_asset_status()

    student_name = "Student"
    if request.user.is_authenticated:
        student_name = request.user.first_name or request.user.username or "Student"

    day_num = lesson.day_number or 1
    lesson_title = lesson.title or "Masterclass Lecture"
    is_full_intro = (day_num == 1 or avatar_settings.play_full_intro_every_day)

    if is_full_intro:
        intro_spoken = avatar_settings.format_full_intro_spoken(
            student_name=student_name,
            course_name=course_title,
            day_number=day_num,
            lesson_title=lesson_title
        )
        intro_display = avatar_settings.format_full_intro_display(
            student_name=student_name,
            course_name=course_title,
            day_number=day_num,
            lesson_title=lesson_title
        )
    else:
        intro_spoken = avatar_settings.format_short_greeting_spoken(
            student_name=student_name,
            lesson_title=lesson_title
        )
        intro_display = avatar_settings.format_short_greeting_display(
            student_name=student_name,
            lesson_title=lesson_title
        )

    return {
        'lesson': lesson,
        'active_course': active_course,
        'course_title': course_title,
        'ai_video_script': ai_video_script,
        'presentation_data': presentation_data,
        'presentation_json': presentation_json,
        'slides_list': slides_list,
        'total_slides': len(slides_list) if slides_list else 10,
        'lesson_video_url': lesson_video_url,
        'lesson_poster_url': lesson_poster_url,
        'avatar_settings': avatar_settings,
        'avatar_assets': asset_status,
        'student_name': student_name,
        'is_full_intro': is_full_intro,
        'intro_spoken': intro_spoken,
        'intro_display': intro_display,
        'avatar_name_display': avatar_settings.avatar_name,
        'avatar_name_spoken': avatar_settings.get_spoken_name(),
        'developer_name': avatar_settings.developer_name,
        'university_or_department': avatar_settings.university_or_department,
    }


# ---------------------------------------------------------------------------
# Assignment (/assignment/?lesson_id=)
# ---------------------------------------------------------------------------
def resolve_assignment_lesson(request, lesson_id=None):
    """Returns (active_course, lesson, redirect_url). Adds the same messages the view added."""
    active_course = GeneratedCourse.objects.filter(user=request.user).order_by('-created_at').first()
    if not active_course:
        messages.warning(request, "First generate your course.")
        return None, None, reverse('mycourse')

    lesson = None
    if lesson_id:
        lesson = DailyLesson.objects.filter(id=lesson_id, generated_course=active_course).first()

    if not lesson:
        lesson = active_course.daily_lessons.filter(is_unlocked=True).last() or active_course.daily_lessons.first()

    if not lesson:
        messages.error(request, "No lesson is available.")
        return active_course, None, reverse('generate_course')

    return active_course, lesson, None


def prepare_assignment(request, active_course, lesson):
    """Loads (or generates) the assignment and records the issue date. Returns the shared state."""
    # Instant access: Load pre-saved assignment directly from database and record issue date upon click
    assignment_prompt, assignment_data = _views().get_saved_or_generated_assignment(lesson, request=request)
    lesson.refresh_from_db()

    deadline_date = lesson.deadline or (timezone.now() + timedelta(days=2))
    is_expired = timezone.now() > deadline_date

    # Track determination
    is_practical = (assignment_data.get('type') == 'practical') if assignment_data else (active_course.course_type == 'Practical')

    return {
        'active_course': active_course,
        'lesson': lesson,
        'assignment_prompt': assignment_prompt,
        'assignment_data': assignment_data,
        'is_practical': is_practical,
        'deadline_date': deadline_date,
        'issue_date': lesson.assignment_issued_at,
        'is_expired': is_expired,
    }


def submit_assignment(request, state, post, files):
    """The POST branch of assignment_view. Adds the result message; returns True when saved."""
    active_course = state['active_course']
    lesson = state['lesson']
    assignment_prompt = state['assignment_prompt']

    submission_text = str(post.get('student_submission', '') or '').strip()
    uploaded_file = files.get('file_submission')

    if not submission_text and not uploaded_file:
        messages.error(request, "Please provide source code/notes or upload a completed solution file.")
        return False

    if uploaded_file:
        from ..upload_safety import UploadRejected, validate_submission_file
        try:
            validate_submission_file(uploaded_file)
        except UploadRejected as exc:
            messages.error(request, str(exc))
            return False

    # Telemetry: Copy/paste and typing pattern tracking
    def _int(name):
        try:
            return max(0, int(post.get(name, 0) or 0))
        except (TypeError, ValueError):
            return 0

    paste_count = _int('paste_count')
    pasted_chars_total = _int('pasted_chars_total')
    typing_duration_seconds = _int('typing_duration_seconds')
    keystroke_count = _int('keystroke_count')

    # Integrity Check: Evaluate copy risk
    copy_risk, peer_sim, ai_prob, copy_details = evaluate_submission_copy_risk(
        submission_text=submission_text,
        paste_count=paste_count,
        pasted_chars_total=pasted_chars_total,
        typing_duration_seconds=typing_duration_seconds,
        keystroke_count=keystroke_count,
        current_user=request.user,
        lesson=lesson
    )

    # Rubric Evaluation: Do not give zero for copy risk; evaluate rubric fairly and flag for admin
    eval_result = evaluate_submission_with_ai(lesson.title, submission_text, uploaded_file)
    score_val = min(10, max(2, int(eval_result.get('score', 4)) * 2))  # Scale to 10 marks
    rubric_remarks = (
        f"Rubric Feedback: Scored {score_val}/10 marks. {eval_result.get('remarks', 'Good implementation.')} "
        f"[Integrity Review: {copy_risk} copy risk flagged for administrative verification]."
    )

    submission, created = AssignmentSubmission.objects.get_or_create(
        user=request.user,
        lesson=lesson,
        defaults={
            'question_prompt': assignment_prompt,
            'submitted_answer': submission_text,
            'file_submission': uploaded_file,
            'score': score_val,
            'marks': score_val,
            'total_marks': 10,
            'ai_feedback': rubric_remarks,
            'paste_count': paste_count,
            'pasted_chars_total': pasted_chars_total,
            'typing_duration_seconds': typing_duration_seconds,
            'keystroke_count': keystroke_count,
            'peer_similarity_score': peer_sim,
            'ai_generated_probability': ai_prob,
            'copy_risk_level': copy_risk,
            'copy_risk_details': copy_details,
            'admin_reviewed': False
        }
    )

    if not created:
        submission.question_prompt = assignment_prompt
        submission.submitted_answer = submission_text
        if uploaded_file:
            submission.file_submission = uploaded_file
        submission.score = score_val
        submission.marks = score_val
        submission.total_marks = 10
        submission.ai_feedback = rubric_remarks
        submission.paste_count = paste_count
        submission.pasted_chars_total = pasted_chars_total
        submission.typing_duration_seconds = typing_duration_seconds
        submission.keystroke_count = keystroke_count
        submission.peer_similarity_score = peer_sim
        submission.ai_generated_probability = ai_prob
        submission.copy_risk_level = copy_risk
        submission.copy_risk_details = copy_details
        submission.submitted_at = timezone.now()
        submission.save()

    # Mark lesson completed
    lesson.is_completed = True
    lesson.save(update_fields=['is_completed'])

    # Continuous daily update of student certificate on submission
    update_or_create_student_certificate(request.user, active_course, request=request)

    messages.success(request, f"Assignment successfully submitted! Rubric score: {score_val}/10 marks.")
    return True


def build_assignment_context(request, state):
    """Full template context (state + submission history)."""
    lesson = state['lesson']
    latest_submission = AssignmentSubmission.objects.filter(user=request.user, lesson=lesson).order_by('-submitted_at').first()
    all_submissions = AssignmentSubmission.objects.filter(user=request.user).select_related('lesson').order_by('-submitted_at')
    return {
        **state,
        'latest_submission': latest_submission,
        'all_submissions': all_submissions,
    }


# ---------------------------------------------------------------------------
# Quiz (/quiz/?lesson_id= and /quiz/<lesson_id>/)
# ---------------------------------------------------------------------------
def resolve_quiz_lesson(request, lesson_id=None):
    """Returns (active_course, lesson, redirect_url). Adds the same message the view added."""
    active_course = GeneratedCourse.objects.filter(user=request.user).order_by('-created_at').first()

    lesson = None
    if lesson_id:
        lesson = DailyLesson.objects.filter(id=lesson_id, generated_course__user=request.user).first()

    if not lesson and active_course:
        lesson = active_course.daily_lessons.filter(is_unlocked=True).last() or active_course.daily_lessons.first()

    if not lesson:
        messages.error(request, "No lesson available for quiz.")
        return active_course, None, reverse('dashboard')

    return active_course, lesson, None


def prepare_quiz(request, lesson):
    """Loads (or generates) the quiz and records the issue date."""
    quiz_questions = _views().get_saved_or_generated_quiz(lesson, request=request)
    lesson.refresh_from_db()
    return quiz_questions


def submit_quiz(request, active_course, lesson, quiz_questions, post):
    """The POST branch of quiz_view. Adds the result message."""
    score = 0
    total = len(quiz_questions)
    summary_list = []
    wrong_answers = []

    for idx, q in enumerate(quiz_questions, start=1):
        q_id = q.get('id', idx)
        user_answer = str(post.get(f"q_{q_id}", "") or "").strip()
        correct_answer = str(q.get('correct', '')).strip()

        is_correct = bool(user_answer and user_answer.lower() == correct_answer.lower())
        if is_correct:
            score += 1
        else:
            wrong_answers.append({
                'question_number': idx,
                'question': q.get('text', ''),
                'user_answer': user_answer or "No answer provided",
                'correct_answer': correct_answer,
                'explanation': q.get('explanation', 'Refer to today\'s core lecture concepts.')
            })

        summary_list.append(
            f"<div class='mb-2 pb-2 border-bottom'>"
            f"<strong>Q{idx}: {q.get('text', '')}</strong><br>"
            f"<small class='text-muted'>Your Answer: <span class='{'text-success fw-bold' if is_correct else 'text-danger fw-bold'}'>{user_answer or 'None'}</span></small><br>"
            f"<small class='text-muted'>Correct Answer: <span class='text-success fw-bold'>{correct_answer}</span></small>"
            f"</div>"
        )

    percentage = int((score / total) * 100) if total > 0 else 0

    # Build remarks with explanation per wrong answer
    if wrong_answers:
        wrong_feedback_parts = [
            f"• Q{w['question_number']}: Correct answer was '{w['correct_answer']}'. {w['explanation']}"
            for w in wrong_answers
        ]
        ai_remarks = (
            f"Completed quiz with {score}/{total} correct answers ({percentage}% accuracy).\n"
            f"Explanations for Incorrect Answers:\n" + "\n".join(wrong_feedback_parts)
        )
    else:
        ai_remarks = f"Flawless performance! You achieved {score}/{total} correct answers (100% accuracy) on today\'s diagnostic quiz."

    question_summary_html = "".join(summary_list)

    QuizSubmission.objects.create(
        user=request.user,
        lesson=lesson,
        score=score,
        total_questions=total,
        percentage=percentage,
        ai_feedback=ai_remarks,
        wrong_answers_explanation=wrong_answers,
        question_summary=question_summary_html
    )

    # Mark lesson completed
    lesson.is_completed = True
    lesson.save(update_fields=['is_completed'])

    # Continuous daily update of student certificate on submission
    update_or_create_student_certificate(request.user, active_course, request=request)

    # Unlock next lesson if passed
    if percentage >= 50:
        next_lesson = DailyLesson.objects.filter(
            generated_course=lesson.generated_course,
            day_number=lesson.day_number + 1
        ).first()
        if next_lesson:
            next_lesson.is_unlocked = True
            next_lesson.save(update_fields=['is_unlocked'])
        messages.success(request, f"Quiz passed with {score}/{total} correct answers ({percentage}%)! Next lesson unlocked.")
    else:
        messages.warning(request, f"Score: {percentage}%. Review the wrong answer explanations and try again to master the concepts.")


def build_quiz_context(request, lesson, quiz_questions):
    all_submissions = QuizSubmission.objects.filter(user=request.user).order_by('-submitted_at')
    latest_submission = QuizSubmission.objects.filter(user=request.user, lesson=lesson).order_by('-submitted_at').first()
    return {
        'lesson': lesson,
        'quiz_questions': quiz_questions,
        'latest_submission': latest_submission,
        'all_submissions': all_submissions,
        'issue_date': lesson.quiz_issued_at,
    }
