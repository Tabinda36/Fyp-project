"""Lecture narration: each slide opens with its own topic; the lesson title is not repeated."""

from django.contrib.auth.models import User
from django.test import TestCase

from .models import AdminCourse, DailyLesson, GeneratedCourse
from .ppt_generator import (
    NARRATION_VERSION, _short_lesson_topic, _spoken_slide_topic, enrich_lecture_with_narrations,
)

TITLE = 'Day 1: Computational Foundations & Problem Deconstruction - In-Depth Study'
SHORT = 'Computational Foundations & Problem Deconstruction'


class NarrationTests(TestCase):
    def setUp(self):
        user = User.objects.create_user('s', 's@example.com', 'Str0ng-pass!')
        admin_course = AdminCourse.objects.create(title='Python Programming Masterclass', slug='py', course_code='PY')
        course = GeneratedCourse.objects.create(user=user, admin_course=admin_course, slug='py-gen')
        self.lesson = DailyLesson.objects.create(generated_course=course, day_number=1, title=TITLE,
                                                 content=f'<p>{TITLE} core content.</p>')

    def test_topic_helpers(self):
        self.assertEqual(_short_lesson_topic(TITLE), SHORT)
        self.assertEqual(_spoken_slide_topic(f'Theoretical Mechanics & Principles: {TITLE}', TITLE, SHORT),
                         'Theoretical Mechanics & Principles')
        self.assertEqual(_spoken_slide_topic(TITLE, TITLE, SHORT), SHORT)
        self.assertEqual(_spoken_slide_topic('Day 1 Laboratory Engineering Challenge', TITLE, SHORT),
                         'Laboratory Engineering Challenge')

    def _deck(self):
        slides = [
            {'type': 'cover', 'title': TITLE},
            {'type': 'overview', 'title': 'Lecture Roadmap & Learning Objectives',
             'learning_objectives': [f'Understand {TITLE}']},
            {'type': 'concepts', 'title': f'Theoretical Mechanics & Principles: {TITLE}',
             'concept_1': {'name': 'A', 'points': [f'Core model governing {TITLE} in production.']}},
        ] + [{'type': 'academic', 'title': f'Deep dive {i}', 'key_points': ['point']} for i in range(8)]
        return {'slides_list': slides}

    def test_slides_open_with_their_topic_without_repeating_lesson_title(self):
        data = enrich_lecture_with_narrations(self._deck(), self.lesson)
        slides = data['slides_list']
        self.assertEqual(data['narration_version'], NARRATION_VERSION)
        self.assertTrue(slides[1]['narration'].startswith('Lecture Roadmap & Learning Objectives. '))
        self.assertTrue(slides[2]['narration'].startswith('Theoretical Mechanics & Principles. '))
        for s in slides:
            self.assertNotIn(TITLE, s['narration'])
        for s in slides[1:]:
            self.assertNotIn('Slide ', s['narration'].split('.')[0])

    def test_outdated_template_narration_is_regenerated_but_custom_narration_is_kept(self):
        deck = self._deck()
        old = 'We now arrive at Slide 3: Core Theoretical Mechanics for ' + TITLE + '. ' + 'word ' * 500
        custom = 'Teacher notes written by the admin. ' + 'word ' * 500
        deck['slides_list'][2]['narration'] = old
        deck['slides_list'][1]['narration'] = custom
        slides = enrich_lecture_with_narrations(deck, self.lesson)['slides_list']
        self.assertTrue(slides[2]['narration'].startswith('Theoretical Mechanics & Principles. '))
        self.assertTrue(slides[1]['narration'].startswith('Teacher notes written by the admin.'))
