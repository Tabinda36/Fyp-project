"""/api/v1/admin-courses/ endpoints (see api/urls.py).

Admin course management: course list, add course, course details, level studio
(+ regenerate, PPT upload) and level telemetry. Data comes from the shared builders
in `page_context/admin_courses.py` (also used by the legacy template views).

Values are pre-rendered the way the templates rendered them (Django filters such as
truncatewords/truncatechars/striptags/date, `default`, missing attributes -> '').
"""

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.template import defaultfilters as f
from django.urls import path, reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import DailyLesson
from ..page_context import admin_courses as ctx
from .common import IsAlvixAdmin, file_url, ok


# ---------------------------------------------------------------------------
# Template-semantics helpers
# ---------------------------------------------------------------------------
_MISSING = object()


def _lookup(obj, key, missing=''):
    """Resolve `{{ obj.key }}` like Django: dict key, then attribute (called if callable),
    then list index; anything that fails resolves to `missing` ('' = string_if_invalid)."""
    if obj is None or obj == '':
        return missing
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
    try:
        value = getattr(obj, key)
    except (AttributeError, ObjectDoesNotExist):
        value = _MISSING
    if value is not _MISSING:
        if callable(value):
            try:
                value = value()
            except Exception:  # noqa: BLE001 - template engine swallows these too
                return missing
        return value
    if isinstance(obj, (list, tuple)):
        try:
            return obj[int(key)]
        except (ValueError, IndexError):
            pass
    return missing


def _text(value):
    """`{{ value }}` -> the string Django would print (None prints as 'None')."""
    return '' if value == '' else str(value)


def _default(value, fallback):
    return value if value else fallback


def _iter(value):
    """`{% for x in value %}` over a JSON field (non-iterables loop zero times)."""
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, dict):
        return list(value.keys())
    if isinstance(value, str):
        return list(value)
    return []


def _task(daily_lesson):
    try:
        return daily_lesson.task
    except ObjectDoesNotExist:
        return None


def _quiz_questions(quiz_data, truncate):
    """Quiz rows as rendered by the admin accordions."""
    questions = []
    for q in _iter(quiz_data):
        question = _lookup(q, 'question')
        correct = _lookup(q, 'correct_answer', None)
        answer = _lookup(q, 'answer', None)
        options = []
        for i, opt in enumerate(_iter(_lookup(q, 'options'))):
            options.append({
                'text': _text(opt),
                'is_correct_index': i == correct,
                'is_correct': i == correct or opt == answer,
            })
        explanation = _lookup(q, 'explanation')
        questions.append({
            'question': _text(question),
            'question_short': f.truncatechars(_text(question), truncate) if truncate else _text(question),
            'options': options,
            'explanation': _text(explanation) if explanation else '',
        })
    return questions


def _academic_lesson(lesson, summary_default=None, quiz_truncate=None):
    summary = lesson.summary
    if summary_default is not None:
        summary = f.truncatewords(_default(summary, summary_default), 15)
    return {
        'id': lesson.id,
        'order': lesson.order,
        'title': lesson.title,
        'summary': _text(summary),
        'estimated_minutes': lesson.estimated_minutes,
        'reading_content': lesson.reading_content or '',
        'code_examples': [
            {
                'title': _text(_default(_lookup(ex, 'title'), 'Code Architecture')),
                'code': _text(_lookup(ex, 'code')),
                'explanation': _text(_lookup(ex, 'explanation')) if _lookup(ex, 'explanation') else '',
            }
            for ex in _iter(lesson.code_examples)
        ] if lesson.code_examples else [],
        'use_cases': [
            {'scenario': _text(_lookup(uc, 'scenario')), 'solution': _text(_lookup(uc, 'solution'))}
            for uc in _iter(lesson.use_cases)
        ] if lesson.use_cases else [],
        'assignment_prompt': lesson.assignment_prompt or '',
        'assignment_rubric': lesson.assignment_rubric or '',
        'quiz_data': _quiz_questions(lesson.quiz_data, quiz_truncate) if lesson.quiz_data else [],
    }


def _module(module):
    return {
        'id': module.id,
        'order': module.order,
        'title': module.title,
        'description': module.description or '',
        'estimated_hours': module.estimated_hours,
        'lessons_count': module.lessons.count(),
    }


def _level(level):
    return {
        'id': level.id,
        'level': level.level,
        'title': level.title,
        'slug': level.slug,
        'level_code': level.level_code,
        'benchmark': level.benchmark,
        'benchmark_description': level.benchmark_description,
    }


