import random
from datetime import timedelta
from time import timezone

import django.utils.timezone
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


def generate_unique_student_id():
    """Generates a unique student ID formatted as ALVIX-YYYY-XXXX."""
    current_year = django.utils.timezone.now().year
    while True:
        rand_digits = random.randint(1000, 9999)
        new_id = f"ALVIX-{current_year}-{rand_digits}"
        if not Profile.objects.filter(student_id=new_id).exists():
            return new_id


# ==========================================
# 1. PROFILE & SETTINGS MODELS
# ==========================================
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    student_id = models.CharField(max_length=30, unique=True, blank=True, null=True, verbose_name="Student ID")
    full_name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    goal = models.TextField(blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    interest_area = models.CharField(max_length=50, blank=True, null=True, verbose_name="Interest Area")
    expectations = models.TextField(blank=True, null=True, verbose_name="Learning Expectations")
    assessment_completed = models.BooleanField(default=False, verbose_name="Assessment Completed")

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = generate_unique_student_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name or self.user.username} ({self.student_id or 'No ID'})"


class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    theme = models.CharField(
        max_length=10,
        choices=[('Dark', 'Dark'), ('Light', 'Light')],
        default='Dark',
    )
    email_notifications = models.BooleanField(default=True)
    ai_notifications = models.BooleanField(default=True)
    assignment_reminders = models.BooleanField(default=True)
    quiz_reminders = models.BooleanField(default=True)
    sound_effects = models.BooleanField(default=True)
    autoplay_videos = models.BooleanField(default=False)
    public_profile = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s Settings"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        profile, p_created = Profile.objects.get_or_create(
            user=instance,
            defaults={
                'full_name': instance.get_full_name() or instance.username,
                'student_id': generate_unique_student_id(),
            }
        )
        if not profile.student_id:
            profile.student_id = generate_unique_student_id()
            profile.save()
        UserSettings.objects.get_or_create(user=instance)


# ==========================================
# 2. PUBLIC COURSE & MODULE MODELS
# ==========================================
class Course(models.Model):
    name = models.CharField(max_length=200, blank=True, null=True)
    title = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='course_images/', blank=True, null=True)
    duration = models.CharField(max_length=50, blank=True, null=True)
    level = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return self.title


