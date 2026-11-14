"""Tests for /api/v1/admin-courses/ (admin course management pages)."""

import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from . import views
from .models import (
    AcademicLesson,
    AdminCourse,
    AssignmentSubmission,
    CourseLevel,
    CourseModule,
    DailyLesson,
    GeneratedCourse,
    LessonTask,
    PresentationSlide,
    QuizSubmission,
)

BASE = '/api/v1/admin-courses'
CTX = 'alvixapp.page_context.admin_courses'
DEEP = 'alvixapp.deep_curriculum_service.generate_deep_university_curriculum'


class AdminCoursesApiBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # No passwords: hashing is slow and the tests use force_login().
        cls.admin = User.objects.create_user('boss', 'boss@x.com', is_staff=True)
        cls.student = User.objects.create_user('stud', 'stud@x.com')
        cls.course = AdminCourse.objects.create(title='Python Engineering', description='Desc')
        cls.level = CourseLevel.objects.create(parent_course=cls.course, level='Beginner')
        cls.module = CourseModule.objects.create(course_level=cls.level, title='Basics', order=1, description='Mod desc')
        cls.lesson = AcademicLesson.objects.create(
            module=cls.module, course_level=cls.level, order=1, title='Variables', reading_content='<p>Read</p>',
            code_examples=[{'title': 'Ex', 'code': 'x = 1', 'explanation': 'assign'}],
            use_cases=[{'scenario': 'S', 'solution': 'Sol'}],
            quiz_data=[{'question': 'Q?', 'options': ['a', 'b'], 'correct_answer': 1, 'explanation': 'because'}],
        )
        PresentationSlide.objects.create(course_level=cls.level, lesson=cls.lesson, slide_number=1, title='Intro',
                                         bullet_points=['one', 'two'])
        cls.daily = DailyLesson.objects.create(course_level=cls.level, day_number=1, title='Day One', content='<p>Hello world</p>')
        LessonTask.objects.create(lesson=cls.daily, assignment_question='Build it',
                                  quiz_data=[{'question': 'DQ?', 'options': ['x', 'y'], 'answer': 'y'}])
        cls.gen = GeneratedCourse.objects.create(user=cls.student, admin_course=cls.course, course_level=cls.level,
                                                 level='Beginner', pace='Standard')

    def add_student_progress(self):
        """Student plan of 2 days: day 1 completed with an assignment + quiz, day 2 untouched."""
        d1 = DailyLesson.objects.create(generated_course=self.gen, day_number=1, title='S1', content='c', is_completed=True)
        DailyLesson.objects.create(generated_course=self.gen, day_number=2, title='S2', content='c')
        AssignmentSubmission.objects.create(user=self.student, lesson=d1, marks=8, total_marks=10)
        QuizSubmission.objects.create(user=self.student, lesson=d1, score=4, total_questions=5, percentage=80)

    def login_admin(self):
        self.client.force_login(self.admin)


class PermissionTests(AdminCoursesApiBase):
    def test_anonymous_rejected(self):
        for url in (f'{BASE}/levels/', f'{BASE}/courses/{self.course.slug}/', f'{BASE}/levels/{self.level.slug}/users/'):
            self.assertIn(self.client.get(url).status_code, (401, 403))

    def test_student_forbidden(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(f'{BASE}/levels/').status_code, 403)
        self.assertEqual(self.client.get(f'{BASE}/levels/{self.level.slug}/').status_code, 403)
        self.assertEqual(self.client.post(f'{BASE}/courses/', {'title': 'X'}).status_code, 403)
        self.assertEqual(self.client.post(f'{BASE}/levels/{self.level.slug}/regenerate/').status_code, 403)
        self.assertEqual(self.client.post(f'{BASE}/lessons/{self.daily.id}/upload-ppt/').status_code, 403)


