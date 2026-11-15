"""/api/v1/learning/ endpoints: my course, course content, generate course, enroll level,
current lesson redirect, certificate. Logic lives in page_context/learning.py (shared with
the legacy template views)."""

from django.http import Http404
from django.template.base import Variable, VariableDoesNotExist
from django.template.context import Context
from django.template.defaultfilters import linebreaks_filter
from django.urls import path
from django.utils.formats import localize
from rest_framework.response import Response
from rest_framework.views import APIView

from ..page_context import learning as ctx
from .common import dt, file_url, ok

# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def tvar(obj, lookup):
    """Resolve `obj.<lookup>` exactly like a Django template variable ('' when missing).
    Content topics are JSON (dicts or plain strings), so e.g. `topic.title` on a string
    calls str.title() in the template: reproduce that rather than guess."""
    try:
        value = Variable(f'v.{lookup}').resolve(Context({'v': obj}))
    except (VariableDoesNotExist, Exception):
        return ''
    return value


def text(value):
    """`{{ value }}` output for a scalar value (None/'' -> '')."""
    if value is None or value == '':
        return ''
    return str(localize(value))


def _iter_strings(value):
    try:
        return [text(v) for v in value]
    except TypeError:
        return []


def admin_course_payload(ac):
    if not ac:
        return None
    return {
        'id': ac.id,
        'title': ac.title,
        'description': ac.description,
        'course_code': ac.course_code,
        'image': file_url(ac.image),
        'course_type': ac.course_type,
    }


def generated_course_payload(gc):
    if not gc:
        return None
    level = gc.course_level
    return {
        'id': gc.id,
        'title': tvar(gc, 'title'),
        'level': gc.level,
        'pace': gc.pace,
        'objective': gc.objective,
        'course_type': gc.course_type,
        'admin_course': admin_course_payload(gc.admin_course),
        'course_level': {'id': level.id, 'title': level.title, 'benchmark': level.benchmark, 'slug': level.slug} if level else None,
    }


def lesson_brief(lesson):
    if not lesson:
        return None
    return {
        'id': lesson.id,
        'day_number': lesson.day_number,
        'title': lesson.title,
    }


# ---------------------------------------------------------------------------
# My course
# ---------------------------------------------------------------------------
def mycourse_payload(context):
    active_course = context.get('active_course')

    topics = []
    for topic in context.get('content_topics') or []:
        if tvar(topic, 'topic'):
            label = tvar(topic, 'topic')
        elif tvar(topic, 'title'):
            label = tvar(topic, 'title')
        else:
            label = topic
        # Topics are stored with `bullets` (ai_services / course_tier_service); `study_bullets` is
        # the older key. Reading only `study_bullets` left every topic with the generic fallback text.
        study_bullets = tvar(topic, 'study_bullets') or tvar(topic, 'bullets')
        study_bullets = _iter_strings(study_bullets) if study_bullets else []
        topics.append({
            'label': text(label),
            'study_bullets': study_bullets,
            'summary': text(tvar(topic, 'summary')),
        })

    today = context.get('today_lesson')
    today_payload = None
    if today:
        try:
            question = today.task.assignment_question
        except Exception:
            question = None
        today_payload = {
            **lesson_brief(today),
            'deadline': dt(today.deadline),
            # {{ today_lesson.task.assignment_question|default:"..."|linebreaks }}
            'assignment_question_html': linebreaks_filter(
                question or "Complete the practical programming task and review questions for this lesson as instructed by Inara.",
                autoescape=True,
            ),
        }

    certificate = context.get('certificate')
    user_courses = context.get('user_courses')

    return {
        'active_course': generated_course_payload(active_course),
        'user_courses': [
            {'id': uc.id, 'admin_course': {'title': uc.admin_course.title if uc.admin_course else ''}}
            for uc in user_courses
        ] if user_courses is not None else [],
        'lessons': [
            {
                **lesson_brief(l),
                'is_completed': l.is_completed,
                'is_unlocked': l.is_unlocked,
                'watch_time_seconds': l.watch_time_seconds,
                'required_watch_seconds': l.required_watch_seconds,
            }
            for l in (context.get('lessons') or [])
        ],
        'content_topics': topics,
        'today_lesson': today_payload,
        'assignment_submissions': [
            {
                'id': s.id,
                'lesson': lesson_brief(s.lesson),
                'submitted_answer': s.submitted_answer,
                'marks': s.marks,
                'score': s.score,
                'total_marks': s.total_marks,
                'ai_feedback': s.ai_feedback,
                'submitted_at': dt(s.submitted_at),
            }
            for s in (context.get('assignment_submissions') or [])
        ],
        'quiz_submissions': [
            {
                'id': q.id,
                'lesson': lesson_brief(q.lesson),
                'score': q.score,
                'total_questions': q.total_questions,
                'percentage': q.percentage,
                'submitted_at': dt(q.submitted_at),
            }
            for q in (context.get('quiz_submissions') or [])
        ],
        # /course/<id>/ renders the template without these: keep them null so the page renders the same blanks
        'progress_percentage': context.get('progress_percentage'),
        'certificate': {'is_unlocked': certificate.is_unlocked, 'certificate_id': certificate.certificate_id} if certificate else None,
        'active_tab': context.get('active_tab'),
    }