class CourseModule(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules', null=True, blank=True)
    course_level = models.ForeignKey('CourseLevel', on_delete=models.CASCADE, related_name='academic_modules', null=True, blank=True)
    admin_course = models.ForeignKey('AdminCourse', on_delete=models.CASCADE, related_name='academic_modules', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    learning_objectives = models.JSONField(default=list, blank=True)
    pedagogical_focus = models.CharField(max_length=255, blank=True, default='')
    content = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=1)
    estimated_hours = models.PositiveIntegerField(default=6)

    class Meta:
        ordering = ['order']

    def __str__(self):
        parent_name = self.course_level.title if self.course_level else (self.course.title if self.course else 'Module')
        return f"{parent_name} - Module {self.order}: {self.title}"


# ==========================================
# 3. STUDENT ASSESSMENT MODEL
# ==========================================
from django.db import models
import django.utils

class StudentAssessment(models.Model):
    EDUCATION_LEVELS = [
        ('', 'Select Education Level'),
        ('Matric', 'Matric'),
        ('Intermediate', 'Intermediate'),
        ('BS', 'BS'),
        ('MS', 'MS'),
        ('Postgraduate', 'Postgraduate'),
    ]

    KNOWLEDGE_LEVELS = [
        ('', 'Select Knowledge Level'),
        ('No Knowledge', 'No Knowledge'),
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ]

    LEARNING_GOALS = [
        ('', 'Select Learning Goal'),
        ('University Study', 'University Study'),
        ('Get a Job', 'Get a Job'),
        ('Freelancing', 'Freelancing'),
        ('Build Projects', 'Build Projects'),
        ('Skill Improvement', 'Skill Improvement'),
        ('Skill Enhancement / Professional Growth', 'Skill Enhancement / Professional Growth'),
    ]

    LEARNING_STYLES = [
        ('', 'Select Learning Style'),
        ('Videos', 'Videos'),
        ('Reading', 'Reading'),
        ('Practical', 'Practical'),
        ('Mixed', 'Mixed'),
        ('Visual', 'Visual'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assessments')
    student_id = models.CharField(max_length=30, blank=True, null=True)
    full_name = models.CharField(max_length=100, default="Unknown")
    email = models.EmailField(max_length=255, blank=True, null=True)
    age = models.PositiveIntegerField(default=18)
    education_level = models.CharField(max_length=50, choices=EDUCATION_LEVELS, default='')
    knowledge_level = models.CharField(max_length=20, choices=KNOWLEDGE_LEVELS, default='')
    interest = models.ForeignKey('AdminCourse', on_delete=models.SET_NULL, null=True, blank=True)
    interest_topic = models.CharField(max_length=255, blank=True, null=True)
    learning_goal = models.CharField(max_length=100, choices=LEARNING_GOALS, default='')
    learning_style = models.CharField(max_length=20, choices=LEARNING_STYLES, default='')
    selected_course = models.CharField(max_length=100, blank=True, null=True)
    expectations = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=django.utils.timezone.now)

    def __str__(self):
        return f"{self.full_name} ({self.student_id or self.email or 'Student'})"


# ==========================================
# 4. REPORT & NOTIFICATION MODELS
# ==========================================
class Report(models.Model):
    PROBLEM_TYPES = [
        ('technical', 'Technical Issue'),
        ('course_content', 'Course Content Error'),
        ('quiz_issue', 'Quiz / Assignment Bug'),
        ('other', 'Other Issue'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    course_name = models.CharField(max_length=255)
    problem_type = models.CharField(max_length=50, choices=PROBLEM_TYPES)
    problem_title = models.CharField(max_length=255)
    problem_description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.problem_title} - {self.student.username} ({self.created_at.strftime('%d %b %Y')})"


class Notification(models.Model):
    RECIPIENT_CHOICES = [
        ('all_students', 'All Students'),
        ('enrolled_students', 'Enrolled Students Only'),
        ('specific_student', 'Specific Student'),
    ]

    CATEGORY_CHOICES = [
        ('announcement', 'General Announcement'),
        ('course_user', 'Course Update'),
        ('alert', 'Urgent Alert'),
        ('reminder', 'Assignment / Quiz Reminder'),
    ]

    target_recipient = models.CharField(max_length=50, choices=RECIPIENT_CHOICES, default='all_students')
    category_type = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='announcement')
    subject_heading = models.CharField(max_length=255, default='')
    notification_body = models.TextField(default='')
    recipient_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_notifications')
    created_at = models.DateTimeField(auto_now_add=True)
    is_dispatched = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject_heading} - {self.created_at.strftime('%d %b %Y, %I:%M %p')}"


class StudentNotificationStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_statuses')
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='student_statuses')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        status_text = 'Read' if self.is_read else 'Unread'
        return f"{self.user.username} - {self.notification.subject_heading} ({status_text})"


@receiver(post_save, sender=Notification)
def create_student_notification_statuses(sender, instance, created, **kwargs):
    if created and instance.is_dispatched:
        if instance.target_recipient == 'all_students':
            all_users = User.objects.all()
            for user in all_users:
                StudentNotificationStatus.objects.create(user=user, notification=instance)
        elif instance.target_recipient == 'specific_student' and instance.recipient_user:
            StudentNotificationStatus.objects.create(user=instance.recipient_user, notification=instance)