class LevelsListTests(AdminCoursesApiBase):
    def test_list_and_filters(self):
        self.login_admin()
        data = self.client.get(f'{BASE}/levels/').json()
        for key in ('level_cards', 'total_courses', 'total_cards', 'search_query', 'tier_filter'):
            self.assertIn(key, data)
        self.assertEqual(data['total_cards'], 1)
        card = data['level_cards'][0]
        self.assertEqual(card['slug'], self.level.slug)
        self.assertEqual(card['enrolled_count'], 1)
        self.assertEqual(card['level'], 'Beginner')
        self.assertTrue(card['level_is_beginner'])
        self.assertFalse(card['level_is_intermediate'])
        self.assertEqual(card['duration'], '12 Days')   # AdminCourse.course_type defaults to Mixed
        self.assertEqual(card['course_title'], 'Python Engineering')
        self.assertEqual(card['level_code'], self.level.level_code)
        self.assertTrue(card['level_code'].startswith('ALV-BEG-'))
        self.assertEqual(card['lessons_count'], 1)
        self.assertEqual(card['description'], 'Desc')   # level has none -> parent course description
        self.assertIsNone(card['image'])

        AdminCourse.objects.filter(pk=self.course.pk).update(course_type='Practical')
        self.assertEqual(self.client.get(f'{BASE}/levels/').json()['level_cards'][0]['duration'], '10 Days')

        data = self.client.get(f'{BASE}/levels/', {'tier': 'Advanced'}).json()
        self.assertEqual(data['total_cards'], 0)
        self.assertEqual(data['tier_filter'], 'Advanced')
        data = self.client.get(f'{BASE}/levels/', {'search': 'python'}).json()
        self.assertEqual(data['total_cards'], 1)


class AddCourseTests(AdminCoursesApiBase):
    def test_create_course(self):
        self.login_admin()
        with patch(f'{CTX}.create_course_tiers_and_curriculum') as tiers:
            res = self.client.post(f'{BASE}/courses/', {'title': 'Rust Systems', 'description': 'Safe'})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body['ok'])
        self.assertEqual(body['redirect'], '/courses_info/')
        self.assertEqual(body['messages'][0]['message'], "Course 'Rust Systems' created and university tiers initialized!")
        self.assertTrue(AdminCourse.objects.filter(slug='rust-systems').exists())
        tiers.assert_called_once()

    def test_missing_title(self):
        self.login_admin()
        res = self.client.post(f'{BASE}/courses/', {'title': '  '})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.json()['ok'])

    def test_legacy_view_still_works(self):
        self.login_admin()
        with patch(f'{CTX}.create_course_tiers_and_curriculum'):
            res = self.client.post(reverse('add_course'), {'title': 'Legacy Course', 'description': 'd'})
        self.assertRedirects(res, reverse('courses_info'), fetch_redirect_response=False)


class CourseDetailTests(AdminCoursesApiBase):
    def test_detail_payload(self):
        self.login_admin()
        data = self.client.get(f'{BASE}/courses/{self.course.slug}/').json()
        for key in ('course', 'course_tiers', 'enrollments', 'enrolled_count', 'total_modules', 'total_lessons'):
            self.assertIn(key, data)
        self.assertEqual(data['course']['title'], 'Python Engineering')
        tier = data['course_tiers'][0]
        lesson = tier['modules'][0]['lessons'][0]
        self.assertEqual(lesson['title'], 'Variables')
        self.assertEqual(lesson['quiz_data'][0]['options'][1]['is_correct'], True)
        self.assertEqual(data['enrolled_count'], 1)
        row = data['enrollments'][0]
        self.assertEqual(row['full_name'], 'stud')   # Profile.full_name falls back to the username
        self.assertEqual(row['student_id'], self.student.profile.student_id)
        self.assertTrue(row['student_id'])
        self.assertEqual(row['email'], 'stud@x.com')
        self.assertEqual(row['progress'], 0)
        self.assertEqual(row['status'], 'Active')
        self.assertTrue(row['enrolled_at'])

    def test_enrollment_progress(self):
        self.add_student_progress()
        self.login_admin()
        row = self.client.get(f'{BASE}/courses/{self.course.slug}/').json()['enrollments'][0]
        self.assertEqual((row['attempted_assignments'], row['total_assignments']), (1, 2))
        self.assertEqual((row['attempted_quizzes'], row['total_quizzes']), (1, 2))
        self.assertEqual((row['completed_lessons'], row['total_lessons']), (1, 2))
        self.assertEqual(row['progress'], 50)
        self.assertEqual(row['status'], 'Active')

    def test_unknown_slug(self):
        self.login_admin()
        self.assertEqual(self.client.get(f'{BASE}/courses/nope/').status_code, 404)


