from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Profile,
    Report,
    Course,
    Performance,
    Notification,
    CourseModule,
    StudentAssessment,
    AssignmentSubmission,
    QuizSubmission,
    DailyLesson,
    Certificate,
    GeneratedCourse,
    AdminCourse,
    CourseLevel,
    AvatarSettings,
)

# 1. Basic Model Registrations
admin.site.register(Profile)
admin.site.register(Performance)
admin.site.register(GeneratedCourse)
admin.site.register(AdminCourse)
admin.site.register(CourseLevel)

# 2. Course Admin
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'title')
    search_fields = ('title',)

# 3. Report Admin
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "course_name",
        "problem_type",
        "status",
        "created_at",
    )
    list_filter = (
        "status",
        "problem_type",
    )
    search_fields = (
        "student__username",
        "course_name",
        "problem_title",
    )

# 4. Notification Admin
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('subject_heading', 'target_recipient', 'category_type', 'created_at', 'is_dispatched')
    list_filter = ('target_recipient', 'category_type', 'is_dispatched', 'created_at')
    search_fields = ('subject_heading', 'notification_body')

# 5. Student Assessment Admin
@admin.register(StudentAssessment)
class StudentAssessmentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'education_level', 'interest', 'created_at')

# 6. Course Module Admin
@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'course')

# 7. Assignment Submission Admin (Integrity Telemetry & Copy Risk Review)
@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'lesson',
        'marks',
        'total_marks',
        'copy_risk_badge',
        'peer_similarity_score',
        'paste_count',
        'pasted_chars_total',
        'typing_duration_seconds',
        'admin_reviewed',
        'submitted_at',
    )
    list_filter = ('copy_risk_level', 'admin_reviewed', 'submitted_at')
    search_fields = ('user__username', 'user__email', 'lesson__title', 'copy_risk_details')
    readonly_fields = ('copy_risk_details', 'peer_similarity_score', 'ai_generated_probability')

    def copy_risk_badge(self, obj):
        level = obj.copy_risk_level or 'Low'
        if level == 'High':
            color = '#dc2626'
            icon = '🚩'
        elif level == 'Medium':
            color = '#d97706'
            icon = '⚠️'
        else:
            color = '#16a34a'
            icon = '✅'
        return format_html(
            '<span style="background-color: {}; color: #fff; padding: 3px 8px; border-radius: 12px; font-weight: bold; font-size: 11px;">{} {}</span>',
            color, icon, level
        )
    copy_risk_badge.short_description = 'Copy Risk'

# 8. Certificate Admin
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = (
        'certificate_id',
        'student_name',
        'student_email',
        'course_name',
        'level',
        'overall_percentage',
        'performance_grade',
        'duration_days',
        'is_unlocked',
        'is_valid',
        'updated_at',
    )
    list_filter = ('is_unlocked', 'is_valid', 'performance_grade', 'level', 'updated_at')
    search_fields = ('certificate_id', 'student_name', 'student_email', 'course_name')
    readonly_fields = ('qr_code_data_uri', 'verification_url')

# 9. Daily Lesson Admin (Telemetry & Issue Dates)
@admin.register(DailyLesson)
class DailyLessonAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'generated_course',
        'day_number',
        'title',
        'assignment_issued_at',
        'quiz_issued_at',
        'watch_time_seconds',
        'watch_time_completed',
        'is_completed',
    )
    list_filter = ('watch_time_completed', 'is_completed', 'day_number')
    search_fields = ('title', 'generated_course__user__username')

# 10. Quiz Submission Admin
@admin.register(QuizSubmission)
class QuizSubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'lesson', 'score', 'total_questions', 'percentage', 'submitted_at')
    list_filter = ('submitted_at',)
    search_fields = ('user__username', 'lesson__title')


# 11. Avatar & AI Teacher Settings Admin
@admin.register(AvatarSettings)
class AvatarSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'avatar_name',
        'developer_name',
        'university_or_department',
        'avatar_name_pronunciation',
        'play_full_intro_every_day',
        'updated_at',
    )