# ==========================================
# 5. PERFORMANCE MODEL
# ==========================================
class Performance(models.Model):
    LEVELS = [
        ("Poor", "Poor"),
        ("Average", "Average"),
        ("Good", "Good"),
        ("Brilliant", "Brilliant"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='performance')
    daily_watch_time = models.PositiveIntegerField(default=0)
    lessons_completed = models.PositiveIntegerField(default=0)
    lessons_skipped = models.PositiveIntegerField(default=0)
    assignments_completed = models.PositiveIntegerField(default=0)
    quizzes_completed = models.PositiveIntegerField(default=0)
    overall_percentage = models.FloatField(default=0)
    performance_level = models.CharField(max_length=20, choices=LEVELS, default="Average")
    assignment_remark = models.TextField(blank=True)
    quiz_remark = models.TextField(blank=True)
    ai_feedback = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username


# ==========================================
# 6. ADMIN & GENERATED COURSE MODELS
# ==========================================
import uuid
from django.db import models
from django.utils.text import slugify

def generate_unique_course_code():
    """Generates a clean unique course identifier, e.g., ALV-CRS-2026-XXXX."""
    year = django.utils.timezone.now().year
    while True:
        rand_digits = random.randint(1000, 9999)
        code = f"ALV-CRS-{year}-{rand_digits}"
        if not AdminCourse.objects.filter(course_code=code).exists():
            return code


class AdminCourse(models.Model):
    # null=True aur blank=True add kar diya taake purane data mein error na aaye
    course_id = models.UUIDField(default=uuid.uuid4, editable=False, null=True, blank=True)
    course_code = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Course Code")
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='course_images/', blank=True, null=True)
    duration = models.CharField(max_length=50, default='University Study Plan')
    level = models.CharField(max_length=50, default='All Levels')
    COURSE_TYPE_CHOICES = [
        ('Theoretical', 'Theoretical (7 Days)'),
        ('Practical', 'Practical (10 Days)'),
        ('Mixed', 'Mixed - Theory + Practical (12 Days)'),
    ]
    course_type = models.CharField(max_length=50, choices=COURSE_TYPE_CHOICES, default='Mixed')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while AdminCourse.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        if not self.course_id:
            self.course_id = uuid.uuid4()
        if not self.course_code:
            self.course_code = generate_unique_course_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.course_code or 'NO-ID'}] {self.title}"


class CourseLevel(models.Model):
    LEVEL_CHOICES = [
        ('Beginner', 'Beginner Level'),
        ('Intermediate', 'Intermediate Level'),
        ('Advanced', 'Advanced Level'),
    ]

    BENCHMARK_CHOICES = {
        'Beginner': 'Harvard University / CS50 philosophy',
        'Intermediate': 'MIT / Data structures & logic',
        'Advanced': 'Stanford & CMU / Systems & AI integration',
    }

    BENCHMARK_DESCRIPTIONS = {
        'Beginner': 'Harvard University / CS50 philosophy: Foundational computational thinking, algorithmic intuition, problem-solving, and clean code hygiene.',
        'Intermediate': 'MIT / Data structures & logic: Rigorous abstract data types, asymptotic efficiency, memory models, modular architecture, and algorithms.',
        'Advanced': 'Stanford & CMU / Systems & AI integration: Distributed architecture, concurrent execution pipelines, low-level profiling, enterprise scalability, and AI workflows.',
    }

    parent_course = models.ForeignKey(AdminCourse, on_delete=models.CASCADE, related_name='course_levels')
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES)
    title = models.CharField(max_length=255)
    benchmark = models.CharField(max_length=255, default='Harvard / MIT / Stanford Standard')
    benchmark_description = models.TextField(blank=True, default='')
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    level_code = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Level Code")
    duration = models.CharField(max_length=50, default='10 Academic Lectures')
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    is_deep_generated = models.BooleanField(default=False)
    content_topics = models.JSONField(default=list, blank=True, help_text="List of main topics with 4 to 8 study bullets each")
    total_modules_count = models.PositiveIntegerField(default=0)
    total_lessons_count = models.PositiveIntegerField(default=0)
    total_slides_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['parent_course', 'id']
        unique_together = ('parent_course', 'level')

    def save(self, *args, **kwargs):
        if not self.benchmark:
            self.benchmark = self.BENCHMARK_CHOICES.get(self.level, 'Harvard / MIT / Stanford Standard')
        if not self.benchmark_description:
            self.benchmark_description = self.BENCHMARK_DESCRIPTIONS.get(self.level, '')
        if not self.title:
            self.title = f"{self.parent_course.title} - {self.level}"
        if not self.slug:
            base_slug = slugify(f"{self.parent_course.title}-{self.level}")
            slug = base_slug
            counter = 1
            while CourseLevel.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        if not self.level_code:
            prefix = 'BEG' if self.level == 'Beginner' else ('INT' if self.level == 'Intermediate' else 'ADV')
            year = django.utils.timezone.now().year
            rand_digits = random.randint(1000, 9999)
            self.level_code = f"ALV-{prefix}-{year}-{rand_digits}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.parent_course.title} - {self.level} [{self.benchmark}]"


