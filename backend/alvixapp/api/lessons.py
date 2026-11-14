"""/api/v1/lessons/ endpoints (see api/urls.py): daily lesson player, assignment, quiz.

The page logic is shared with the legacy template views through `alvixapp/page_context/lessons.py`.
"""

import json

from django.template.defaultfilters import title as title_filter
from django.urls import path
from rest_framework.response import Response
from rest_framework.views import APIView

from ..page_context.lessons import (
    build_assignment_context,
    build_lesson_player_context,
    build_quiz_context,
    prepare_assignment,
    prepare_quiz,
    resolve_assignment_lesson,
    resolve_quiz_lesson,
    submit_assignment,
    submit_quiz,
)
from .common import collect_messages, dt, file_url


def _redirect_payload(request, url):
    return {'ok': True, 'redirect': url, 'messages': collect_messages(request)}


def _text(value):
    """What `{{ value }}` prints for a scalar (None -> 'None', like Django)."""
    return value if isinstance(value, str) else str(value)


# ---------------------------------------------------------------------------
# Daily lesson player
# ---------------------------------------------------------------------------
class LessonPlayerView(APIView):
    """GET /api/v1/lessons/<lesson_id>/ — context of course_data/daily_lesson.html."""

    def get(self, request, lesson_id):
        ctx = build_lesson_player_context(request._request, lesson_id)  # Http404 -> 404
        lesson = ctx['lesson']
        active_course = ctx['active_course']
        assets = ctx['avatar_assets']
        try:
            presentation_data = json.loads(ctx['presentation_json'] or '{}')
        except (TypeError, ValueError):
            presentation_data = {}

        return Response({
            'lesson': {
                'id': lesson.id,
                'title': lesson.title,
                'day_number': lesson.day_number,
                'watch_time_seconds': lesson.watch_time_seconds,
                'required_watch_seconds': lesson.required_watch_seconds,
                'watch_time_completed': lesson.watch_time_completed,
                'is_completed': lesson.is_completed,
            },
            'active_course': {'id': active_course.id, 'slug': active_course.slug} if active_course else None,
            'course_title': ctx['course_title'],
            'ai_video_script': ctx['ai_video_script'],
            'presentation_data': presentation_data,
            'slides_list': presentation_data.get('slides_list', []) if isinstance(presentation_data, dict) else [],
            'total_slides': ctx['total_slides'],
            'lesson_video_url': ctx['lesson_video_url'],
            'lesson_poster_url': ctx['lesson_poster_url'],
            # Filesystem paths are left out on purpose; the page only uses URLs and flags.
            'avatar_assets': {
                'present_count': assets['present_count'],
                'total_required': assets['total_required'],
                'all_exist': assets['all_exist'],
                'missing_files': assets['missing_files'],
                'has_idle': assets['has_idle'],
                'none_exist': assets['none_exist'],
                'has_custom_avatar': assets['has_custom_avatar'],
                'resolved_urls': assets['resolved_urls'],
            },
            'student_name': ctx['student_name'],
            'is_full_intro': ctx['is_full_intro'],
            'intro_spoken': ctx['intro_spoken'],
            'intro_display': ctx['intro_display'],
            'avatar_name_display': ctx['avatar_name_display'],
            'avatar_name_spoken': ctx['avatar_name_spoken'],
            'developer_name': ctx['developer_name'],
            'university_or_department': ctx['university_or_department'],
            'watch_time_url': f'/lesson/{lesson.id}/watch-time/',
            'download_ppt_url': f'/lesson/{lesson.id}/download-ppt/',
        })


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------
def _assignment_display(data):
    """Pre-rendered pieces the template printed with filters (`criterion|title`, `{{ pts }}`)."""
    if not isinstance(data, dict):
        return {'rubric': [], 'requirements_checklist': [], 'expected_points': []}
    rubric = data.get('rubric') or {}
    return {
        'rubric': [[title_filter(str(k)), _text(v)] for k, v in rubric.items()] if isinstance(rubric, dict) else [],
        'requirements_checklist': [_text(r) for r in (data.get('requirements_checklist') or [])],
        'expected_points': [_text(p) for p in (data.get('expected_points') or [])],
    }