def _course(course):
    return {
        'id': course.id,
        'title': course.title,
        'slug': course.slug,
        'course_code': course.course_code,
        'description': course.description,
        'level': course.level,
        'image': file_url(course.image),
    }


def _enrollment_row(row):
    """A `page_context.admin_courses.enrollment_row` dict as JSON (dates pre-formatted like the
    templates' `|date:"M d, Y"`)."""
    data = {k: v for k, v in row.items() if k not in ('user', 'enrolled_at')}
    data['user'] = {'username': row['user'].username}
    data['enrolled_at'] = f.date(timezone.localtime(row['enrolled_at']), 'M d, Y')
    return data


class AdminAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAlvixAdmin]


# ---------------------------------------------------------------------------
# GET /levels/  (courses_info)
# ---------------------------------------------------------------------------
class LevelsListView(AdminAPIView):
    def get(self, request):
        c = ctx.build_courses_info_context(request)
        cards = []
        for card in c['level_cards']:
            level_value = card['level']
            cards.append({
                'level': level_value,
                'level_is_beginner': level_value == 'Beginner',
                'level_is_intermediate': level_value == 'Intermediate',
                'title': card['title'],
                'slug': card['slug'],
                'image': file_url(card['image']),
                'level_code': card['level_code'],
                'course_title': card['course_title'],
                'lessons_count': card['lessons_count'],
                'duration': _default(card['duration'], '7 Days'),
                'description': f.truncatewords(card['description'], 18),
                'enrolled_count': card['enrolled_count'],
            })
        return Response({
            'level_cards': cards,
            'total_courses': c['total_courses'],
            'total_cards': c['total_cards'],
            'search_query': c['search_query'],
            'tier_filter': c['tier_filter'],
        })