# ==========================================
# 6B. ACADEMIC CURRICULUM HIERARCHY MODELS
# ==========================================
class AcademicLesson(models.Model):
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='lessons')
    course_level = models.ForeignKey(CourseLevel, on_delete=models.CASCADE, related_name='academic_lessons')
    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, null=True)
    summary = models.TextField(blank=True, default='')

    # Deep Technical Long-form Material
    reading_content = models.TextField(help_text="Comprehensive, long-form core reading material")
    code_examples = models.JSONField(default=list, blank=True, help_text="List of code snippets with explanations")
    use_cases = models.JSONField(default=list, blank=True, help_text="Practical production/industry use cases")

    # Rigorous Academic Assessment
    assignment_prompt = models.TextField(blank=True, default='')
    assignment_rubric = models.TextField(blank=True, default='')
    quiz_data = models.JSONField(default=list, blank=True, help_text="Diagnostic quiz questions and explanations")

    estimated_minutes = models.PositiveIntegerField(default=45)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['module', 'order']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.course_level.slug}-mod{self.module.order}-les{self.order}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"M{self.module.order}.L{self.order}: {self.title}"


class PresentationSlide(models.Model):
    lesson = models.ForeignKey(AcademicLesson, on_delete=models.CASCADE, related_name='presentation_slides', null=True, blank=True)
    daily_lesson = models.ForeignKey('DailyLesson', on_delete=models.CASCADE, related_name='slides', null=True, blank=True)
    course_level = models.ForeignKey(CourseLevel, on_delete=models.CASCADE, related_name='presentation_slides', null=True, blank=True)

    slide_number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=255)
    bullet_points = models.JSONField(default=list, help_text="Detailed academic bullet points")
    speaker_notes = models.TextField(blank=True, help_text="Deep technical explanations and instructor lecture notes")
    code_snippet = models.TextField(blank=True, help_text="Code snippet, architectural pattern, or syntax")
    diagram_or_visual = models.TextField(blank=True, help_text="ASCII diagram, mental model, or visualization spec")
    slide_category = models.CharField(max_length=50, default='Concept', blank=True)
    slide_text = models.TextField(blank=True, default='', help_text="Raw extracted text from PPT slide")
    explanation = models.TextField(blank=True, default='', help_text="AI/Teacher simple easy-to-understand explanation with real-world examples")
    audio_file = models.CharField(max_length=500, blank=True, null=True, help_text="Path or URL to generated slide audio mp3")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['slide_number']

    def __str__(self):
        return f"Slide {self.slide_number}: {self.title}"


class StudentCourse(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_enrolled_courses')
    base_course = models.ForeignKey(AdminCourse, on_delete=models.CASCADE, related_name='student_courses')
    name = models.CharField(max_length=255, blank=True)
    level = models.CharField(max_length=50, blank=True)
    pace = models.CharField(max_length=50, default='Standard')
    objective = models.TextField(blank=True, null=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    
    course_chapters = models.TextField(blank=True, null=True)
    lesson_title = models.CharField(max_length=255, blank=True, null=True)
    lesson_content = models.TextField(blank=True, null=True)
    assignment_prompt = models.TextField(blank=True, null=True)
    quiz_data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.student.username} - {self.name or self.base_course.title}"


class GeneratedCourse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_generated_courses')
    admin_course = models.ForeignKey(AdminCourse, on_delete=models.CASCADE, related_name='generated_instances')
    course_level = models.ForeignKey(CourseLevel, on_delete=models.SET_NULL, null=True, blank=True, related_name='enrolled_students')
    slug = models.SlugField(max_length=255, blank=True, null=True)
    level = models.CharField(max_length=50)
    pace = models.CharField(max_length=50)
    course_type = models.CharField(max_length=50, default='Mixed')
    content_topics = models.JSONField(default=list, blank=True, help_text="List of main topics with 4 to 8 study bullets each")
    objective = models.TextField(blank=True)
    ai_prompt = models.TextField(blank=True, null=True)
    ai_model = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admin_course.title} - {self.user.username} ({self.level})"


