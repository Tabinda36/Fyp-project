"""Tests for /api/v1/learning/ (my course, course content, generate course, enroll level,
current lesson, certificate) and the legacy template views that share page_context/learning.py."""

from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from .models import (
    AdminCourse,
    AssignmentSubmission,
    CourseLevel,
    DailyLesson,
    GeneratedCourse,
    QuizSubmission,
)


class LearningApiBase(TestCase):
    def setUp(self):
        patchers = [
            patch('alvixapp.ppt_service.synthesize_speech', return_value=True),
            patch('alvixapp.ppt_service.generate_slide_audio_gtts', return_value=True),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)

        self.user = User.objects.create_user('learner', 'learner@example.com', 'Str0ng-pass!')
        self.other = User.objects.create_user('other', 'other@example.com', 'Str0ng-pass!')
        self.admin_course = AdminCourse.objects.create(title='Python Programming', description='Learn Python from scratch.')
        self.level = CourseLevel.objects.create(
            parent_course=self.admin_course, level='Beginner', title='Python Programming - Beginner',
            content_topics=[{'title': 'Variables', 'bullets': ['ints', 'strings']}, 'plain topic'],
        )
        self.course = GeneratedCourse.objects.create(
            user=self.user, admin_course=self.admin_course, course_level=self.level,
            level='Beginner', pace='Standard', objective='Get good at Python',
            content_topics=[{'title': 'Variables', 'bullets': ['ints', 'strings']}, 'plain topic'],
        )
        self.l1 = DailyLesson.objects.create(generated_course=self.course, day_number=1, title='Intro', content='<p>Hello</p>',
                                             is_unlocked=True, is_completed=True)
        self.l2 = DailyLesson.objects.create(generated_course=self.course, day_number=2, title='Loops', content='<p>Loops</p>',
                                             is_unlocked=True)
        self.l3 = DailyLesson.objects.create(generated_course=self.course, day_number=3, title='Functions', content='x')
        self.other_course = GeneratedCourse.objects.create(
            user=self.other, admin_course=self.admin_course, level='Beginner', pace='Standard',
            content_topics=['x'],
        )


class AuthRequiredTests(LearningApiBase):
    def test_endpoints_require_login(self):
        for url in ['/api/v1/learning/mycourse/', '/api/v1/learning/course-content/', '/api/v1/learning/generate-course/',
                    '/api/v1/learning/current-lesson/', '/api/v1/learning/certificate/', f'/api/v1/learning/course/{self.course.id}/']:
            self.assertIn(self.client.get(url).status_code, (401, 403), url)
        self.assertIn(self.client.post(f'/api/v1/learning/enroll-level/{self.level.slug}/').status_code, (401, 403))


