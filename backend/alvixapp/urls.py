"""
ALVIX page/file URLs.

Every page keeps its original path and URL name. Which implementation answers a
page URL depends on settings.ALVIX_FRONTEND:

  'react'      -> the React SPA (frontend/dist/index.html); data comes from /api/v1/
  'templates'  -> the original Django template views (legacy, kept for comparison/rollback)

File downloads and the two legacy AJAX endpoints are always served by Django.
"""

from django.conf import settings
from django.urls import path

from . import views
from .spa import spa_index

# (route, template_view, name)
PAGE_ROUTES = [
    # Main page & Auth
    ('', views.mainpage, 'mainpage'),
    ('suggested_courses/', views.suggested_courses, 'suggested_courses'),
    ('signup/', views.signup_view, 'signup'),
    ('verify-otp/', views.verify_otp_view, 'verify_otp'),
    ('login/', views.login_view, 'login'),
    ('logout/', views.logout, 'logout'),

    # Student Dashboard
    ('dashboard/', views.dashboard, 'dashboard'),
    ('profile/', views.profile, 'profile'),
    ('assessment/', views.student_assessment, 'student_assessment'),
    ('mycourse/', views.mycourse, 'mycourse'),
    ('reports/', views.reports, 'reports'),
    ('notifications/', views.notifications, 'notifications'),
    ('performance/', views.Performance_view, 'performance'),
    ('settings/', views.settings_view, 'settings'),
    ('certificate/', views.certificate, 'certificate'),
    ('certificate/<int:course_id>/', views.certificate, 'certificate'),

    # Learning
    ('generate_course/', views.generate_course, 'generate_course'),
    ('course/<int:course_id>/', views.course_detail, 'course_detail'),
    ('course_content/', views.course_content_view, 'course_content'),
    ('course-content/', views.course_content_view, 'course_content_view'),
    ('daily_lesson/', views.daily_lesson_view, 'daily_lesson'),
    ('daily-lesson/<int:lesson_id>/', views.single_lesson_view, 'daily_lesson'),
    ('daily-lesson/<int:lesson_id>/', views.single_lesson_view, 'daily_lesson_view'),
    ('submit-lesson/<int:lesson_id>/', views.submit_lesson_step, 'submit_lesson_step'),
    ('enroll-level/<slug:slug>/', views.enroll_level_view, 'enroll_level'),
    ('assignment/', views.assignment_view, 'assignment'),
    ('assignment/', views.assignment_view, 'assignment_view'),
    ('quiz/', views.quiz_view, 'quiz'),
    ('quiz/', views.quiz_view, 'quiz_view'),
    ('quiz/<int:lesson_id>/', views.quiz_view, 'quiz_detail'),
    ('verify-certificate/<str:cert_id>/', views.verify_certificate, 'verify_certificate'),

    # Admin
    ('admindashboard/', views.admin_dashboard, 'admin_dashboard'),
    ('user_management/', views.user_management, 'user_management'),
    ('edit_user/<int:user_id>/', views.edit_user, 'edit_user'),
    ('delete_user/<int:user_id>/', views.delete_user, 'delete_user'),
    ('courses_info/', views.courses_info, 'courses_info'),
    ('course_details/<slug:slug>/', views.admin_course_detail, 'admin_course_detail'),
    ('course_details/<slug:slug>/', views.admin_course_detail, 'course_details'),
    ('toggle_system_mode/', views.toggle_system_mode, 'toggle_system_mode'),
    ('analytics/', views.analytics, 'analytics'),
    ('admin_notifications/', views.admin_notifications, 'admin_notifications'),
    ('add_course/', views.add_course, 'add_course'),
    ('admindashboard/avatar-settings/', views.admin_avatar_settings_view, 'admin_avatar_settings'),
    ('admindashboard/level/<slug:slug>/course/', views.admin_course_level_detail, 'admin_course_level_detail'),
    ('admindashboard/level/<slug:slug>/regenerate/', views.admin_regenerate_deep_curriculum, 'admin_regenerate_deep_curriculum'),
    ('admindashboard/level/<slug:slug>/users/', views.admin_course_level_users, 'admin_course_level_users'),
    ('admin_reports/', views.admin_reports, 'admin_reports'),
    ('admin-reports/respond/<int:report_id>/', views.send_report_response, 'send_report_response'),
    ('admin-reports/delete/<int:report_id>/', views.delete_report, 'delete_report'),
]

# Always served by Django (binary downloads / uploads / legacy JSON endpoints)
FILE_ROUTES = [
    path('lesson/<int:lesson_id>/download-ppt/', views.download_lesson_ppt, name='download_lesson_ppt'),
    path('lesson/<int:lesson_id>/upload-ppt/', views.admin_upload_lesson_ppt, name='admin_upload_lesson_ppt'),
    path('download-assignment-pdf/<int:submission_id>/', views.download_assignment_pdf, name='download_assignment_pdf'),
    path('certificate/<int:course_id>/download-pdf/', views.download_certificate_pdf, name='download_certificate_pdf'),
    path('lesson/<int:lesson_id>/watch-time/', views.record_lesson_watch_time, name='record_lesson_watch_time'),
    path('notifications/read/<int:id>/', views.mark_notification_read, name='mark_notification_read'),
]

USE_REACT = getattr(settings, 'ALVIX_FRONTEND', 'templates') == 'react'

urlpatterns = list(FILE_ROUTES) + [
    path(route, spa_index if USE_REACT else view, name=name)
    for route, view, name in PAGE_ROUTES
]