def _assignment_payload(request, ctx):
    lesson = ctx['lesson']
    latest = ctx['latest_submission']
    active_course = ctx['active_course']
    return {
        'active_course': {'id': active_course.id, 'course_type': active_course.course_type},
        'lesson': {
            'id': lesson.id,
            'title': lesson.title,
            'day_number': lesson.day_number,
            'assignment_issued_at': dt(lesson.assignment_issued_at),
            'deadline': dt(lesson.deadline),
        },
        'assignment_prompt': ctx['assignment_prompt'],
        'assignment_data': ctx['assignment_data'] or {},
        'assignment_display': _assignment_display(ctx['assignment_data']),
        'is_practical': ctx['is_practical'],
        'deadline_date': dt(ctx['deadline_date']),
        'issue_date': dt(ctx['issue_date']),
        'is_expired': ctx['is_expired'],
        'latest_submission': {
            'id': latest.id,
            'submitted_at': dt(latest.submitted_at),
            'score': latest.score,
            'marks': latest.marks,
            'total_marks': latest.total_marks,
            'ai_feedback': latest.ai_feedback,
            'copy_risk_level': latest.copy_risk_level,
        } if latest else None,
        'all_submissions': [
            {
                'id': sub.id,
                'lesson': {
                    'id': sub.lesson.id,
                    'day_number': sub.lesson.day_number,
                    'title': sub.lesson.title,
                    'deadline': dt(sub.lesson.deadline),
                    'created_at': dt(sub.lesson.created_at),
                } if sub.lesson else None,
                'submitted_at': dt(sub.submitted_at),
                'question_prompt': sub.question_prompt,
                'file_submission': file_url(sub.file_submission),
                'ai_feedback': sub.ai_feedback,
                'score': sub.score,
                'marks': sub.marks,
                'total_marks': sub.total_marks,
            }
            for sub in ctx['all_submissions']
        ],
    }


class AssignmentView(APIView):
    """GET / POST (multipart) /api/v1/lessons/assignment/?lesson_id= — course_data/assignment.html."""

    def _resolve(self, request):
        req = request._request
        active_course, lesson, redirect_to = resolve_assignment_lesson(req, request.query_params.get('lesson_id'))
        return req, active_course, lesson, redirect_to

    def get(self, request):
        req, active_course, lesson, redirect_to = self._resolve(request)
        if redirect_to:
            return Response(_redirect_payload(req, redirect_to))
        state = prepare_assignment(req, active_course, lesson)
        return Response(_assignment_payload(req, build_assignment_context(req, state)))

    def post(self, request):
        req, active_course, lesson, redirect_to = self._resolve(request)
        if redirect_to:
            return Response(_redirect_payload(req, redirect_to))
        state = prepare_assignment(req, active_course, lesson)
        saved = submit_assignment(req, state, request.data, request.FILES)
        payload = {'ok': saved, 'lesson_id': lesson.id, 'messages': collect_messages(req)}
        if not saved:
            payload['error'] = payload['messages'][0]['message'] if payload['messages'] else ''
        return Response(payload, status=200 if saved else 400)


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------
def _quiz_payload(ctx):
    lesson = ctx['lesson']
    latest = ctx['latest_submission']
    return {
        'lesson': {
            'id': lesson.id,
            'title': lesson.title,
            'day_number': lesson.day_number,
            'quiz_issued_at': dt(lesson.quiz_issued_at),
        },
        # Correct answers and explanations stay on the server (the template never printed them).
        'quiz_questions': [
            {'id': q['id'], 'text': q['text'], 'code': q['code'], 'options': q['options'], 'topic': q['topic']}
            for q in ctx['quiz_questions']
        ],
        'issue_date': dt(ctx['issue_date']),
        'latest_submission': {
            'id': latest.id,
            'submitted_at': dt(latest.submitted_at),
            'score': latest.score,
            'total_questions': latest.total_questions,
            'percentage': latest.percentage,
            'ai_feedback': latest.ai_feedback,
            'wrong_answers_explanation': latest.wrong_answers_explanation or [],
        } if latest else None,
        'all_submissions': [
            {
                'id': sub.id,
                'submitted_at': dt(sub.submitted_at),
                'question_summary': sub.question_summary,
                'ai_feedback': sub.ai_feedback,
                'score': sub.score,
                'total_questions': sub.total_questions,
            }
            for sub in ctx['all_submissions']
        ],
    }


class QuizView(APIView):
    """GET / POST /api/v1/lessons/quiz/?lesson_id= — course_data/quiz.html. Answers are `q_<id>`."""

    def _resolve(self, request):
        req = request._request
        active_course, lesson, redirect_to = resolve_quiz_lesson(req, request.query_params.get('lesson_id'))
        return req, active_course, lesson, redirect_to

    def get(self, request):
        req, _active_course, lesson, redirect_to = self._resolve(request)
        if redirect_to:
            return Response(_redirect_payload(req, redirect_to))
        quiz_questions = prepare_quiz(req, lesson)
        return Response(_quiz_payload(build_quiz_context(req, lesson, quiz_questions)))

    def post(self, request):
        req, active_course, lesson, redirect_to = self._resolve(request)
        if redirect_to:
            return Response(_redirect_payload(req, redirect_to))
        quiz_questions = prepare_quiz(req, lesson)
        submit_quiz(req, active_course, lesson, quiz_questions, request.data)
        return Response({'ok': True, 'lesson_id': lesson.id, 'messages': collect_messages(req)})


urlpatterns = [
    path('assignment/', AssignmentView.as_view(), name='api_lesson_assignment'),
    path('quiz/', QuizView.as_view(), name='api_lesson_quiz'),
    path('<int:lesson_id>/', LessonPlayerView.as_view(), name='api_lesson_player'),
]