class MyCourseApiTests(LearningApiBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_payload_keys_and_today_lesson(self):
        AssignmentSubmission.objects.create(user=self.user, lesson=self.l1, submitted_answer='print(1)', marks=8)
        QuizSubmission.objects.create(user=self.user, lesson=self.l1, score=4, total_questions=5, percentage=80)
        data = self.client.get('/api/v1/learning/mycourse/').json()
        for key in ['active_course', 'user_courses', 'lessons', 'content_topics', 'today_lesson', 'assignment_submissions',
                    'quiz_submissions', 'progress_percentage', 'certificate', 'active_tab']:
            self.assertIn(key, data)
        self.assertEqual(data['active_course']['id'], self.course.id)
        self.assertEqual(data['active_course']['admin_course']['title'], 'Python Programming')
        self.assertEqual(data['active_tab'], 'content')
        self.assertEqual([l['day_number'] for l in data['lessons']], [1, 2, 3])
        self.assertEqual(data['today_lesson']['id'], self.l2.id)
        self.assertIn('<p>', data['today_lesson']['assignment_question_html'])
        self.assertEqual(data['assignment_submissions'][0]['marks'], 8)
        self.assertEqual(data['quiz_submissions'][0]['percentage'], 80)
        # Same number as the Performance page / certificate (shared scoring engine)
        from .certificate_service import calculate_course_performance
        self.assertEqual(data['progress_percentage'], calculate_course_performance(self.user, self.course)['overall_percentage'])
        # topics resolved like the template: dict title, and str.title() for plain strings
        self.assertEqual(data['content_topics'][0]['label'], 'Variables')
        self.assertEqual(data['content_topics'][1]['label'], 'Plain Topic')

    def test_tab_validation(self):
        self.assertEqual(self.client.get('/api/v1/learning/mycourse/?tab=QUIZ').json()['active_tab'], 'quiz')
        self.assertEqual(self.client.get('/api/v1/learning/mycourse/?tab=bogus').json()['active_tab'], 'content')

    def test_other_users_course_is_not_shown(self):
        data = self.client.get(f'/api/v1/learning/mycourse/?course_id={self.other_course.id}').json()
        self.assertEqual(data['active_course']['id'], self.course.id)

    def test_course_switcher_lists_own_courses(self):
        second = GeneratedCourse.objects.create(user=self.user, admin_course=self.admin_course, level='Advanced', pace='Fast',
                                                content_topics=['a'])
        data = self.client.get(f'/api/v1/learning/mycourse/?course_id={second.id}').json()
        self.assertEqual(data['active_course']['id'], second.id)
        self.assertEqual([c['id'] for c in data['user_courses']], [self.course.id, second.id])

    def test_no_course(self):
        self.client.force_login(User.objects.create_user('nocourse', 'n@example.com', 'x'))
        data = self.client.get('/api/v1/learning/mycourse/').json()
        self.assertIsNone(data['active_course'])

    def test_course_detail(self):
        data = self.client.get(f'/api/v1/learning/course/{self.course.id}/').json()
        self.assertEqual(data['active_course']['id'], self.course.id)
        self.assertEqual(len(data['lessons']), 3)
        # the template view passes less context: no tab, no progress, no switcher
        self.assertIsNone(data['active_tab'])
        self.assertIsNone(data['progress_percentage'])
        self.assertEqual(data['user_courses'], [])
        self.assertEqual(self.client.get(f'/api/v1/learning/course/{self.other_course.id}/').json()['redirect'], '/mycourse/')


class CourseContentApiTests(LearningApiBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_payload(self):
        data = self.client.get(f'/api/v1/learning/course-content/?course_id={self.course.id}').json()
        self.assertEqual(data['active_course']['id'], self.course.id)
        self.assertEqual(data['course_type'], 'Mixed')
        self.assertEqual(data['plan_duration'], 12)
        self.assertEqual(len(data['lessons']), 3)
        self.assertEqual(data['lessons'][0]['content'], '<p>Hello</p>')
        self.assertFalse(data['lessons'][0]['has_real_video'])
        self.assertEqual(data['content_topics'][0], {'title': 'Variables', 'bullets': ['ints', 'strings']})
        self.assertEqual(data['content_topics'][1], {'title': 'Plain Topic', 'bullets': []})

    def test_cannot_open_other_users_course(self):
        data = self.client.get(f'/api/v1/learning/course-content/?course_id={self.other_course.id}').json()
        self.assertEqual(data['active_course']['id'], self.course.id)

    def test_self_healing_enrols_lessons(self):
        self.client.force_login(self.other)
        with patch('alvixapp.page_context.learning.fetch_and_enroll_student_in_level') as enrol:
            self.client.get('/api/v1/learning/course-content/')
        enrol.assert_called_once()


class GenerateCourseApiTests(LearningApiBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_get(self):
        data = self.client.get('/api/v1/learning/generate-course/').json()
        self.assertEqual(data['available_courses'][0]['title'], 'Python Programming')
        self.assertEqual(data['suggested_courses'][0]['course_levels'][0]['slug'], self.level.slug)
        self.assertIsNone(data['assessment'])

    def test_post_enrols_and_redirects(self):
        res = self.client.post('/api/v1/learning/generate-course/',
                               {'course_topic': str(self.admin_course.id), 'level': 'Beginner', 'pace': 'Standard', 'objective': 'x'})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['redirect'], f'/course_content/?course_id={self.course.id}')
        self.assertIn('Instant Access: Loaded', data['messages'][0]['message'])

    def test_post_without_any_course(self):
        AdminCourse.objects.all().delete()
        res = self.client.post('/api/v1/learning/generate-course/', {'level': 'Beginner'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['error'], 'Valid course level not found. Please choose a university-benchmarked course.')
        self.assertEqual(res.json()['redirect'], '/generate_course/')


class EnrollLevelApiTests(LearningApiBase):
    def test_enroll(self):
        self.client.force_login(self.other)
        res = self.client.post(f'/api/v1/learning/enroll-level/{self.level.slug}/')
        self.assertEqual(res.status_code, 200)
        gc = GeneratedCourse.objects.get(user=self.other, course_level=self.level)
        self.assertEqual(res.json()['redirect'], f'/course_content/?course_id={gc.id}')
        self.assertEqual(res.json()['messages'][0]['message'],
                         f'Successfully enrolled in {self.level.title} [{self.level.benchmark}]!')

    def test_unknown_slug(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post('/api/v1/learning/enroll-level/nope/').status_code, 404)

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f'/api/v1/learning/enroll-level/{self.level.slug}/').status_code, 405)


class CurrentLessonApiTests(LearningApiBase):
    def test_redirects(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/api/v1/learning/current-lesson/').json()['redirect'], f'/daily-lesson/{self.l2.id}/')
        self.assertEqual(self.client.get('/api/v1/learning/current-lesson/?lesson_id=7').json()['redirect'], '/daily-lesson/7/')

    def test_no_lesson(self):
        self.client.force_login(User.objects.create_user('nocourse', 'n@example.com', 'x'))
        data = self.client.get('/api/v1/learning/current-lesson/').json()
        self.assertEqual(data['redirect'], '/course-content/')
        self.assertEqual(data['messages'], [{'tags': 'error', 'message': 'No active lesson found.'}])


class CertificateApiTests(LearningApiBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_no_course(self):
        self.client.force_login(User.objects.create_user('nocourse', 'n@example.com', 'x'))
        data = self.client.get('/api/v1/learning/certificate/').json()
        self.assertTrue(data['locked'])
        self.assertEqual(data['error'], 'No active course found. Please enroll in a course to view your certificate.')

    def test_locked(self):
        data = self.client.get(f'/api/v1/learning/certificate/?course_id={self.course.id}').json()
        self.assertTrue(data['locked'])
        for key in ['remaining_lessons', 'score_gap', 'pass_mark', 'current_score', 'score_gap_display', 'current_score_display']:
            self.assertIn(key, data)
        self.assertGreater(data['remaining_lessons'], 0)

    def test_student_cannot_preview_locked_certificate(self):
        data = self.client.get(f'/api/v1/learning/certificate/?course_id={self.course.id}&preview=1').json()
        self.assertTrue(data['locked'])

    def test_preview_unlocked_shows_student_id(self):
        from django.contrib.auth.models import User
        from .models import Certificate
        admin = User.objects.create_user('cert_admin', 'cert_admin@example.com', 'x', is_staff=True)
        self.client.force_login(admin)
        data = self.client.get(f'/api/v1/learning/certificate/?course_id={self.course.id}&preview=1').json()
        # the certificate is issued to the course's student, never to the previewing admin
        self.assertFalse(Certificate.objects.filter(user=admin).exists())
        self.assertFalse(data['locked'])
        cert = data['certificate']
        self.assertEqual(cert['student_id'], self.user.profile.student_id)
        for key in ['certificate_id', 'student_name', 'course_name', 'overall_percentage_display', 'performance_grade',
                    'level', 'start_date', 'current_date', 'duration_days', 'ai_review', 'qr_code_data_uri']:
            self.assertIn(key, cert)
        self.assertEqual(data['active_course']['id'], self.course.id)

    def test_other_users_course_404(self):
        self.assertEqual(self.client.get(f'/api/v1/learning/certificate/?course_id={self.other_course.id}').status_code, 404)


class LegacyTemplateViewTests(LearningApiBase):
    """The template views now use page_context/learning.py; they must keep rendering."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_template_views(self):
        from django.conf import settings
        if getattr(settings, 'ALVIX_FRONTEND', 'templates') == 'react':
            self.skipTest('page URLs are served by the SPA')
        self.assertContains(self.client.get('/mycourse/?tab=lessons'), 'Daily Academic Lesson Roadmap')
        self.assertContains(self.client.get(f'/course/{self.course.id}/'), 'Course Syllabus')
        self.assertContains(self.client.get('/course_content/'), 'CURRICULUM HUB')
        self.assertEqual(self.client.get('/generate_course/').status_code, 200)
        self.assertRedirects(self.client.get('/daily_lesson/'), f'/daily-lesson/{self.l2.id}/', fetch_redirect_response=False)
        self.assertContains(self.client.get('/certificate/'), 'Certificate of Completion Locked')
        # Note: the unlocked legacy certificate.html raises VariableDoesNotExist (`|default:certificate_id`
        # filter argument is never in the context), so only the locked variant is rendered here.