class DailyLesson(models.Model):
    generated_course = models.ForeignKey(GeneratedCourse, on_delete=models.CASCADE, related_name='daily_lessons', null=True, blank=True)
    course_level = models.ForeignKey(CourseLevel, on_delete=models.CASCADE, related_name='canonical_lessons', null=True, blank=True)
    module = models.ForeignKey(CourseModule, on_delete=models.SET_NULL, null=True, blank=True, related_name='daily_lessons')
    academic_lesson = models.ForeignKey(AcademicLesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='daily_lesson_instances')
    day_number = models.IntegerField(default=1)
    title = models.CharField(max_length=255)
    content = models.TextField()
    video_url = models.URLField(blank=True, null=True)
    is_unlocked = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(null=True, blank=True)
    presentation_data = models.JSONField(blank=True, null=True)
    ppt_file = models.FileField(upload_to='lesson_ppts/', blank=True, null=True, help_text="Uploaded teacher PPT presentation")
    ai_prompt = models.TextField(blank=True, null=True)
    ai_model = models.CharField(max_length=100, blank=True, null=True)

    # Student interaction & telemetry
    assignment_issued_at = models.DateTimeField(null=True, blank=True)
    quiz_issued_at = models.DateTimeField(null=True, blank=True)
    watch_time_seconds = models.PositiveIntegerField(default=0)
    required_watch_seconds = models.PositiveIntegerField(default=180)
    watch_time_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['day_number']

    def __str__(self):
        return f"Day {self.day_number}: {self.title}"


class LessonTask(models.Model):
    lesson = models.OneToOneField(DailyLesson, on_delete=models.CASCADE, related_name='task')
    assignment_question = models.TextField()
    assignment_data = models.JSONField(default=dict, blank=True, help_text="Structured assignment data: type, checklist, rubric, expected_file_type, expected_points")
    quiz_data = models.JSONField()

    def __str__(self):
        return f"Task for {self.lesson.title}"


class StudentProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_records')
    lesson = models.ForeignKey(DailyLesson, on_delete=models.CASCADE, related_name='student_progresses')
    assignment_submission = models.TextField(blank=True)
    quiz_score = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}"


class AssignmentSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(DailyLesson, on_delete=models.CASCADE, null=True, blank=True)
    question_prompt = models.TextField(blank=True, null=True)
    submitted_answer = models.TextField(blank=True, null=True)
    file_submission = models.FileField(upload_to='assignment_files/', blank=True, null=True)
    score = models.IntegerField(default=5)
    marks = models.IntegerField(default=10)
    total_marks = models.IntegerField(default=10)
    rubric_feedback = models.JSONField(default=list, blank=True)
    ai_feedback = models.TextField(blank=True, null=True)
    ai_prompt = models.TextField(blank=True, null=True)
    ai_model = models.CharField(max_length=100, blank=True, null=True)

    # Copy/Paste & Integrity Telemetry
    paste_count = models.PositiveIntegerField(default=0)
    pasted_chars_total = models.PositiveIntegerField(default=0)
    typing_duration_seconds = models.PositiveIntegerField(default=0)
    keystroke_count = models.PositiveIntegerField(default=0)
    peer_similarity_score = models.FloatField(default=0.0)
    ai_generated_probability = models.FloatField(default=0.0)
    copy_risk_level = models.CharField(max_length=20, default='Low')
    copy_risk_details = models.TextField(blank=True, default='')
    admin_reviewed = models.BooleanField(default=False)

    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title if self.lesson else 'Assignment'}"


class QuizSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey('DailyLesson', on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=5)
    percentage = models.IntegerField(default=0)
    ai_feedback = models.TextField(blank=True, null=True)
    wrong_answers_explanation = models.JSONField(default=list, blank=True, help_text="Explanation per wrong answer")
    question_summary = models.TextField(blank=True, null=True)
    ai_prompt = models.TextField(blank=True, null=True)
    ai_model = models.CharField(max_length=100, blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title} - {self.score}/{self.total_questions}"


class StudentReport(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_reports')
    course_name = models.CharField(max_length=100)
    progress = models.IntegerField(default=0)
    quiz_score = models.IntegerField(default=0)
    is_reviewed = models.BooleanField(default=False)
    admin_feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.course_name}"


# ==========================================
# 7. ENROLLMENT MODEL
# ==========================================
class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.title}"

