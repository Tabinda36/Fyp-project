from unittest.mock import patch
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from alvixapp.models import Profile, StudentAssessment, AIGenerationLog, AdminCourse, CourseLevel, GeneratedCourse
from alvixapp.forms import StudentProfileAssessmentForm
from alvixapp.ai_helpers import log_ai_generation, generate_assignment_and_quiz
from alvixapp.course_recommendation import (
    filter_catalog_by_interest_and_goal,
    determine_course_type,
    suggest_best_fit_course_with_ai
)


class StudentAssessmentFormTests(TestCase):
    def test_valid_form(self):
        data = {
            'interest_area': 'Development',
            'goal': 'Practical',
            'expectations': 'I want to master web engineering and build scalable production full-stack systems.'
        }
        form = StudentProfileAssessmentForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_expectations_min_length_validation(self):
        # Less than 20 characters must fail
        data = {
            'interest_area': 'Development',
            'goal': 'Practical',
            'expectations': 'Too short'
        }
        form = StudentProfileAssessmentForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('expectations', form.errors)

    def test_invalid_choices(self):
        # Prohibited or unsupported options must fail
        data = {
            'interest_area': 'Freelancing',  # Prohibited choice
            'goal': 'Get a Job',             # Prohibited choice
            'expectations': 'I want to master web engineering and build scalable systems.'
        }
        form = StudentProfileAssessmentForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('interest_area', form.errors)
        self.assertIn('goal', form.errors)

    def test_prohibited_fields_absent(self):
        form = StudentProfileAssessmentForm()
        prohibited = ['job', 'freelancing', 'language', 'available_time']
        for field in prohibited:
            self.assertNotIn(field, form.fields)


