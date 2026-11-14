# ALVIX URL → view → template map

Routes: `alvixapp/urls.py` (included at `/` from `alvix/urls.py`). Plus `/admin/` (Django admin), `/media/…` and `/static/…` (DEBUG), `/public/…` (avatar frames, always served).

Auth legend: **P** public · **L** `@login_required` · **A** login + `admin_required` (`is_alvix_admin`: staff/superuser).

## Public / auth
| Path | Name | View | Auth | Template / response |
|---|---|---|---|---|
| `/` | `mainpage` | `mainpage` | P | `main_front/mainpage.html` |
| `/signup/` | `signup` | `signup_view` | P | `main_front/signup.html` (2 steps: form → OTP) |
| `/verify-otp/` | `verify_otp` | `verify_otp_view` | P | `main_front/verify_otp.html` |
| `/login/` | `login` | `login_view` | P | `main_front/login.html`; staff → admin dashboard, no assessment → assessment, else dashboard |
| `/logout/` | `logout` | `logout` | P | GET: `student_dashboard/logout.html` confirm; POST: logs out |
| `/suggested_courses/` | `suggested_courses` | `suggested_courses` | L | `main_front/suggested_courses.html`; POST `action` = `start_suggested` / `pick_other_course` / `generate_new_course` |
| `/verify-certificate/<cert_id>/` | `verify_certificate` | `verify_certificate` | P | `student_dashboard/certificate_verify.html` |

## Student
| Path | Name | View | Auth | Template / response |
|---|---|---|---|---|
| `/dashboard/` | `dashboard` | `dashboard` | L | `student_dashboard/dashboard.html` |
| `/assessment/` | `student_assessment` | `student_assessment` | L | `student_dashboard/assessment.html` (`?retake=true`) |
| `/profile/` | `profile` | `profile` | L | `student_dashboard/profile.html`; POST multipart (picture) |
| `/mycourse/` | `mycourse` | `mycourse` | L | `student_dashboard/mycourse.html` (`?course_id=&tab=content|lessons|assignment|quiz|overview`) |
| `/course/<id>/` | `course_detail` | `course_detail` | L | `student_dashboard/mycourse.html` |
| `/course_content/`, `/course-content/` | `course_content`, `course_content_view` | `course_content_view` | L | `course_data/course_content.html` (`?course_id=`) |
| `/generate_course/` | `generate_course` | `generate_course` | L | `course_data/generate_course.html` |
| `/daily_lesson/` | `daily_lesson` | `daily_lesson_view` | L | redirect to current lesson |
| `/daily-lesson/<lesson_id>/` | `daily_lesson`*, `daily_lesson_view` | `single_lesson_view` | L | `course_data/daily_lesson.html` (slides + Inara avatar + speech) |
| `/lesson/<id>/watch-time/` | `record_lesson_watch_time` | same | L (CSRF) | **JSON** POST `{seconds}` → `{watch_time_seconds, required_watch_seconds, percentage, is_completed}` |
| `/lesson/<id>/download-ppt/` | `download_lesson_ppt` | same | L | PPTX file |
| `/submit-lesson/<id>/` | `submit_lesson_step` | same | L | legacy combined submit |
| `/assignment/` | `assignment`, `assignment_view` | `assignment_view` | L | `course_data/assignment.html` (`?lesson_id=`); POST multipart + telemetry |
| `/download-assignment-pdf/<id>/` | `download_assignment_pdf` | same | L | PDF |
| `/quiz/`, `/quiz/<lesson_id>/` | `quiz`, `quiz_view`, `quiz_detail` | `quiz_view` | L | `course_data/quiz.html`; POST `q_<id>` answers |
| `/certificate/`, `/certificate/<course_id>/` | `certificate` | `certificate` | L | `course_data/certificate.html` or `certificate_locked.html` (`?preview=1`) |
| `/certificate/<course_id>/download-pdf/` | `download_certificate_pdf` | same | L | PDF |
| `/performance/` | `performance` | `Performance_view` | L | `student_dashboard/performance.html` |
| `/reports/` | `reports` | `reports` | L | `student_dashboard/reports.html` (ReportForm) |
| `/notifications/` | `notifications` | `notifications` | L | `student_dashboard/notifications.html` |
| `/notifications/read/<id>/` | `mark_notification_read` | same | L | **JSON** |
| `/settings/` | `settings` | `settings_view` | L | `student_dashboard/settings.html` (UserSettingsForm) |
| `/enroll-level/<slug>/` | `enroll_level` | `enroll_level_view` | L | redirect |

\* `daily_lesson` name is defined twice; Django's `reverse('daily_lesson')` resolves to the **last** definition with that name.