class LevelDetailTests(AdminCoursesApiBase):
    def test_level_payload_without_generation(self):
        self.login_admin()
        with patch(DEEP) as deep:
            data = self.client.get(f'{BASE}/levels/{self.level.slug}/').json()
        deep.assert_not_called()   # deep content already exists
        for key in ('course_level', 'parent_course', 'modules', 'total_modules', 'total_lessons', 'all_slides',
                    'total_slides', 'daily_lessons', 'daily_lessons_count', 'enrolled_count'):
            self.assertIn(key, data)
        self.assertEqual(data['total_slides'], 1)
        day = data['daily_lessons'][0]
        self.assertEqual(day['assignment_question'], 'Build it')
        self.assertEqual(day['module_title'], 'Core Principles & Mechanics')
        self.assertTrue(day['quiz_data'][0]['options'][1]['is_correct'])
        self.assertEqual(data['modules'][0]['lessons'][0]['quiz_data'][0]['options'][1]['is_correct_index'], True)

    def test_generates_when_missing(self):
        PresentationSlide.objects.all().delete()
        self.login_admin()
        with patch(DEEP) as deep:
            res = self.client.get(f'{BASE}/levels/{self.level.slug}/')
        self.assertEqual(res.status_code, 200)
        deep.assert_called_once_with(self.level, force=False, use_ai=True)

    def test_regenerate_query(self):
        self.login_admin()
        with patch(DEEP) as deep:
            body = self.client.get(f'{BASE}/levels/{self.level.slug}/', {'regenerate': '1'}).json()
        deep.assert_called_once_with(self.level, force=True, use_ai=True)
        self.assertEqual(body['redirect'], f'/admindashboard/level/{self.level.slug}/course/')
        self.assertIn('Deep university curriculum regenerated for', body['messages'][0]['message'])

    def test_regenerate_post(self):
        self.login_admin()
        with patch(DEEP) as deep:
            body = self.client.post(f'{BASE}/levels/{self.level.slug}/regenerate/').json()
        deep.assert_called_once()
        self.assertTrue(body['ok'])
        self.assertEqual(body['redirect'], f'/admindashboard/level/{self.level.slug}/course/')

    def test_legacy_view_still_renders(self):
        self.login_admin()
        with patch(DEEP):
            res = self.client.get(reverse('admin_course_level_detail', kwargs={'slug': self.level.slug}))
        self.assertEqual(res.status_code, 200)


class LevelUsersTests(AdminCoursesApiBase):
    def test_users_payload(self):
        self.login_admin()
        data = self.client.get(f'{BASE}/levels/{self.level.slug}/users/').json()
        for key in ('course_level', 'parent_course', 'enrollments', 'total_enrolled', 'completed_count',
                    'active_count', 'avg_progress'):
            self.assertIn(key, data)
        self.assertEqual(data['total_enrolled'], 1)
        self.assertEqual(data['avg_progress'], '0.0')
        row = data['enrollments'][0]
        self.assertEqual(row['user']['username'], 'stud')
        self.assertEqual(row['email'], 'stud@x.com')
        self.assertEqual(row['full_name'], 'stud')
        self.assertEqual(row['progress'], 0)
        # original KPI definition: in-progress = at least one (not all) lessons completed; nothing started yet
        self.assertEqual(data['active_count'], 0)
        self.assertEqual(data['completed_count'], 0)

    def test_users_progress_and_kpis(self):
        self.add_student_progress()
        self.login_admin()
        data = self.client.get(f'{BASE}/levels/{self.level.slug}/users/').json()
        row = data['enrollments'][0]
        self.assertEqual(row['progress'], 50)
        self.assertEqual((row['completed_lessons'], row['total_lessons']), (1, 2))
        self.assertEqual((row['attempted_assignments'], row['attempted_quizzes']), (1, 1))
        self.assertEqual((data['active_count'], data['completed_count'], data['avg_progress']), (1, 0, '0.0'))  # original: avg = completed / enrolled

        DailyLesson.objects.filter(generated_course=self.gen).update(is_completed=True)
        data = self.client.get(f'{BASE}/levels/{self.level.slug}/users/').json()
        self.assertEqual(data['enrollments'][0]['status'], 'Completed')
        self.assertEqual((data['active_count'], data['completed_count'], data['avg_progress']), (0, 1, '100.0'))

    def test_users_email_default(self):
        User.objects.filter(pk=self.student.pk).update(email='')
        self.login_admin()
        data = self.client.get(f'{BASE}/levels/{self.level.slug}/users/').json()
        self.assertEqual(data['enrollments'][0]['email'], 'N/A')


