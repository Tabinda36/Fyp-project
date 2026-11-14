"""Tests for /api/v1/lessons/ (daily lesson player, assignment, quiz) and the shared legacy views."""

from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from .models import (
    AdminCourse,
    AssignmentSubmission,
    DailyLesson,
    GeneratedCourse,
    LessonTask,
    QuizSubmission,
)

SLIDES = [
    {'type': 'cover' if i == 0 else 'content', 'title': f'Slide {i + 1}', 'narration': f'Narration {i + 1}.'}
    for i in range(12)
]

QUIZ = [
    {'id': 1, 'question': 'Q one?', 'options': ['A', 'B', 'C'], 'correct': 'B', 'explanation': 'Because B.'},
    {'id': 2, 'question': 'Q two?', 'options': ['X', 'Y'], 'correct': 'X', 'explanation': 'Because X.'},
]

ASSIGNMENT_DATA = {
    'type': 'practical',
    'expected_file_type': '.py',
    'requirements_checklist': ['Parse the header', 'Write tests'],
    'rubric': {'correctness': 4, 'code_quality': 3, 'documentation': 3},
}

GRADE = {'score': 4, 'remarks': 'Solid work.', 'model': 'heuristic-rubric'}


def png_upload(name):
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (4, 4), 'black').save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


def make_course(user, title='Systems 101', days=2):
    admin_course = AdminCourse.objects.create(title=title, slug=f'{user.username}-course', course_code=f'C-{user.username}')
    course = GeneratedCourse.objects.create(user=user, admin_course=admin_course, slug=f'{user.username}-gen', course_type='Practical')
    lessons = []
    for day in range(1, days + 1):
        lesson = DailyLesson.objects.create(
            generated_course=course, day_number=day, title=f'Day {day} Topic', content='Core content for the day.',
            is_unlocked=(day == 1), presentation_data={'slides_list': SLIDES},
        )
        LessonTask.objects.create(
            lesson=lesson, assignment_question='Implement a slotted page header parser.',
            assignment_data=ASSIGNMENT_DATA, quiz_data=QUIZ,
        )
        lessons.append(lesson)
    return course, lessons


class LessonApiBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('learner', 'learner@example.com', 'Str0ng-pass!', first_name='Ayesha')
        self.other = User.objects.create_user('other', 'other@example.com', 'Str0ng-pass!')
        self.course, self.lessons = make_course(self.user)
        self.other_course, self.other_lessons = make_course(self.other, title='Other')
        self.client.force_login(self.user)


class AuthRequiredTests(TestCase):
    def test_anonymous_is_rejected(self):
        for url in ('/api/v1/lessons/1/', '/api/v1/lessons/assignment/', '/api/v1/lessons/quiz/'):
            self.assertIn(self.client.get(url).status_code, (401, 403), url)