## Admin
| Path | Name | View | Template |
|---|---|---|---|
| `/admindashboard/` | `admin_dashboard` | `admin_dashboard` | `admin_db/admindashboard.html` |
| `/user_management/` | `user_management` | `user_management` | `admin_db/user_management.html` (POST `action`) |
| `/edit_user/<id>/`, `/delete_user/<id>/` | `edit_user`, `delete_user` | same | redirect / user_management |
| `/courses_info/` | `courses_info` | `courses_info` | `admin_db/courses_info.html` |
| `/course_details/<slug>/` | `admin_course_detail`, `course_details` | `admin_course_detail` | `admin_db/course_details.html` |
| `/add_course/` | `add_course` | `add_course` | `admin_db/add_course.html` (multipart image) |
| `/admindashboard/level/<slug>/course/` | `admin_course_level_detail` | same | `admin_db/level_course_view.html` (`?regenerate=1`) |
| `/admindashboard/level/<slug>/regenerate/` | `admin_regenerate_deep_curriculum` | same | redirect |
| `/admindashboard/level/<slug>/users/` | `admin_course_level_users` | same | `admin_db/level_users_telemetry.html` |
| `/admindashboard/avatar-settings/` | `admin_avatar_settings` | `admin_avatar_settings_view` | `admin_db/admin_settings.html` |
| `/analytics/` | `analytics` | `analytics` | `admin_db/analytics.html` |
| `/admin_notifications/` | `admin_notifications` | same | `admin_db/admin_notifications.html` |
| `/admin_reports/` | `admin_reports` | same | `admin_db/admin_reports.html` |
| `/admin-reports/respond/<id>/`, `/admin-reports/delete/<id>/` | `send_report_response`, `delete_report` | same | redirect |
| `/lesson/<id>/upload-ppt/` | `admin_upload_lesson_ppt` | same | redirect |
| `/toggle_system_mode/` | `toggle_system_mode` | same | redirect |

## How page URLs are served
`ALVIX_FRONTEND=react`: every path above returns the React app (`frontend/dist/index.html`), which loads its data from the API below. `ALVIX_FRONTEND=templates`: the legacy template views answer. Downloads, PPT upload (legacy form), `/lesson/<id>/watch-time/` and `/notifications/read/<id>/` are always Django.

## JSON API (`/api/v1/`, session auth + CSRF)
Permissions: auth/public endpoints `AllowAny` except suggested-courses (login). Student/learning/lessons: `IsAuthenticated` + ownership. Admin/admin-courses: `IsAuthenticated` + `IsAlvixAdmin`.

| Path | Methods | View |
|---|---|---|
| `/api/v1/auth/csrf/` | GET | `auth.CsrfView` |
| `/api/v1/auth/me/` | GET | `auth.MeView` |
| `/api/v1/auth/login/` | POST | `auth.LoginView` |
| `/api/v1/auth/logout/` | POST | `auth.LogoutView` |
| `/api/v1/public/signup/` | POST | `public.SignupView` |
| `/api/v1/public/signup/verify/` | GET/POST | `public.SignupVerifyView` |
| `/api/v1/public/suggested-courses/` | GET/POST | `public.SuggestedCoursesView` |
| `/api/v1/public/certificates/<cert_id>/verify/` | GET | `public.CertificateVerifyView` |
| `/api/v1/student/dashboard/` | GET | `student.DashboardView` |
| `/api/v1/student/assessment/` | GET/POST | `student.AssessmentView` |
| `/api/v1/student/profile/` | GET/POST (multipart) | `student.ProfileView` |
| `/api/v1/student/notifications/` | GET | `student.NotificationsView` |
| `/api/v1/student/reports/` | GET/POST | `student.ReportsView` |
| `/api/v1/student/performance/` | GET | `student.PerformanceView` |
| `/api/v1/student/settings/` | GET/POST | `student.SettingsView` |
| `/api/v1/learning/mycourse/` | GET | `learning.MyCourseView` |
| `/api/v1/learning/course/<course_id>/` | GET | `learning.CourseDetailView` |
| `/api/v1/learning/course-content/` | GET | `learning.CourseContentView` |
| `/api/v1/learning/generate-course/` | GET/POST | `learning.GenerateCourseView` |
| `/api/v1/learning/enroll-level/<slug>/` | POST | `learning.EnrollLevelView` |
| `/api/v1/learning/current-lesson/` | GET | `learning.CurrentLessonView` |
| `/api/v1/learning/certificate/` | GET | `learning.CertificateView` |
| `/api/v1/lessons/<lesson_id>/` | GET | `lessons.LessonPlayerView` |
| `/api/v1/lessons/assignment/` | GET/POST (multipart) | `lessons.AssignmentView` |
| `/api/v1/lessons/quiz/` | GET/POST | `lessons.QuizView` |
| `/api/v1/admin/dashboard/` | GET | `admin.DashboardView` |
| `/api/v1/admin/users/` | GET/POST | `admin.UsersView` |
| `/api/v1/admin/reports/` | GET | `admin.ReportsView` |
| `/api/v1/admin/reports/<id>/respond/` | POST | `admin.ReportRespondView` |
| `/api/v1/admin/reports/<id>/delete/` | POST | `admin.ReportDeleteView` |
| `/api/v1/admin/notifications/` | GET/POST | `admin.NotificationsView` |
| `/api/v1/admin/analytics/` | GET | `admin.AnalyticsView` |
| `/api/v1/admin/avatar-settings/` | GET/POST | `admin.AvatarSettingsView` |
| `/api/v1/admin-courses/levels/` | GET | `admin_courses.LevelsListView` |
| `/api/v1/admin-courses/levels/<slug>/` | GET | `admin_courses.LevelDetailView` |
| `/api/v1/admin-courses/levels/<slug>/regenerate/` | POST | `admin_courses.LevelRegenerateView` |
| `/api/v1/admin-courses/levels/<slug>/users/` | GET | `admin_courses.LevelUsersView` |
| `/api/v1/admin-courses/courses/` | POST (multipart) | `admin_courses.CourseCreateView` |
| `/api/v1/admin-courses/courses/<slug>/` | GET | `admin_courses.CourseDetailView` |
| `/api/v1/admin-courses/lessons/<lesson_id>/upload-ppt/` | POST (multipart) | `admin_courses.LessonPptUploadView` |

Action responses: `{ok: true, messages: [{tags, message}], redirect?}`; errors: HTTP 400 `{ok: false, error | errors}`.