# ==========================================
# 8. AI GENERATION & AUDIT LOG MODEL
# ==========================================
class AIGenerationLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_generation_logs')
    item_type = models.CharField(max_length=100)  # e.g., 'course_curriculum', 'quiz', 'assignment', 'evaluation'
    item_id = models.CharField(max_length=100, blank=True, null=True)
    model_used = models.CharField(max_length=100)
    prompt = models.TextField()
    response_json = models.JSONField(default=dict, blank=True)
    is_validated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.item_type} [{self.model_used}] - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


# ==========================================
# 9. CERTIFICATE MODEL & ACADEMIC REGISTRY
# ==========================================
class Certificate(models.Model):
    certificate_id = models.CharField(max_length=100, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(GeneratedCourse, on_delete=models.CASCADE, related_name='certificates')
    is_unlocked = models.BooleanField(default=False)
    is_valid = models.BooleanField(default=True)
    student_name = models.CharField(max_length=255)
    student_email = models.EmailField()
    course_name = models.CharField(max_length=255)
    level = models.CharField(max_length=50)
    start_date = models.DateField()
    current_date = models.DateField()
    duration_days = models.PositiveIntegerField(default=1)
    overall_percentage = models.FloatField(default=0.0)
    performance_grade = models.CharField(max_length=50, default='Pass')
    ai_review = models.TextField(blank=True, default='')
    qr_code_data_uri = models.TextField(blank=True, default='')
    verification_url = models.URLField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.certificate_id}] {self.student_name} - {self.course_name} ({self.overall_percentage}%)"


# ==========================================
# 10. AVATAR & AI TEACHER SETTINGS
# ==========================================
class AvatarSettings(models.Model):
    avatar_name = models.CharField(max_length=100, default="Inara", help_text="Real name displayed on screen")
    developer_name = models.CharField(max_length=150, default="Tabinda Rukhsar")
    university_or_department = models.CharField(max_length=200, blank=True, default="Department of Computer Science")
    avatar_name_pronunciation = models.CharField(
        max_length=100,
        blank=True,
        default="ee-nah-rah",
        help_text="Optional phonetic spelling used ONLY for speech synthesis, e.g. 'ee-nah-rah'"
    )
    play_full_intro_every_day = models.BooleanField(
        default=False,
        help_text="If True, plays full introduction on every day. If False, only on Day 1."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Avatar Settings"
        verbose_name_plural = "Avatar Settings"

    def __str__(self):
        return f"{self.avatar_name} ({self.developer_name})"

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(id=1, defaults={
            'avatar_name': 'Inara',
            'developer_name': 'Tabinda Rukhsar',
            'university_or_department': 'Department of Computer Science',
            'avatar_name_pronunciation': 'ee-nah-rah',
            'play_full_intro_every_day': False,
        })
        return obj

    def get_spoken_name(self):
        return self.avatar_name_pronunciation.strip() if self.avatar_name_pronunciation else self.avatar_name

    def format_full_intro_spoken(self, student_name, course_name, day_number, lesson_title):
        univ_text = f" at {self.university_or_department}" if self.university_or_department.strip() else ""
        spoken_name = self.get_spoken_name()
        return (
            f"Assalamu alaikum, {student_name}! I am {spoken_name}, your AI teacher at ALVIX, "
            f"the adaptive learning system with AI-driven content. ALVIX was developed by {self.developer_name}{univ_text} "
            f"as a final year project. In this course, {course_name}, I will guide you step by step. "
            f"Today, in Day {day_number}, we will learn {lesson_title}. Let us begin!"
        )

    def format_full_intro_display(self, student_name, course_name, day_number, lesson_title):
        univ_text = f" at {self.university_or_department}" if self.university_or_department.strip() else ""
        return (
            f"Assalamu alaikum, {student_name}! I am {self.avatar_name}, your AI teacher at ALVIX, "
            f"the adaptive learning system with AI-driven content. ALVIX was developed by {self.developer_name}{univ_text} "
            f"as a final year project. In this course, {course_name}, I will guide you step by step. "
            f"Today, in Day {day_number}, we will learn {lesson_title}. Let us begin!"
        )

    def format_short_greeting_spoken(self, student_name, lesson_title):
        return f"Welcome back, {student_name}! Today we will learn {lesson_title}."

    def format_short_greeting_display(self, student_name, lesson_title):
        return f"Welcome back, {student_name}! Today we will learn {lesson_title}."