# ---------------------------------------------------------------------------
# POST /courses/  (add_course)
# ---------------------------------------------------------------------------
class CourseCreateView(AdminAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        admin_course, msg = ctx.create_admin_course(request.data, request.FILES)
        if not admin_course:
            # The template view silently re-rendered the empty form.
            return Response({'ok': False, 'errors': {}}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ok(msg, 'success', redirect=reverse('courses_info'), slug=admin_course.slug))


# ---------------------------------------------------------------------------
# GET /courses/<slug>/  (course_details)
# ---------------------------------------------------------------------------
class CourseDetailView(AdminAPIView):
    def get(self, request, slug):
        c = ctx.build_course_detail_context(slug)
        course = c['course']

        tiers = []
        for tier in c['course_tiers']:
            modules = []
            for module in tier.academic_modules.all():
                row = _module(module)
                row['lessons'] = [
                    _academic_lesson(
                        lesson,
                        summary_default='Deep technical architecture, code implementation, lab task, and quiz.',
                        quiz_truncate=55,
                    )
                    for lesson in module.lessons.all()
                ]
                modules.append(row)
            canonical = []
            if not modules:
                for d_les in tier.canonical_lessons.all():
                    task = _task(d_les)
                    canonical.append({
                        'id': d_les.id,
                        'day_number': d_les.day_number,
                        'title': d_les.title,
                        'content': d_les.content or '',
                        'content_preview': f.truncatewords(f.striptags(d_les.content or ''), 15),
                        'task': {'assignment_question': task.assignment_question} if task else None,
                    })
            tier_row = _level(tier)
            tier_row.update({'modules': modules, 'canonical_lessons': canonical})
            tiers.append(tier_row)

        enrollments = []
        for item in c['enrollments']:
            enrollments.append(_enrollment_row(item))

        return Response({
            'course': _course(course),
            'course_tiers': tiers,
            'enrollments': enrollments,
            'enrolled_count': c['enrolled_count'],
            'total_modules': c['total_modules'],
            'total_lessons': c['total_lessons'],
        })


# ---------------------------------------------------------------------------
# GET /levels/<slug>/  (level_course_view, ?regenerate=1)
# POST /levels/<slug>/regenerate/
# ---------------------------------------------------------------------------
class LevelDetailView(AdminAPIView):
    def get(self, request, slug):
        course_level = ctx.get_course_level(slug)
        force_regen = request.query_params.get('regenerate') == '1'
        regen_msg = ctx.prepare_level_detail(course_level, force_regen)
        if regen_msg:
            return Response(ok(regen_msg, 'success', redirect=reverse('admin_course_level_detail', kwargs={'slug': slug})))

        c = ctx.build_level_detail_context(course_level)
        modules = []
        for module in c['modules']:
            row = _module(module)
            row['lessons'] = [_academic_lesson(lesson) for lesson in module.lessons.all()]
            modules.append(row)

        daily_lessons = []
        for d in c['daily_lessons']:
            task = _task(d)
            quiz = task.quiz_data if task else None
            daily_lessons.append({
                'id': d.id,
                'day_number': d.day_number,
                'title': d.title,
                'module_title': _default(d.module.title if d.module else '', 'Core Principles & Mechanics'),
                'ppt_file': bool(d.ppt_file),
                'content_html': f.truncatewords_html(d.content or '', 130),
                'assignment_question': _default(
                    task.assignment_question if task else '',
                    "Implement the day's architectural blueprint and submit your code solution for automated review.",
                ),
                'quiz_data': _quiz_questions(quiz, 65) if (task and quiz) else [],
            })

        slides = [
            {
                'id': s.id,
                'slide_number': s.slide_number,
                'slide_category': _default(s.slide_category, 'Lecture Concept'),
                'title': s.title,
                'bullet_points': [_text(pt) for pt in _iter(s.bullet_points)],
                'speaker_notes': s.speaker_notes or '',
                'code_snippet': s.code_snippet or '',
                'diagram_or_visual': s.diagram_or_visual or '',
            }
            for s in c['all_slides']
        ]

        return Response({
            'course_level': _level(course_level),
            'parent_course': _course(c['parent_course']),
            'modules': modules,
            'total_modules': c['total_modules'],
            'total_lessons': c['total_lessons'],
            'all_slides': slides,
            'total_slides': c['total_slides'],
            'daily_lessons': daily_lessons,
            'daily_lessons_count': len(daily_lessons),
            'enrolled_count': c['enrolled_count'],
        })


class LevelRegenerateView(AdminAPIView):
    def post(self, request, slug):
        course_level = ctx.get_course_level(slug)
        msg = ctx.regenerate_level_curriculum(course_level)
        return Response(ok(msg, 'success', redirect=reverse('admin_course_level_detail', kwargs={'slug': slug})))


# ---------------------------------------------------------------------------
# POST /lessons/<lesson_id>/upload-ppt/
# ---------------------------------------------------------------------------
class LessonPptUploadView(AdminAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, lesson_id):
        lesson = get_object_or_404(DailyLesson, id=lesson_id)
        level, msg = ctx.upload_lesson_ppt(lesson, request.FILES.get('ppt_file'))
        payload = ok(msg, level, redirect=ctx.ppt_upload_redirect_url(lesson))
        payload['ok'] = level == 'success'
        return Response(payload)


# ---------------------------------------------------------------------------
# GET /levels/<slug>/users/  (level_users_telemetry)
# ---------------------------------------------------------------------------
class LevelUsersView(AdminAPIView):
    def get(self, request, slug):
        c = ctx.build_level_users_context(slug)
        rows = []
        for student in c['enrollments']:
            row = _enrollment_row(student)
            row['email'] = _default(row['email'], 'N/A')  # `{{ student.email|default:"N/A" }}`
            rows.append(row)
        return Response({
            'course_level': _level(c['course_level']),
            'parent_course': _course(c['parent_course']),
            'enrollments': rows,
            'total_enrolled': c['total_enrolled'],
            'completed_count': c['completed_count'],
            'active_count': c['active_count'],
            'avg_progress': _text(c['avg_progress']),  # a float: Django printed "0.0" / "33.3"
        })


urlpatterns = [
    path('levels/', LevelsListView.as_view(), name='api_admin_levels'),
    path('levels/<slug:slug>/', LevelDetailView.as_view(), name='api_admin_level_detail'),
    path('levels/<slug:slug>/regenerate/', LevelRegenerateView.as_view(), name='api_admin_level_regenerate'),
    path('levels/<slug:slug>/users/', LevelUsersView.as_view(), name='api_admin_level_users'),
    path('courses/', CourseCreateView.as_view(), name='api_admin_course_create'),
    path('courses/<slug:slug>/', CourseDetailView.as_view(), name='api_admin_course_detail'),
    path('lessons/<int:lesson_id>/upload-ppt/', LessonPptUploadView.as_view(), name='api_admin_lesson_upload_ppt'),
]