class LessonPlayerApiTests(LessonApiBase):
    def test_owner_gets_full_context(self):
        lesson = self.lessons[0]
        res = self.client.get(f'/api/v1/lessons/{lesson.id}/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        for key in (
            'lesson', 'course_title', 'presentation_data', 'slides_list', 'total_slides', 'avatar_assets',
            'student_name', 'is_full_intro', 'intro_spoken', 'intro_display', 'avatar_name_display',
            'avatar_name_spoken', 'developer_name', 'university_or_department', 'watch_time_url',
        ):
            self.assertIn(key, data)
        # real JSON, not a string
        self.assertIsInstance(data['presentation_data'], dict)
        self.assertIsInstance(data['slides_list'], list)
        self.assertEqual(len(data['slides_list']), 12)
        self.assertEqual(data['total_slides'], 12)
        self.assertEqual(data['course_title'], 'Systems 101')
        self.assertEqual(data['student_name'], 'Ayesha')
        self.assertTrue(data['is_full_intro'])  # day 1
        self.assertIn('resolved_urls', data['avatar_assets'])
        self.assertNotIn('avatar_dir', data['avatar_assets'])
        self.assertEqual(data['lesson']['required_watch_seconds'], 180)
        self.assertEqual(data['watch_time_url'], f'/lesson/{lesson.id}/watch-time/')

    def test_other_students_lesson_is_404(self):
        res = self.client.get(f'/api/v1/lessons/{self.other_lessons[0].id}/')
        self.assertEqual(res.status_code, 404)

    def test_missing_lesson_is_404(self):
        self.assertEqual(self.client.get('/api/v1/lessons/999999/').status_code, 404)

    def test_admin_can_preview(self):
        admin = User.objects.create_user('staff', 'staff@example.com', 'p', is_staff=True)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(f'/api/v1/lessons/{self.lessons[0].id}/').status_code, 200)

    def test_legacy_template_view_still_renders(self):
        res = self.client.get(f'/daily-lesson/{self.lessons[0].id}/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'id="presentationData"')
        self.assertEqual(self.client.get(f'/daily-lesson/{self.other_lessons[0].id}/').status_code, 404)

    def test_watch_time_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        url = f'/lesson/{self.lessons[0].id}/watch-time/'
        self.assertEqual(csrf_client.post(url, data='{"seconds": 5}', content_type='application/json').status_code, 403)
        csrf_client.get('/api/v1/auth/csrf/')
        token = csrf_client.cookies['csrftoken'].value
        res = csrf_client.post(url, data='{"seconds": 5}', content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['watch_time_seconds'], 5)


@mock.patch('alvixapp.page_context.lessons.evaluate_submission_with_ai', return_value=GRADE)
class AssignmentApiTests(LessonApiBase):
    def test_get_returns_context_and_sets_issue_date(self, _grade):
        lesson = self.lessons[0]
        res = self.client.get('/api/v1/lessons/assignment/', {'lesson_id': lesson.id})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['lesson']['id'], lesson.id)
        self.assertIn('slotted page header parser', data['assignment_prompt'])
        self.assertTrue(data['is_practical'])
        self.assertFalse(data['is_expired'])
        self.assertIsNone(data['latest_submission'])
        self.assertEqual(data['all_submissions'], [])
        self.assertEqual(data['assignment_display']['rubric'][0], ['Correctness', '4'])
        self.assertEqual(data['assignment_display']['rubric'][1], ['Code_Quality', '3'])
        self.assertIsNotNone(data['lesson']['assignment_issued_at'])
        lesson.refresh_from_db()
        self.assertIsNotNone(lesson.assignment_issued_at)

    def test_other_students_lesson_id_falls_back_to_own_lesson(self, _grade):
        res = self.client.get('/api/v1/lessons/assignment/', {'lesson_id': self.other_lessons[0].id})
        self.assertEqual(res.json()['lesson']['id'], self.lessons[0].id)

    def test_no_course_redirects_to_mycourse(self, _grade):
        loner = User.objects.create_user('loner', 'loner@example.com', 'p')
        self.client.force_login(loner)
        data = self.client.get('/api/v1/lessons/assignment/').json()
        self.assertEqual(data['redirect'], '/mycourse/')
        self.assertEqual(data['messages'], [{'tags': 'warning', 'message': 'First generate your course.'}])

    def test_post_empty_is_rejected_with_message(self, grade):
        res = self.client.post(f'/api/v1/lessons/assignment/?lesson_id={self.lessons[0].id}', {'student_submission': '  '})
        self.assertEqual(res.status_code, 400)
        msg = 'Please provide source code/notes or upload a completed solution file.'
        self.assertEqual(res.json()['error'], msg)
        self.assertEqual(res.json()['messages'][0]['tags'], 'error')
        self.assertFalse(AssignmentSubmission.objects.exists())
        grade.assert_not_called()

    def test_post_saves_submission_with_telemetry(self, _grade):
        lesson = self.lessons[0]
        res = self.client.post(f'/api/v1/lessons/assignment/?lesson_id={lesson.id}', {
            'student_submission': 'def parse(header): return header.split()',
            'paste_count': '2', 'pasted_chars_total': '40', 'typing_duration_seconds': '75', 'keystroke_count': '120',
            'file_submission': SimpleUploadedFile('solution.py', b'print(1)\n', content_type='text/x-python'),
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['messages'], [{'tags': 'success', 'message': 'Assignment successfully submitted! Rubric score: 8/10 marks.'}])
        sub = AssignmentSubmission.objects.get(user=self.user, lesson=lesson)
        self.assertEqual((sub.paste_count, sub.pasted_chars_total, sub.typing_duration_seconds, sub.keystroke_count), (2, 40, 75, 120))
        self.assertEqual((sub.score, sub.marks, sub.total_marks), (8, 8, 10))
        self.assertTrue(sub.file_submission.name.startswith('assignment_files/'))
        lesson.refresh_from_db()
        self.assertTrue(lesson.is_completed)

        data = self.client.get('/api/v1/lessons/assignment/', {'lesson_id': lesson.id}).json()
        self.assertEqual(data['latest_submission']['total_marks'], 10)
        self.assertIn('Rubric Feedback: Scored 8/10 marks.', data['latest_submission']['ai_feedback'])
        self.assertEqual(len(data['all_submissions']), 1)
        row = data['all_submissions'][0]
        self.assertEqual(row['lesson']['day_number'], 1)
        self.assertTrue(row['file_submission'].startswith('/media/assignment_files/'))
        sub.file_submission.delete(save=False)

    def test_output_screenshot_is_saved_and_listed(self, grade):
        lesson = self.lessons[0]
        res = self.client.post(f'/api/v1/lessons/assignment/?lesson_id={lesson.id}', {
            'student_submission': 'print("hello")',
            'output_image': png_upload('output.png'),
        })
        self.assertEqual(res.status_code, 200)
        sub = AssignmentSubmission.objects.get(user=self.user, lesson=lesson)
        self.assertTrue(sub.output_image.name.startswith('assignment_outputs/'))
        self.assertIsNotNone(grade.call_args.kwargs['output_image'])
        data = self.client.get('/api/v1/lessons/assignment/', {'lesson_id': lesson.id}).json()
        self.assertTrue(data['all_submissions'][0]['output_image'].startswith('/media/assignment_outputs/'))
        self.assertTrue(data['latest_submission']['output_image'].startswith('/media/assignment_outputs/'))
        sub.output_image.delete(save=False)

    def test_output_screenshot_alone_is_a_valid_submission(self, _grade):
        res = self.client.post(f'/api/v1/lessons/assignment/?lesson_id={self.lessons[0].id}', {
            'output_image': png_upload('run.png'),
        })
        self.assertEqual(res.status_code, 200)
        AssignmentSubmission.objects.get(user=self.user).output_image.delete(save=False)

    def test_output_screenshot_must_be_an_image(self, grade):
        res = self.client.post(f'/api/v1/lessons/assignment/?lesson_id={self.lessons[0].id}', {
            'student_submission': 'code',
            'output_image': SimpleUploadedFile('output.png', b'<script>alert(1)</script>', content_type='image/png'),
        })
        self.assertEqual(res.status_code, 400)
        self.assertFalse(AssignmentSubmission.objects.exists())
        grade.assert_not_called()

    def test_issue_date_is_set_only_for_the_opened_day(self, _grade):
        self.client.get('/api/v1/lessons/assignment/', {'lesson_id': self.lessons[0].id})
        day1, day2 = (DailyLesson.objects.get(pk=lesson.pk) for lesson in self.lessons)
        self.assertIsNotNone(day1.assignment_issued_at)
        self.assertIsNotNone(day1.deadline)
        self.assertIsNone(day2.assignment_issued_at)  # not issued until the student opens it
        self.assertIsNone(day2.deadline)

    def test_assignment_without_lesson_id_opens_first_unsubmitted_day(self, _grade):
        AssignmentSubmission.objects.create(user=self.user, lesson=self.lessons[0], submitted_answer='x')
        data = self.client.get('/api/v1/lessons/assignment/').json()
        self.assertEqual(data['lesson']['id'], self.lessons[1].id)

    def test_legacy_view_post_still_works(self, _grade):
        lesson = self.lessons[0]
        res = self.client.post(f'/assignment/?lesson_id={lesson.id}', {'student_submission': 'My written answer.'})
        self.assertRedirects(res, f'/assignment/?lesson_id={lesson.id}', fetch_redirect_response=False)
        self.assertTrue(AssignmentSubmission.objects.filter(user=self.user, lesson=lesson).exists())
        self.assertEqual(self.client.get(f'/assignment/?lesson_id={lesson.id}').status_code, 200)


class QuizApiTests(LessonApiBase):
    def test_get_hides_correct_answers(self):
        lesson = self.lessons[0]
        res = self.client.get('/api/v1/lessons/quiz/', {'lesson_id': lesson.id})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual([q['id'] for q in data['quiz_questions']], [1, 2])
        self.assertEqual(data['quiz_questions'][0]['text'], 'Q one?')
        for q in data['quiz_questions']:
            self.assertNotIn('correct', q)
            self.assertNotIn('explanation', q)
        self.assertIsNotNone(data['lesson']['quiz_issued_at'])
        self.assertIsNone(data['latest_submission'])

    def test_other_students_lesson_is_not_used(self):
        data = self.client.get('/api/v1/lessons/quiz/', {'lesson_id': self.other_lessons[0].id}).json()
        self.assertEqual(data['lesson']['id'], self.lessons[0].id)

    def test_no_lesson_redirects_to_dashboard(self):
        loner = User.objects.create_user('loner', 'loner@example.com', 'p')
        self.client.force_login(loner)
        data = self.client.get('/api/v1/lessons/quiz/').json()
        self.assertEqual(data['redirect'], '/dashboard/')
        self.assertEqual(data['messages'][0]['message'], 'No lesson available for quiz.')

    def test_post_pass_records_result(self):
        lesson = self.lessons[0]
        res = self.client.post(f'/api/v1/lessons/quiz/?lesson_id={lesson.id}', {'q_1': 'B', 'q_2': 'X'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['messages'], [{
            'tags': 'success', 'message': 'Quiz passed with 2/2 correct answers (100%)!',
        }])
        sub = QuizSubmission.objects.get(user=self.user, lesson=lesson)
        self.assertEqual((sub.score, sub.total_questions, sub.percentage), (2, 2, 100))

        data = self.client.get('/api/v1/lessons/quiz/', {'lesson_id': lesson.id}).json()
        self.assertEqual(data['latest_submission']['score'], 2)
        self.assertEqual(len(data['all_submissions']), 1)
        self.assertIn('Q1: Q one?', data['all_submissions'][0]['question_summary'])

    def test_post_fail_lists_wrong_answers(self):
        lesson = self.lessons[0]
        res = self.client.post(f'/api/v1/lessons/quiz/?lesson_id={lesson.id}', {'q_1': 'A'})
        self.assertEqual(res.json()['messages'][0]['tags'], 'warning')
        data = self.client.get('/api/v1/lessons/quiz/', {'lesson_id': lesson.id}).json()
        wrong = data['latest_submission']['wrong_answers_explanation']
        self.assertEqual([w['question_number'] for w in wrong], [1, 2])
        self.assertEqual(wrong[1]['user_answer'], 'No answer provided')

    def test_second_attempt_is_not_recorded_twice(self):
        lesson = self.lessons[0]
        url = f'/api/v1/lessons/quiz/?lesson_id={lesson.id}'
        self.client.post(url, {'q_1': 'B', 'q_2': 'X'})
        res = self.client.post(url, {'q_1': 'A', 'q_2': 'Y'})  # double click / retry / second tab
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['messages'][0]['tags'], 'info')
        self.assertEqual(QuizSubmission.objects.filter(user=self.user, lesson=lesson).count(), 1)
        self.assertEqual(QuizSubmission.objects.get(user=self.user, lesson=lesson).score, 2)  # first result kept

    def test_old_duplicate_attempts_are_listed_once(self):
        lesson = self.lessons[0]
        for score in (1, 2):  # duplicates recorded before the one-attempt rule
            QuizSubmission.objects.create(user=self.user, lesson=lesson, score=score, total_questions=2, percentage=score * 50)
        data = self.client.get('/api/v1/lessons/quiz/', {'lesson_id': lesson.id}).json()
        self.assertEqual(len(data['all_submissions']), 1)
        self.assertEqual(data['all_submissions'][0]['id'], data['latest_submission']['id'])
        self.assertEqual(QuizSubmission.objects.filter(user=self.user, lesson=lesson).count(), 2)  # nothing deleted

    def test_quiz_without_lesson_id_opens_first_unattempted_day(self):
        QuizSubmission.objects.create(user=self.user, lesson=self.lessons[0], score=2, total_questions=2, percentage=100)
        data = self.client.get('/api/v1/lessons/quiz/').json()
        self.assertEqual(data['lesson']['id'], self.lessons[1].id)

    def test_legacy_quiz_detail_view(self):
        lesson = self.lessons[0]
        self.assertEqual(self.client.get(f'/quiz/{lesson.id}/').status_code, 200)
        res = self.client.post(f'/quiz/?lesson_id={lesson.id}', {'q_1': 'B', 'q_2': 'X'})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(QuizSubmission.objects.filter(user=self.user).count(), 1)
