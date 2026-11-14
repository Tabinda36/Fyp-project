"""
/api/v1/ routes. Each area lives in its own module with its own `urlpatterns`:

  auth.py        /api/v1/auth/...
  public.py      /api/v1/public/...    landing, signup + OTP, suggested courses, certificate verify
  student.py     /api/v1/student/...   dashboard, assessment, profile, notifications, reports, settings, performance
  learning.py    /api/v1/learning/...  my course, course content, generate course, enroll level, certificate
  lessons.py     /api/v1/lessons/...   daily lesson player, assignment, quiz
  admin.py       /api/v1/admin/...     admin dashboard, users, reports, notifications, analytics, avatar settings
  admin_courses.py /api/v1/admin-courses/... course list, add course, course details, level studio, level telemetry
"""

from django.urls import include, path

from . import auth

urlpatterns = [
    path('auth/csrf/', auth.CsrfView.as_view(), name='api_csrf'),
    path('auth/me/', auth.MeView.as_view(), name='api_me'),
    path('auth/login/', auth.LoginView.as_view(), name='api_login'),
    path('auth/logout/', auth.LogoutView.as_view(), name='api_logout'),
    path('public/', include('alvixapp.api.public')),
    path('student/', include('alvixapp.api.student')),
    path('learning/', include('alvixapp.api.learning')),
    path('lessons/', include('alvixapp.api.lessons')),
    path('admin/', include('alvixapp.api.admin')),
    path('admin-courses/', include('alvixapp.api.admin_courses')),
]
