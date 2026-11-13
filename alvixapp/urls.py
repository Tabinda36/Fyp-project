from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from alvixapp import views

urlpatterns = [
    # Main page & Auth
    path('', views.mainpage, name='mainpage'), 
    path('suggested_courses/', views.suggested_courses, name='suggested_courses'),
    path('signup/', views.signup_view, name='signup'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout, name='logout'),

    # Student Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('assessment/', views.student_assessment, name='student_assessment'),
    path('mycourse/', views.mycourse, name='mycourse'),
    path('reports/', views.reports, name='reports'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/read/<int:id>/', views.mark_notification_read, name='mark_notification_read'),
    path('performance/', views.Performance_view, name='performance'),
    path('settings/', views.settings_view, name='settings'),
    path('certificate/', views.certificate, name='certificate'),
    path('certificate/<int:course_id>/', views.certificate, name='certificate'),
    
    # AI INTEGRATION
    path('generate_course/', views.generate_course, name='generate_course'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('course_details/<slug:slug>/', views.admin_course_detail, name='admin_course_detail'),
    path('course_content/', views.course_content_view, name='course_content'),
    path('course-content/', views.course_content_view, name='course_content_view'),
    path('daily_lesson/', views.daily_lesson_view, name='daily_lesson'),
    path('daily-lesson/<int:lesson_id>/', views.single_lesson_view, name='daily_lesson'),
    path('daily-lesson/<int:lesson_id>/', views.single_lesson_view, name='daily_lesson_view'),
    path('lesson/<int:lesson_id>/download-ppt/', views.download_lesson_ppt, name='download_lesson_ppt'),
    path('lesson/<int:lesson_id>/upload-ppt/', views.admin_upload_lesson_ppt, name='admin_upload_lesson_ppt'),
    path('submit-lesson/<int:lesson_id>/', views.submit_lesson_step, name='submit_lesson_step'),

    # Admin Dashboard & User Management
    path('admindashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('user_management/', views.user_management, name='user_management'),
    path('edit_user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('delete_user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('courses_info/', views.courses_info, name='courses_info'),
    path('course_details/<slug:slug>/', views.admin_course_detail, name='course_details'),
    path('toggle_system_mode/', views.toggle_system_mode, name='toggle_system_mode'),
    path('analytics/', views.analytics, name='analytics'),
    path('admin_notifications/', views.admin_notifications, name='admin_notifications'),
    path('add_course/', views.add_course, name='add_course'),
    path('admindashboard/avatar-settings/', views.admin_avatar_settings_view, name='admin_avatar_settings'),
    
    # Course Levels (University Benchmarks & Telemetry)
    path('admindashboard/level/<slug:slug>/course/', views.admin_course_level_detail, name='admin_course_level_detail'),
    path('admindashboard/level/<slug:slug>/regenerate/', views.admin_regenerate_deep_curriculum, name='admin_regenerate_deep_curriculum'),
    path('admindashboard/level/<slug:slug>/users/', views.admin_course_level_users, name='admin_course_level_users'),
    path('enroll-level/<slug:slug>/', views.enroll_level_view, name='enroll_level'),
    
    # REPORT
    path('admin_reports/', views.admin_reports, name='admin_reports'),
    path('admin-reports/respond/<int:report_id>/', views.send_report_response, name='send_report_response'),
    path('admin-reports/delete/<int:report_id>/', views.delete_report, name='delete_report'),

    # ASSIGNMENT AND QUIZ URLS
    path('assignment/', views.assignment_view, name='assignment'),
    path('assignment/', views.assignment_view, name='assignment_view'),
    path('download-assignment-pdf/<int:submission_id>/', views.download_assignment_pdf, name='download_assignment_pdf'),
    path('quiz/', views.quiz_view, name='quiz'),
    path('quiz/', views.quiz_view, name='quiz_view'),
    path('quiz/<int:lesson_id>/', views.quiz_view, name='quiz_detail'),

    # PERFORMANCE & CERTIFICATION
    path('lesson/<int:lesson_id>/watch-time/', views.record_lesson_watch_time, name='record_lesson_watch_time'),
    path('certificate/<int:course_id>/download-pdf/', views.download_certificate_pdf, name='download_certificate_pdf'),
    path('verify-certificate/<str:cert_id>/', views.verify_certificate, name='verify_certificate'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)