class PptUploadTests(AdminCoursesApiBase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

    def test_missing_file(self):
        self.login_admin()
        body = self.client.post(f'{BASE}/lessons/{self.daily.id}/upload-ppt/').json()
        self.assertFalse(body['ok'])
        self.assertEqual(body['messages'][0], {'tags': 'error', 'message': 'Please select a PPTX file to upload.'})
        self.assertEqual(body['redirect'], '/admindashboard/')   # canonical lesson -> same redirect as the old view

    def test_upload_success(self):
        self.login_admin()
        upload = SimpleUploadedFile('deck.pptx', b'PK fake', content_type='application/octet-stream')
        with override_settings(MEDIA_ROOT=self.media), \
                patch('alvixapp.ppt_service.process_lesson_ppt_upload', return_value={'success': True, 'slides_count': 3}):
            body = self.client.post(f'{BASE}/lessons/{self.daily.id}/upload-ppt/', {'ppt_file': upload}).json()
        self.assertTrue(body['ok'])
        self.assertEqual(body['messages'][0]['tags'], 'success')

    def test_upload_extraction_error(self):
        self.login_admin()
        upload = SimpleUploadedFile('deck.pptx', b'PK fake', content_type='application/octet-stream')
        with patch('alvixapp.ppt_service.process_lesson_ppt_upload', side_effect=ValueError('No slides could be extracted.')):
            body = self.client.post(f'{BASE}/lessons/{self.daily.id}/upload-ppt/', {'ppt_file': upload}).json()
        self.assertFalse(body['ok'])
        self.assertEqual(body['messages'][0]['message'], 'No slides could be extracted.')


class LegacyTemplateViewTests(AdminCoursesApiBase):
    """The template views now use the shared page_context builders; they must still work."""

    def test_legacy_pages_render(self):
        self.login_admin()
        for url in (reverse('courses_info'), reverse('admin_course_detail', kwargs={'slug': self.course.slug}),
                    reverse('admin_course_level_users', kwargs={'slug': self.level.slug})):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_templates_show_real_data(self):
        """Render the legacy views directly (their URLs serve the SPA in react mode)."""
        self.add_student_progress()

        def render(view, *args):
            request = RequestFactory().get('/')
            request.user = self.admin
            return view(request, *args).content.decode()

        html = render(views.courses_info)
        self.assertIn('Harvard CS50 Benchmark', html)
        self.assertNotIn('Stanford &amp; CMU Benchmark', html)
        self.assertIn('Beginner Level', html)
        self.assertIn(self.level.level_code, html)
        self.assertIn('12 Days', html)
        html = render(views.admin_course_detail, self.course.slug)
        self.assertIn('stud@x.com', html)
        self.assertIn('width: 50%;', html)
        self.assertIn('50% (1/2)', html)
        html = render(views.admin_course_level_users, self.level.slug)
        self.assertIn('@stud', html)
        self.assertIn('width: 50%;', html)
        self.assertIn('1/2 Days', html)

    def test_legacy_regenerate_redirects(self):
        self.login_admin()
        with patch(DEEP):
            res = self.client.get(reverse('admin_regenerate_deep_curriculum', kwargs={'slug': self.level.slug}))
        self.assertRedirects(res, reverse('admin_course_level_detail', kwargs={'slug': self.level.slug}),
                             fetch_redirect_response=False)

    def test_legacy_upload_without_file_redirects(self):
        self.login_admin()
        res = self.client.post(reverse('admin_upload_lesson_ppt', kwargs={'lesson_id': self.daily.id}))
        self.assertRedirects(res, reverse('admin_dashboard'), fetch_redirect_response=False)