class MyCourseView(APIView):
    """GET /api/v1/learning/mycourse/?course_id=&tab= (page /mycourse/)."""

    def get(self, request):
        return Response(mycourse_payload(ctx.build_mycourse_context(request)))


class CourseDetailView(APIView):
    """GET /api/v1/learning/course/<id>/ (page /course/<id>/: same template, less context)."""

    def get(self, request, course_id):
        context = ctx.build_course_detail_context(request, course_id)
        if context is None:
            return Response({'redirect': '/mycourse/'})
        return Response(mycourse_payload(context))


# ---------------------------------------------------------------------------
# Course content
# ---------------------------------------------------------------------------
class CourseContentView(APIView):
    """GET /api/v1/learning/course-content/?course_id= (pages /course_content/ and /course-content/).
    Self-healing like the template view: may enrol/sync lessons on first load."""

    def get(self, request):
        context = ctx.build_course_content_context(request)
        topics = []
        for topic in context['content_topics'] or []:
            bullets = tvar(topic, 'bullets')
            topics.append({
                'title': text(tvar(topic, 'title')),
                'bullets': _iter_strings(bullets) if bullets else [],
            })
        return Response({
            'active_course': generated_course_payload(context['active_course']),
            'content_topics': topics,
            'course_type': context['course_type'],
            'plan_duration': context['plan_duration'],
            'lessons': [
                {
                    **lesson_brief(l),
                    'content': l.content,
                    'has_real_video': bool(getattr(l, 'has_real_video', False)),
                    'video_url': l.video_url,
                    'video_script': text(getattr(l, 'video_script', '')),
                }
                for l in context['lessons']
            ],
        })


# ---------------------------------------------------------------------------
# Generate course
# ---------------------------------------------------------------------------
class GenerateCourseView(APIView):
    """GET/POST /api/v1/learning/generate-course/ (page /generate_course/)."""

    def get(self, request):
        context = ctx.build_generate_course_context(request)
        assessment = context['assessment']
        return Response({
            'available_courses': [
                {'id': c.id, 'course_code': c.course_code, 'title': c.title}
                for c in context['available_courses']
            ],
            'suggested_courses': [
                {
                    **admin_course_payload(c),
                    'course_levels': [
                        {
                            'id': lvl.id,
                            'level': lvl.level,
                            'title': lvl.title,
                            'benchmark': lvl.benchmark,
                            'description': lvl.description,
                            'slug': lvl.slug,
                        }
                        for lvl in c.course_levels.all()
                    ],
                }
                for c in context['suggested_courses']
            ],
            'assessment': {'learning_goal': assessment.learning_goal} if assessment else None,
        })

    def post(self, request):
        success, level, message, target = ctx.perform_generate_course(request.user, request.data)
        if success:
            return Response(ok(message, level, redirect=target))
        return Response(
            {'ok': False, 'error': message, 'messages': [{'tags': level, 'message': message}], 'redirect': target},
            status=400,
        )