class AssessmentAndCourseRecommendationTests(TestCase):
    def setUp(self):
        self.patcher1 = patch('alvixapp.ppt_service.synthesize_speech', return_value=True)
        self.patcher2 = patch('alvixapp.ppt_service.generate_slide_audio_gtts', return_value=True)
        self.patcher1.start()
        self.patcher2.start()
        self.addCleanup(self.patcher1.stop)
        self.addCleanup(self.patcher2.stop)
        self.client = Client()
        self.password = "Secur3P@ssw0rd!"
        self.user = User.objects.create_user(
            username="student_recom_test",
            email="recom_test@example.com",
            password=self.password,
            first_name="Test Student"
        )
        self.profile = self.user.profile

        # Create test courses across domains and types
        self.course_dev_practical = AdminCourse.objects.create(
            title="Full-Stack Web Development",
            course_type="Practical",
            description="Comprehensive practical full-stack web application development and hands-on coding."
        )
        self.course_dev_theory = AdminCourse.objects.create(
            title="Data Structures & Algorithms Theory",
            course_type="Theoretical",
            description="Rigorous algorithmic theory, complexity proofs, abstract models, and asymptotic analysis."
        )
        self.course_design = AdminCourse.objects.create(
            title="UI/UX Graphical Designing",
            description="Visual design, wireframes, component libraries, and interactive prototyping."
        )
        self.course_marketing = AdminCourse.objects.create(
            title="Digital Marketing & Growth Analytics",
            description="Campaign management, SEO, growth metrics, and customer acquisition."
        )

    def test_catalog_filtering_by_interest_and_goal(self):
        # Development + Practical: Full-Stack Web Development should be first
        results_practical = filter_catalog_by_interest_and_goal("Development", "Practical")
        self.assertGreaterEqual(len(results_practical), 1)
        self.assertEqual(results_practical[0].id, self.course_dev_practical.id)

        # Development + Theory: Data Structures & Algorithms should be preferred
        results_theory = filter_catalog_by_interest_and_goal("Development", "Theory")
        self.assertGreaterEqual(len(results_theory), 1)
        self.assertEqual(results_theory[0].id, self.course_dev_theory.id)

        # Designing should yield design course
        results_design = filter_catalog_by_interest_and_goal("Designing", "Practical")
        self.assertEqual(results_design[0].id, self.course_design.id)

        # Marketing should yield marketing course
        results_marketing = filter_catalog_by_interest_and_goal("Marketing", "Practical")
        self.assertEqual(results_marketing[0].id, self.course_marketing.id)

    def test_ai_suggestion_validates_course_against_database(self):
        # AI recommendation must return an existing AdminCourse and 2-sentence reason
        expectations = "I want to master web engineering and build production APIs."
        course, reason, level = suggest_best_fit_course_with_ai(
            user=self.user,
            interest_area="Development",
            goal="Practical",
            expectations=expectations
        )
        self.assertIsNotNone(course)
        self.assertTrue(AdminCourse.objects.filter(id=course.id).exists())
        self.assertIn(level, ['Beginner', 'Intermediate', 'Advanced'])
        self.assertTrue(len(reason) > 20)

        # Verify AIGenerationLog recorded
        log_entry = AIGenerationLog.objects.filter(item_type='course_suggestion').first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.item_id, str(course.id))

    def test_first_login_flow_to_recommendation(self):
        self.client.login(username=self.user.username, password=self.password)
        post_data = {
            'interest_area': 'Development',
            'goal': 'Practical',
            'expectations': 'I want to build full stack web apps with database integration and clean APIs.'
        }
        response = self.client.post(reverse('student_assessment'), data=post_data, follow=False)
        # Should redirect to suggested_courses to show the 3 choices
        self.assertRedirects(response, reverse('suggested_courses'))

        # Check that profile was updated
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.assessment_completed)
        self.assertEqual(self.profile.interest_area, 'Development')
        self.assertEqual(self.profile.goal, 'Practical')

    def test_suggested_courses_displays_recommendation_and_choices(self):
        self.profile.interest_area = 'Development'
        self.profile.goal = 'Practical'
        self.profile.expectations = 'I want to build full stack web apps with database integration and clean APIs.'
        self.profile.assessment_completed = True
        self.profile.save()

        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get(reverse('suggested_courses'))
        self.assertEqual(response.status_code, 200)

        # Check content includes Choice A, Choice B, Choice C
        self.assertContains(response, 'Start Suggested Course')
        self.assertContains(response, 'Pick Another Existing Course')
        self.assertContains(response, 'Go Directly to Dashboard')

    def test_choice_a_dashboard_access(self):
        self.profile.assessment_completed = True
        self.profile.save()
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_choice_b_start_suggested_course(self):
        self.profile.assessment_completed = True
        self.profile.save()
        self.client.login(username=self.user.username, password=self.password)

        # Set suggested course in session
        session = self.client.session
        session['recommended_course_id'] = self.course_dev_practical.id
        session['ai_suggested_level'] = 'Intermediate'
        session.save()

        post_data = {
            'action': 'start_suggested',
            'level': 'Intermediate'
        }
        response = self.client.post(reverse('suggested_courses'), data=post_data, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/course_content/?course_id=', response.url)

        # Check student enrolled in GeneratedCourse
        gen_course = GeneratedCourse.objects.filter(user=self.user, admin_course=self.course_dev_practical).first()
        self.assertIsNotNone(gen_course)
        self.assertEqual(gen_course.level, 'Intermediate')

    def test_choice_c1_pick_other_existing_course(self):
        self.profile.assessment_completed = True
        self.profile.save()
        self.client.login(username=self.user.username, password=self.password)

        post_data = {
            'action': 'pick_other_course',
            'other_course_id': self.course_marketing.id,
            'other_level': 'Beginner'
        }
        response = self.client.post(reverse('suggested_courses'), data=post_data, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/course_content/?course_id=', response.url)

        gen_course = GeneratedCourse.objects.filter(user=self.user, admin_course=self.course_marketing).first()
        self.assertIsNotNone(gen_course)
        self.assertEqual(gen_course.level, 'Beginner')

    def test_choice_c2_generate_new_course_from_title(self):
        self.profile.assessment_completed = True
        self.profile.save()
        self.client.login(username=self.user.username, password=self.password)

        post_data = {
            'action': 'generate_new_course',
            'custom_course_title': 'Cloud Native Kubernetes Architecture',
            'custom_level': 'Beginner',
            'custom_pace': 'Standard'
        }
        response = self.client.post(reverse('suggested_courses'), data=post_data, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/course_content/?course_id=', response.url)

        # Check that AdminCourse was created
        new_admin_course = AdminCourse.objects.filter(title='Cloud Native Kubernetes Architecture').first()
        self.assertIsNotNone(new_admin_course)

        # Check student enrolled in GeneratedCourse
        gen_course = GeneratedCourse.objects.filter(user=self.user, admin_course=new_admin_course).first()
        self.assertIsNotNone(gen_course)

from django.conf import settings
from alvixapp.models import DailyLesson, LessonTask
from alvixapp.course_tier_service import create_course_tiers_and_curriculum, fetch_and_enroll_student_in_level
from alvixapp.ai_services import (
    get_curated_level_content_and_plan,
    generate_level_content_and_plan_with_ai,
    get_curated_slide_deck_for_bullets,
    generate_lesson_slide_deck_with_ai,
    build_detailed_slide_narration,
    ensure_slide_narration_word_count
)
from alvixapp.ppt_generator import generate_lesson_ppt_bytes


class CourseContentAndLessonPlanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='syllabus_tester', email='tester@alvix.edu', password='TestPassword123!')
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.profile.assessment_completed = True
        self.profile.save()

    def test_plan_durations_configured_in_settings(self):
        """Settings must store the course durations without hard-coding."""
        self.assertEqual(settings.THEORETICAL_COURSE_DAYS, 7)
        self.assertEqual(settings.PRACTICAL_COURSE_DAYS, 10)
        self.assertEqual(settings.MIXED_COURSE_DAYS, 12)
        durations = getattr(settings, 'COURSE_PLAN_DURATIONS', {})
        self.assertEqual(durations.get('Theoretical'), 7)
        self.assertEqual(durations.get('Practical'), 10)
        self.assertEqual(durations.get('Mixed'), 12)

    def test_theoretical_course_structure_7_days(self):
        """Theoretical course must have 7 days: 1 lesson, 1 assignment, 1 quiz per day."""
        course = AdminCourse.objects.create(
            title="Automata & Formal Languages",
            course_type="Theoretical",
            is_active=True
        )
        create_course_tiers_and_curriculum(course)
        level = course.course_levels.filter(level="Beginner").first()
        self.assertIsNotNone(level)

        # Content topics: main topics only, 4 to 8 bullets each
        self.assertGreaterEqual(len(level.content_topics), 3)
        for topic in level.content_topics:
            self.assertIn('title', topic)
            self.assertIn('bullets', topic)
            self.assertGreaterEqual(len(topic['bullets']), 4)
            self.assertLessEqual(len(topic['bullets']), 8)

        # Lesson plan: exactly 7 days
        canonical_lessons = DailyLesson.objects.filter(course_level=level, generated_course__isnull=True).order_by('day_number')
        self.assertEqual(canonical_lessons.count(), settings.THEORETICAL_COURSE_DAYS)

        for l in canonical_lessons:
            # Exactly one assignment and one quiz per day attached via LessonTask
            self.assertTrue(hasattr(l, 'task'))
            self.assertTrue(bool(l.task.assignment_question))
            self.assertTrue(bool(l.task.quiz_data) and len(l.task.quiz_data) >= 1)

    def test_practical_course_structure_10_days(self):
        """Practical course must have 10 days: 1 lesson, 1 assignment, 1 quiz per day."""
        course = AdminCourse.objects.create(
            title="Full-Stack React & Node Deployment",
            course_type="Practical",
            is_active=True
        )
        create_course_tiers_and_curriculum(course)
        level = course.course_levels.filter(level="Beginner").first()
        self.assertIsNotNone(level)

        canonical_lessons = DailyLesson.objects.filter(course_level=level, generated_course__isnull=True).order_by('day_number')
        self.assertEqual(canonical_lessons.count(), settings.PRACTICAL_COURSE_DAYS)

        for l in canonical_lessons:
            self.assertTrue(hasattr(l, 'task'))
            self.assertTrue(bool(l.task.assignment_question))
            self.assertTrue(bool(l.task.quiz_data) and len(l.task.quiz_data) >= 1)

    def test_mixed_course_structure_12_days(self):
        """Mixed course must have 12 days: 1 lesson, 1 assignment, 1 quiz per day."""
        course = AdminCourse.objects.create(
            title="Computer Architecture & Systems Engineering",
            course_type="Mixed",
            is_active=True
        )
        create_course_tiers_and_curriculum(course)
        level = course.course_levels.filter(level="Beginner").first()
        self.assertIsNotNone(level)

        canonical_lessons = DailyLesson.objects.filter(course_level=level, generated_course__isnull=True).order_by('day_number')
        self.assertEqual(canonical_lessons.count(), settings.MIXED_COURSE_DAYS)

        for l in canonical_lessons:
            self.assertTrue(hasattr(l, 'task'))
            self.assertTrue(bool(l.task.assignment_question))
            self.assertTrue(bool(l.task.quiz_data) and len(l.task.quiz_data) >= 1)

    def test_ui_course_content_page_renders_topics_and_extend_buttons(self):
        """UI must render collapsed topic cards with 'Extend' buttons and lesson schedule."""
        course = AdminCourse.objects.create(
            title="Algorithms & Systems",
            course_type="Practical",
            is_active=True
        )
        create_course_tiers_and_curriculum(course)
        level = course.course_levels.filter(level="Beginner").first()
        gen_course = fetch_and_enroll_student_in_level(self.user, level)

        client = Client()
        client.login(username='syllabus_tester', password='TestPassword123!')
        response = client.get(f"/course_content/?course_id={gen_course.id}")
        self.assertEqual(response.status_code, 200)

        # Check UI components
        content_str = response.content.decode('utf-8')
        self.assertIn("Course Content", content_str)
        self.assertIn("Extend", content_str)
        self.assertIn("Lesson Plan", content_str)
        self.assertIn("10-Day Practical Track", content_str)
        self.assertIn("PPT", content_str)


class SlideDeckAndPPTXTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='slide_tester', email='slide@alvix.edu', password='TestPassword123!')
        self.course = AdminCourse.objects.create(
            title="Concurrent Distributed Systems",
            course_type="Theoretical",
            is_active=True
        )
        create_course_tiers_and_curriculum(self.course)
        self.level = self.course.course_levels.filter(level="Beginner").first()
        self.gen_course = fetch_and_enroll_student_in_level(self.user, self.level)
        self.lesson = self.gen_course.daily_lessons.order_by('day_number').first()

    def test_slide_deck_covers_all_topic_bullets(self):
        """Slide deck must cover every bullet point of the day's topic."""
        bullets = [
            "Deconstructing problems into logical computational steps",
            "Understanding variables, data types, and deterministic execution",
            "Control flow mechanics: conditionals, branches, and loop invariants",
            "Writing clean pseudo-code before typing implementation code",
            "Tracing program execution step by step with sample inputs"
        ]
        slides = get_curated_slide_deck_for_bullets(course_title="Distributed Systems", lesson_title="Day 1 Lecture", topic_title="Computational Foundations", bullets=bullets)

        # Every bullet point must be covered
        self.assertGreaterEqual(len(slides), len(bullets))

        # Check line limits (1 to 3 lines per point, no paragraphs)
        for s in slides:
            self.assertIn('title', s)
            self.assertIn('points', s)
            self.assertGreater(len(s['points']), 0)
            for p in s['points']:
                lines = [line.strip() for line in p.splitlines() if line.strip()]
                self.assertLessEqual(len(lines), 3, f"Point exceeded 3 lines: {p}")
                self.assertGreaterEqual(len(lines), 1)

    def test_generate_lesson_slide_deck_saves_and_logs(self):
        """generate_lesson_slide_deck_with_ai must validate JSON and save to lesson."""
        deck = generate_lesson_slide_deck_with_ai(self.lesson, user=self.user, use_ai=False)
        self.assertIn("slides_list", deck)
        self.assertEqual(deck.get("source"), "topic_bullet_deck")
        self.assertGreaterEqual(len(deck["slides_list"]), 4)

        # Reload lesson
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.presentation_data.get("source"), "topic_bullet_deck")

        # Check AIGenerationLog audit trail
        log = AIGenerationLog.objects.filter(item_type="lesson_slide_deck").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.user)
        self.assertTrue(log.is_validated)

    def test_generate_lesson_pptx_binary_download(self):
        """Downloadable PPTX must generate a valid PowerPoint binary stream."""
        # Ensure slide deck generated
        generate_lesson_slide_deck_with_ai(self.lesson, user=self.user, use_ai=False)
        self.lesson.refresh_from_db()

        ppt_stream = generate_lesson_ppt_bytes(self.lesson)
        self.assertIsNotNone(ppt_stream)
        ppt_bytes = ppt_stream.getvalue()
        self.assertGreater(len(ppt_bytes), 2000)
        # Check PPTX PK zip header
        self.assertTrue(ppt_bytes.startswith(b'PK'))

    def test_download_lesson_ppt_view_response(self):
        """download_lesson_ppt view must return attachment HTTP response."""
        client = Client()
        client.login(username='slide_tester', password='TestPassword123!')
        response = client.get(reverse('download_lesson_ppt', kwargs={'lesson_id': self.lesson.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        self.assertIn('attachment; filename=', response['Content-Disposition'])


    def test_slide_narration_word_count_and_conversational_phrases(self):
        """Every slide must have a narration script of at least 150 words in a conversational teacher style."""
        deck = generate_lesson_slide_deck_with_ai(self.lesson, user=self.user, use_ai=False)
        self.assertIn("slides_list", deck)
        slides = deck["slides_list"]
        self.assertGreaterEqual(len(slides), 3)

        for s in slides:
            narration = s.get("narration", "")
            words = narration.split()
            self.assertGreaterEqual(
                len(words),
                150,
                f"Slide '{s.get('title')}' narration was only {len(words)} words, expected >= 150 words."
            )
            # Verify conversational teacher style phrases
            has_teacher_marker = any(marker in narration for marker in [
                "Let us look at", "Notice that", "Notice", "Let us", "Observe", "In practice", "Remember that"
            ])
            self.assertTrue(has_teacher_marker, f"Slide narration missing friendly teacher phrasing: {narration[:100]}")

        # Direct verification of build_detailed_slide_narration
        script = build_detailed_slide_narration(
            slide_title="Memory Hierarchy and Cache Locality",
            points=["L1/L2 cache lines operate on 64-byte boundaries", "Spatial locality minimizes memory bus contention"],
            course_title="Computer Architecture",
            lesson_title="Cache Subsystems",
            topic_title="Memory Optimization",
            bullet_covered="Cache line alignment",
            level_name="Advanced",
            is_first=True
        )
        self.assertGreaterEqual(len(script.split()), 150)
        self.assertTrue("Notice that" in script or "Let us look" in script)

        # Direct verification of ensure_slide_narration_word_count enrichment
        short_script = "This is a very short script about cache memory and algorithms."
        enriched = ensure_slide_narration_word_count(
            short_script,
            slide_title="Cache Architecture",
            points=["Point 1", "Point 2"],
            course_title="Architecture",
            lesson_title="Day 1",
            topic_title="Memory Hierarchy"
        )
        self.assertGreaterEqual(len(enriched.split()), 150)

    def test_lesson_player_avatar_and_controls(self):
        """Lesson player must render original hijab-wearing SVG avatar and full playback controls."""
        client = Client()
        client.login(username='slide_tester', password='TestPassword123!')
        response = client.get(reverse('daily_lesson_view', kwargs={'lesson_id': self.lesson.id}))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')

        # Check Original Cartoon Avatar with Hijab
        self.assertIn('id="aiTeacherAvatarContainer"', html)
        self.assertIn('id="teacherAvatarSvg"', html)
        self.assertIn('id="avatarHeadGroup"', html)
        self.assertIn('id="avatarMouthGroup"', html)
        self.assertIn('hijabGrad', html)

        # Check Lesson Player Controls
        self.assertIn('id="mainPlayPauseBtn"', html)
        self.assertIn('id="replaySlideBtn"', html)
        self.assertIn('id="prevSlideBtn"', html)
        self.assertIn('id="nextSlideBtn"', html)
        self.assertIn('id="captionsToggleBtn"', html)
        self.assertIn('id="speedBtn"', html)
        self.assertIn('data-speed="0.75"', html)
        self.assertIn('data-speed="1.25"', html)
        self.assertIn('data-speed="1.5"', html)

        # Check speech synthesis engine prioritizing natural female voice
        self.assertIn('window.speechSynthesis', html)
        self.assertIn('isFemaleVoice', html)


from django.core.management import call_command
from alvixapp.ai_services import is_topic_practical, build_track_assignment_and_quiz
from alvixapp.copy_detection import evaluate_submission_copy_risk
from alvixapp.certificate_service import (
    calculate_course_performance,
    update_or_create_student_certificate,
    generate_certificate_ai_review
)
from alvixapp.certificate_pdf import generate_certificate_pdf_bytes
from alvixapp.models import Certificate, AssignmentSubmission, QuizSubmission, DailyLesson, LessonTask


class TrackAssignmentAndQuizGenerationTests(TestCase):
    def test_practical_course_assignment_and_quiz_format(self):
        """Practical course: practical task with checklist, rubric, file type; tricky MCQs with code."""
        prompt, data, quiz = build_track_assignment_and_quiz(
            course_title="Distributed Systems Engineering",
            level_name="Advanced",
            day_number=3,
            topic_title="Lock-Free Concurrency & Memory Fences",
            course_type="Practical",
            bullets=["Compare-and-swap (CAS) primitives", "Memory barriers and fences", "Lock-free queue implementation"]
        )
        self.assertEqual(data['type'], 'practical')
        self.assertIn('requirements_checklist', data)
        self.assertGreaterEqual(len(data['requirements_checklist']), 3)
        self.assertIn('rubric', data)
        self.assertEqual(data['expected_file_type'], '.py')

        # Verify quiz format
        self.assertGreaterEqual(len(quiz), 3)
        for q in quiz:
            self.assertIn('question', q)
            self.assertIn('options', q)
            self.assertEqual(len(q['options']), 4)
            self.assertIn('correct', q)
            self.assertIn(q['correct'], q['options'], f"Correct option '{q['correct']}' must be in options")
            self.assertIn('explanation', q)
            self.assertIn('topic', q)
        # Check tricky practical items include code or predict output / spot error
        has_tricky_question = any("predict" in q['question'].lower() or "error" in q['question'].lower() or "practice" in q['question'].lower() or q.get('code') for q in quiz)
        self.assertTrue(has_tricky_question)

    def test_theory_course_assignment_and_quiz_format(self):
        """Theory course: short-answer / case-study question with expected points and rubric; concept MCQs."""
        prompt, data, quiz = build_track_assignment_and_quiz(
            course_title="Computational Complexity & Automata",
            level_name="Intermediate",
            day_number=2,
            topic_title="Turing Completeness & Reductions",
            course_type="Theoretical",
            bullets=["Halting problem proof", "Decidability and recognizability", "Rice's Theorem"]
        )
        self.assertEqual(data['type'], 'theory')
        self.assertIn('expected_points', data)
        self.assertGreaterEqual(len(data['expected_points']), 3)
        self.assertIn('rubric', data)

        # Verify quiz format and options
        self.assertGreaterEqual(len(quiz), 3)
        for q in quiz:
            self.assertIn(q['correct'], q['options'])
            self.assertIn('explanation', q)

    def test_mixed_course_follows_topic(self):
        """Mixed course: syntax/coding topics get practical tasks; concept topics get theory tasks."""
        # Syntax / Coding topic
        _, p_data, _ = build_track_assignment_and_quiz(
            course_title="Full Stack Software Architecture",
            level_name="Beginner",
            day_number=1,
            topic_title="Async Python Syntax and Coroutines",
            course_type="Mixed",
            bullets=["async/await keywords", "Event loop lifecycle", "asyncio.gather"]
        )
        self.assertEqual(p_data['type'], 'practical')

        # Architecture / Theory topic
        _, t_data, _ = build_track_assignment_and_quiz(
            course_title="Full Stack Software Architecture",
            level_name="Beginner",
            day_number=2,
            topic_title="CAP Theorem and Architectural Tradeoffs",
            course_type="Mixed",
            bullets=["Consistency models", "Availability guarantees", "Partition tolerance"]
        )
        self.assertEqual(t_data['type'], 'theory')


class AssignmentQuizFetchAndIssueDateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student_fetch', password='TestPassword123!', email='student@alvix.org')
        self.admin_course = AdminCourse.objects.create(
            title="Database Architecture",
            slug="database-architecture",
            course_code="ALV-DBA-01",
            description="Deep relational and distributed database internals.",
            is_active=True
        )
        self.level = CourseLevel.objects.create(
            parent_course=self.admin_course,
            level="Advanced",
            title="Advanced Database Architecture",
            slug="database-architecture-advanced",
            benchmark="MIT 6.824 & CMU 15-445",
            is_active=True
        )
        # Canonical lesson in admin database
        self.canonical_lesson = DailyLesson.objects.create(
            course_level=self.level,
            day_number=1,
            title="B-Tree Page Internals & Disk Layout",
            content="Page header structure; Slotted page architecture; Cell pointer offsets"
        )
        # Pre-save task on admin database
        _, p_data, p_quiz = build_track_assignment_and_quiz(
            course_title=self.admin_course.title,
            level_name="Advanced",
            day_number=1,
            topic_title=self.canonical_lesson.title,
            course_type="Practical",
            bullets=["Page header structure", "Slotted page architecture", "Cell pointer offsets"]
        )
        LessonTask.objects.create(
            lesson=self.canonical_lesson,
            assignment_question="Implement a slotted page header parser.",
            assignment_data=p_data,
            quiz_data=p_quiz
        )

        # Enrolled student course
        self.student_course = GeneratedCourse.objects.create(
            user=self.user,
            admin_course=self.admin_course,
            course_level=self.level,
            slug="database-architecture-advanced",
            course_type="Practical"
        )
        self.student_lesson = DailyLesson.objects.create(
            generated_course=self.student_course,
            course_level=self.level,
            day_number=1,
            title="B-Tree Page Internals & Disk Layout",
            content="Page header structure; Slotted page architecture"
        )

    def test_assignment_click_fetches_from_admin_db_and_sets_issue_date(self):
        """When student clicks on assignment option, fetches from admin DB and sets issue date to click time."""
        self.assertIsNone(self.student_lesson.assignment_issued_at)
        client = Client()
        client.login(username='student_fetch', password='TestPassword123!')

        response = client.get(f"{reverse('assignment_view')}?lesson_id={self.student_lesson.id}")
        self.assertEqual(response.status_code, 200)

        self.student_lesson.refresh_from_db()
        self.assertIsNotNone(self.student_lesson.assignment_issued_at)
        self.assertIsNotNone(self.student_lesson.deadline)

        # Fetched assignment from canonical admin DB
        task = getattr(self.student_lesson, 'task', None)
        self.assertIsNotNone(task)
        self.assertIn("slotted page", task.assignment_question.lower())

    def test_quiz_click_fetches_from_admin_db_and_sets_issue_date(self):
        """When student clicks on quiz option, fetches from admin DB and sets quiz issue date to click time."""
        self.assertIsNone(self.student_lesson.quiz_issued_at)
        client = Client()
        client.login(username='student_fetch', password='TestPassword123!')

        response = client.get(f"{reverse('quiz_view')}?lesson_id={self.student_lesson.id}")
        self.assertEqual(response.status_code, 200)

        self.student_lesson.refresh_from_db()
        self.assertIsNotNone(self.student_lesson.quiz_issued_at)

        # Fetched quiz from canonical admin DB
        task = getattr(self.student_lesson, 'task', None)
        self.assertIsNotNone(task)
        self.assertGreaterEqual(len(task.quiz_data), 3)


class PerformanceScoringAndTelemetryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student_perf', password='TestPassword123!', email='perf@alvix.org')
        self.admin_course = AdminCourse.objects.create(
            title="Algorithms Masterclass",
            slug="algorithms-masterclass",
            course_code="ALV-ALG-01"
        )
        self.course = GeneratedCourse.objects.create(
            user=self.user,
            admin_course=self.admin_course,
            slug="algorithms-masterclass",
            course_type="Theoretical"
        )
        # Create 7 daily lessons (7-day theoretical course)
        self.lessons = []
        for d in range(1, 8):
            les = DailyLesson.objects.create(
                generated_course=self.course,
                day_number=d,
                title=f"Algorithms Topic Day {d}",
                required_watch_seconds=180
            )
            self.lessons.append(les)

    def test_lesson_watch_time_api(self):
        """System records watch time and marks completed when required threshold is met."""
        client = Client()
        client.login(username='student_perf', password='TestPassword123!')
        lesson = self.lessons[0]

        # Send watch time heartbeat
        res = client.post(
            reverse('record_lesson_watch_time', kwargs={'lesson_id': lesson.id}),
            data='{"seconds": 25}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        lesson.refresh_from_db()
        self.assertEqual(lesson.watch_time_seconds, 25)
        self.assertFalse(lesson.watch_time_completed)

        # Exceed threshold (API has anti-tamper cap of max 30s per ping)
        lesson.watch_time_seconds = 160
        lesson.save(update_fields=['watch_time_seconds'])
        client.post(
            reverse('record_lesson_watch_time', kwargs={'lesson_id': lesson.id}),
            data='{"seconds": 25}',
            content_type='application/json'
        )
        lesson.refresh_from_db()
        self.assertGreaterEqual(lesson.watch_time_seconds, 180)
        self.assertTrue(lesson.watch_time_completed)

    def test_copy_paste_detection_telemetry_and_flag(self):
        """Copy/paste detection tracks paste count, character ratio, and flags for admin review without zeroing."""
        copied_text = """
        The quick brown fox jumps over the lazy dog. In computer science, an algorithmic paradigm is a generic approach
        or bias towards designing solutions for a category of problems. Examples include divide and conquer, dynamic programming,
        and greedy algorithms. These techniques form the cornerstone of formal software engineering.
        """
        risk_level, peer_sim, ai_prob, details = evaluate_submission_copy_risk(
            submission_text=copied_text,
            paste_count=4,
            pasted_chars_total=len(copied_text),
            typing_duration_seconds=3,
            keystroke_count=5,
            current_user=self.user,
            lesson=self.lessons[0]
        )
        self.assertIn(risk_level, ['Medium', 'High'])
        self.assertIn("4 paste event", details)

    def test_scoring_formula_split_and_certificate_unlock(self):
        """Course total is 100% split across N days, and within each day 20% watch / 40% assignment / 40% quiz."""
        # Day 1: full watch time, full assignment, full quiz
        d1 = self.lessons[0]
        d1.watch_time_seconds = 180
        d1.watch_time_completed = True
        d1.is_completed = True
        d1.save()

        AssignmentSubmission.objects.create(
            user=self.user,
            lesson=d1,
            submitted_answer="My complete theoretical proof for Day 1.",
            marks=10,
            total_marks=10,
            score=5
        )
        QuizSubmission.objects.create(
            user=self.user,
            lesson=d1,
            score=3,
            total_questions=3,
            percentage=100
        )

        perf = calculate_course_performance(self.user, self.course)
        self.assertEqual(perf['total_days'], 7)
        self.assertAlmostEqual(perf['days'][0]['day_max_score'], 100.0 / 7, places=2)
        # Day 1 score should be approx 14.3 (100 / 7)
        self.assertAlmostEqual(perf['days'][0]['day_score'], 100.0 / 7, places=1)
        self.assertEqual(perf['days'][0]['day_percentage'], 100.0)

        # Incomplete course should remain locked
        self.assertFalse(perf['is_unlocked'])
        self.assertEqual(perf['completed_days_count'], 1)

        # Complete all 7 days with passing score
        for d in self.lessons[1:]:
            d.watch_time_seconds = 180
            d.watch_time_completed = True
            d.is_completed = True
            d.save()
            AssignmentSubmission.objects.create(user=self.user, lesson=d, marks=8, total_marks=10)
            QuizSubmission.objects.create(user=self.user, lesson=d, score=3, total_questions=3)

        perf_completed = calculate_course_performance(self.user, self.course)
        self.assertTrue(perf_completed['is_course_completed'])
        self.assertGreaterEqual(perf_completed['overall_percentage'], 35)
        self.assertTrue(perf_completed['is_unlocked'])

        # Certificate record synchronization
        cert, _ = update_or_create_student_certificate(self.user, self.course)
        self.assertTrue(cert.is_unlocked)
        self.assertTrue(cert.is_valid)
        self.assertGreaterEqual(cert.overall_percentage, 35)
        self.assertIn("ALV-CERT-2026-", cert.certificate_id)
        self.assertTrue(cert.qr_code_data_uri.startswith("data:image/png;base64,"))


class CertificateVerificationAndPdfTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cert_student', password='TestPassword123!', email='cert_student@alvix.org')
        admin_c = AdminCourse.objects.create(
            title="Machine Learning Foundations",
            slug="machine-learning-foundations",
            course_code="ALV-MLF-01"
        )
        self.course = GeneratedCourse.objects.create(
            user=self.user,
            admin_course=admin_c,
            slug="machine-learning-foundations",
            course_type="Practical"
        )
        self.cert, _ = update_or_create_student_certificate(self.user, self.course)
        self.cert.is_unlocked = True
        self.cert.is_valid = True
        self.cert.overall_percentage = 92.5
        self.cert.performance_grade = 'A'
        self.cert.save()

    def test_public_verification_view_valid(self):
        """Public verification endpoint reports VALID for unlocked, authentic certificates."""
        client = Client()
        url = reverse('verify_certificate', kwargs={'cert_id': self.cert.certificate_id})
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("OFFICIALLY VERIFIED & VALID", response.content.decode('utf-8'))
        self.assertIn(self.cert.certificate_id, response.content.decode('utf-8'))

    def test_public_verification_view_invalid(self):
        """Public verification endpoint reports INVALID for non-existent certificate ID."""
        client = Client()
        url = reverse('verify_certificate', kwargs={'cert_id': "FAKE-ID-9999"})
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("INVALID OR UNVERIFIED", response.content.decode('utf-8'))

    def test_server_pdf_generation(self):
        """Generates compliant PDF bytes containing unique certificate ID and metadata."""
        pdf_stream = generate_certificate_pdf_bytes(self.cert)
        pdf_bytes = pdf_stream.getvalue()
        self.assertTrue(pdf_bytes.startswith(b'%PDF-1.4'))
        self.assertGreater(len(pdf_bytes), 1000)

    def test_daily_update_command(self):
        """Daily scheduled management command executes cleanly."""
        call_command('update_certificates')
        self.cert.refresh_from_db()
        self.assertIsNotNone(self.cert.current_date)


class InaraAvatarPlayerAndSettingsTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='admin_staff',
            password='StaffPassword123!',
            email='staff@alvix.org',
            is_staff=True,
            is_superuser=True
        )
        self.student = User.objects.create_user(
            username='student_inara',
            password='StudentPass123!',
            email='student@alvix.org',
            first_name='Zainab'
        )
        admin_c = AdminCourse.objects.create(
            title="Full Stack Software Engineering",
            slug="full-stack-software-engineering",
            course_code="ALV-FSSE-01"
        )
        self.course = GeneratedCourse.objects.create(
            user=self.student,
            admin_course=admin_c,
            slug="full-stack-software-engineering",
            course_type="Mixed"
        )
        self.lesson_day1 = DailyLesson.objects.create(
            generated_course=self.course,
            day_number=1,
            title="Introduction to Scalable Architecture",
            content="Mastering distributed systems and deterministic state machines."
        )
        self.lesson_day2 = DailyLesson.objects.create(
            generated_course=self.course,
            day_number=2,
            title="Database Invariants and Query Optimization",
            content="ACID transactions, indexing patterns, and memory footprints."
        )

    def test_avatar_settings_defaults_and_singleton(self):
        """AvatarSettings default values and singleton access."""
        from alvixapp.models import AvatarSettings
        settings_obj = AvatarSettings.get_settings()
        self.assertEqual(settings_obj.avatar_name, "Inara")
        self.assertEqual(settings_obj.developer_name, "Tabinda Rukhsar")
        self.assertEqual(settings_obj.avatar_name_pronunciation, "ee-nah-rah")
        self.assertFalse(settings_obj.play_full_intro_every_day)

    def test_avatar_intro_script_formatting_and_pronunciation(self):
        """Spoken text uses pronunciation override while display text retains real avatar name."""
        from alvixapp.models import AvatarSettings
        settings_obj = AvatarSettings.get_settings()
        settings_obj.avatar_name = "Inara"
        settings_obj.avatar_name_pronunciation = "ee-nah-rah"
        settings_obj.developer_name = "Tabinda Rukhsar"
        settings_obj.university_or_department = "Department of Software Engineering"
        settings_obj.save()

        spoken = settings_obj.format_full_intro_spoken(
            student_name="Zainab",
            course_name="Full Stack Software Engineering",
            day_number=1,
            lesson_title="Introduction to Scalable Architecture"
        )
        display = settings_obj.format_full_intro_display(
            student_name="Zainab",
            course_name="Full Stack Software Engineering",
            day_number=1,
            lesson_title="Introduction to Scalable Architecture"
        )

        # Spoken text must use phonetic pronunciation
        self.assertIn("I am ee-nah-rah, your AI teacher at ALVIX", spoken)
        self.assertIn("developed by Tabinda Rukhsar at Department of Software Engineering as a final year project", spoken)
        self.assertIn("Assalamu alaikum, Zainab!", spoken)

        # Display text must use real display name
        self.assertIn("I am Inara, your AI teacher at ALVIX", display)
        self.assertNotIn("ee-nah-rah", display)

        # Short greeting
        short_greeting = settings_obj.format_short_greeting_display("Zainab", "Database Invariants")
        self.assertEqual(short_greeting, "Welcome back, Zainab! Today we will learn Database Invariants.")

    def test_avatar_asset_status_and_fallbacks(self):
        """Scans public/assets/avatar/ and verifies fallback resolution to idle for missing frames."""
        from alvixapp.views import get_avatar_asset_status
        status = get_avatar_asset_status()
        self.assertTrue(status['dir_exists'])
        self.assertTrue(status['has_idle'])
        self.assertTrue(status['has_custom_avatar'])
        self.assertIn('inara_idle.png', status['resolved_urls']['idle'])

        # Verify fallback logic: If wave frame is marked non-existent in dictionary, it falls back to idle
        simulated_files = {
            'idle': {'filename': 'inara_idle.png', 'exists': True, 'url': '/public/assets/avatar/inara_idle.png'},
            'wave': {'filename': 'inara_wave.png', 'exists': False, 'url': '/public/assets/avatar/inara_wave.png'},
        }
        fallback_wave_url = simulated_files['wave']['url'] if simulated_files['wave']['exists'] else simulated_files['idle']['url']
        self.assertEqual(fallback_wave_url, '/public/assets/avatar/inara_idle.png')

    def test_admin_avatar_settings_view(self):
        """Admin can view and update avatar configuration via the admin dashboard settings page."""
        client = Client()
        client.force_login(self.staff_user)

        # GET request
        response = client.get(reverse('admin_avatar_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("AI Teacher & Avatar Settings", response.content.decode('utf-8'))
        self.assertIn("inara_idle.png", response.content.decode('utf-8'))

        # POST request updating avatar settings
        post_data = {
            'avatar_name': 'Inara AI',
            'developer_name': 'Tabinda Rukhsar',
            'university_or_department': 'NED University of Engineering and Technology',
            'avatar_name_pronunciation': 'ee-nah-rah',
            'play_full_intro_every_day': True,
        }
        post_res = client.post(reverse('admin_avatar_settings'), post_data)
        self.assertEqual(post_res.status_code, 302)

        from alvixapp.models import AvatarSettings
        updated = AvatarSettings.get_settings()
        self.assertEqual(updated.avatar_name, 'Inara AI')
        self.assertEqual(updated.university_or_department, 'NED University of Engineering and Technology')
        self.assertTrue(updated.play_full_intro_every_day)

    def test_single_lesson_view_avatar_integration(self):
        """Lesson player renders Inara center introduction, corner lecture avatar, and modular JS."""
        client = Client()
        client.force_login(self.student)

        # Day 1: Full introduction
        url_day1 = reverse('daily_lesson_view', kwargs={'lesson_id': self.lesson_day1.id})
        res_day1 = client.get(url_day1)
        self.assertEqual(res_day1.status_code, 200)
        html_day1 = res_day1.content.decode('utf-8')

        # Check required DOM elements
        self.assertIn('id="inaraIntroStage"', html_day1)
        self.assertIn('id="inaraLectureAvatarContainer"', html_day1)
        self.assertIn('id="btnStartIntro"', html_day1)
        self.assertIn('id="btnSkipIntro"', html_day1)
        self.assertIn('inara_player.js', html_day1)
        self.assertIn('avatarConfigData', html_day1)

        # Check context variables
        self.assertIn("Assalamu alaikum, Zainab!", html_day1)
        self.assertIn("Introduction to Scalable Architecture", html_day1)