# ---------------------------------------------------------------------------
# Enroll level
# ---------------------------------------------------------------------------
class EnrollLevelView(APIView):
    """POST /api/v1/learning/enroll-level/<slug>/ (page /enroll-level/<slug>/)."""

    def post(self, request, slug):
        message, target = ctx.perform_enroll_level(request.user, slug)
        return Response(ok(message, 'success', redirect=target))


# ---------------------------------------------------------------------------
# Current lesson redirect
# ---------------------------------------------------------------------------
class CurrentLessonView(APIView):
    """GET /api/v1/learning/current-lesson/?lesson_id=&course_id= (page /daily_lesson/, redirect only)."""

    def get(self, request):
        lesson_id, error = ctx.resolve_current_lesson(request)
        if lesson_id:
            if not str(lesson_id).isdigit():
                raise Http404  # the template view could not reverse a non-numeric id either
            return Response({'redirect': f'/daily-lesson/{lesson_id}/'})
        return Response({'messages': [{'tags': 'error', 'message': error}], 'redirect': '/course-content/'})


# ---------------------------------------------------------------------------
# Certificate
# ---------------------------------------------------------------------------
class CertificateView(APIView):
    """GET /api/v1/learning/certificate/?course_id=&preview= (pages /certificate/, /certificate/<id>/)."""

    def get(self, request):
        course_id = request.GET.get('course_id')
        if course_id and not str(course_id).isdigit():
            raise Http404
        locked, context = ctx.build_certificate_context(request, int(course_id) if course_id else None)

        if locked:
            payload = {'locked': True, 'error': context.get('error')}
            if 'active_course' in context:
                payload.update({
                    'active_course': {'id': context['active_course'].id},
                    'remaining_lessons': context['remaining_lessons'],
                    'score_gap': context['score_gap'],
                    'score_gap_display': text(context['score_gap']),
                    'pass_mark': context['pass_mark'],
                    'pass_mark_display': text(context['pass_mark']) if context['pass_mark'] else '35',
                    'current_score': context['current_score'],
                    'current_score_display': text(context['current_score']) if context['current_score'] else '0',
                })
            return Response(payload)

        cert = context['certificate']
        active_course = context['active_course']
        owner_profile = getattr(cert.user, 'profile', None)
        return Response({
            'locked': False,
            'active_course': {'id': active_course.id, 'level': active_course.level},
            'certificate': {
                'certificate_id': cert.certificate_id,
                'student_name': cert.student_name,
                'student_email': cert.student_email,
                # Owner-approved fix: the certificate shows the student ID (was the email).
                'student_id': owner_profile.student_id if owner_profile else '',
                'course_name': cert.course_name,
                'overall_percentage': cert.overall_percentage,
                'overall_percentage_display': text(cert.overall_percentage),
                'performance_grade': cert.performance_grade,
                'level': cert.level,
                'start_date': dt(cert.start_date),
                'current_date': dt(cert.current_date),
                'duration_days': cert.duration_days,
                'ai_review': cert.ai_review,
                'qr_code_data_uri': cert.qr_code_data_uri,
                'is_unlocked': cert.is_unlocked,
            },
        })


urlpatterns = [
    path('mycourse/', MyCourseView.as_view(), name='api_learning_mycourse'),
    path('course/<int:course_id>/', CourseDetailView.as_view(), name='api_learning_course_detail'),
    path('course-content/', CourseContentView.as_view(), name='api_learning_course_content'),
    path('generate-course/', GenerateCourseView.as_view(), name='api_learning_generate_course'),
    path('enroll-level/<slug:slug>/', EnrollLevelView.as_view(), name='api_learning_enroll_level'),
    path('current-lesson/', CurrentLessonView.as_view(), name='api_learning_current_lesson'),
    path('certificate/', CertificateView.as_view(), name='api_learning_certificate'),
]
