# Plan: Django templates → React frontend + Django REST backend

**Status (2026-11-14): Phases 0–5 complete. All 32 template pages ported to React with API endpoints and tests. Phase 6 cut-over: `ALVIX_FRONTEND=react` is the default; legacy templates are kept for rollback and comparison.**

## Goal
Replace the 32 server-rendered Django templates with a React SPA **without changing any page's look, theme, copy or behaviour**. Keep Django as the backend (models, services, AI, admin, PDFs) and expose it as a JSON API.

## Guiding principles
1. **Pixel parity first, improvements later.** Every port copies the template's markup, class names, ids and `<style>` blocks unchanged, and loads the same Bootstrap / Icons / font CDN versions. A page is "done" only after a side-by-side comparison and a `ui-parity-reviewer` PASS.
2. **Strangler pattern.** Old Django pages keep working until the React page replaces them, so the app is never broken mid-migration.
3. **Same URLs.** React Router paths equal today's Django paths (`/dashboard/`, `/mycourse/`, `/daily-lesson/:id/` …), so bookmarks and the certificate QR verification links keep working.
4. **Business logic stays in Python.** Views become thin API views calling the existing services.
5. **Fix crash and security bugs in the backend first** (known-issues B1–B7). These are bugs, not UI changes.

## Target folder structure
```
Fyp-project/
├── backend/                       (moved from root; git mv keeps history)
│   ├── manage.py
│   ├── alvix/                     settings split: settings/base.py, dev.py, prod.py
│   ├── alvixapp/
│   │   ├── api/                   NEW: serializers.py, permissions.py, urls.py, student.py, admin.py, courses.py, lessons.py
│   │   ├── services/              existing *_service.py / ai_*.py moved here (imports updated)
│   │   ├── templates/             kept until cut-over, then only PDF/email templates remain
│   │   ├── tests/                 tests.py split per area + API tests, Gemini mocked
│   │   └── models.py, admin.py, forms.py, migrations/, management/
│   ├── static/  public/
│   └── requirements.txt           NEW (pinned)
├── frontend/                      NEW: Vite + React 19 (JavaScript)
│   ├── index.html                 Bootstrap 5.3.x + Icons CDN links as in templates
│   ├── vite.config.js             dev proxy /api /media /static /public → :8000
│   └── src/
│       ├── main.jsx  App.jsx  routes.jsx
│       ├── api/client.js          fetch wrapper: credentials, X-CSRFToken, JSON errors
│       ├── hooks/                 useApi, useAuth, usePageStyles (mount/unmount page CSS)
│       ├── layouts/               PublicLayout, StudentLayout, AdminLayout (from the 2 base templates)
│       ├── components/            FlashMessages, Sidebar(s), CourseCard, TierBadge, …
│       ├── pages/public/          Home, Login, Signup, SuggestedCourses, CertificateVerify, Logout
│       ├── pages/student/         Dashboard, Assessment, Profile, MyCourse, CourseContent, GenerateCourse,
│       │                          DailyLesson, Assignment, Quiz, Performance, Reports, Notifications,
│       │                          Settings, Certificate, CertificateLocked
│       ├── pages/admin/           AdminDashboard, UserManagement, CoursesInfo, AddCourse, CourseDetails,
│       │                          LevelCourseView, LevelUsersTelemetry, AdminReports, AdminNotifications,
│       │                          Analytics, AvatarSettings
│       ├── player/inara_player.js existing file, unchanged, wrapped by usePlayer hook
│       └── utils/                 djangoDate.js (same output as |date filters), formatters
├── .claude/  CLAUDE.md  README.md  .gitignore  .env.example
```
Production: `npm run build` → Django serves `frontend/dist` (WhiteNoise) with a catch-all route that returns `index.html` for SPA paths. One origin, so no CORS.

## Phases
| Phase | Work | Exit criteria |
|---|---|---|
| 0 | Restructure into `backend/` and `frontend/`; `requirements.txt`; `.env.example`; settings split; hermetic tests (mock Gemini) | `manage.py check` + tests green; app unchanged in the browser |
| 1 | Fix backend bugs B1–B7; add DRF, `api/` package, auth endpoints (`/api/v1/auth/login, logout, signup, verify-otp, me, csrf`) | API tests green |
| 2 | Scaffold Vite React app, layouts, API client, flash messages, routing, per-page CSS loader | `npm run build` green; Student/Admin shell identical to the templates |
| 3 | Port public pages (6) | parity PASS each |
| 4 | Port student pages (15), including the Daily Lesson player wrapping `inara_player.js` | parity PASS each; watch-time, assignment, quiz flows work end-to-end |
| 5 | Port admin pages (11) | parity PASS each |
| 6 | Cut-over: Django serves the SPA; remove ported templates (keep certificate PDF and email templates); update README | full click-through of every page and flow |
| 7 (optional, separate approval) | Enhancements: fix UI defects F1–F9, unify duplicated CSS into tokens, TypeScript, tests (Vitest + Playwright visual snapshots) | owner sign-off per change |

## Page checklist
Public: [x] mainpage [x] login [x] signup (+OTP) [x] verify_otp [x] suggested_courses [x] logout [x] certificate_verify
Student: [x] dashboard [x] assessment [x] profile [x] mycourse [x] course_content [x] generate_course [x] daily_lesson [x] assignment [x] quiz [x] performance [x] reports [x] notifications [x] settings [x] certificate [x] certificate_locked
Admin: [x] admindashboard [x] user_management [x] courses_info [x] add_course [x] course_details [x] level_course_view [x] level_users_telemetry [x] admin_reports [x] admin_notifications [x] analytics [x] admin_settings

## Risks and mitigations
- **CSS leakage between routes.** Each template overrides `body{}` globally. Mitigation: `usePageStyles` injects the page CSS on mount and removes it on unmount.
- **Bootstrap JS widgets** (modals, tabs, collapses). Load the same bundle globally and initialise in `useEffect`. Keep the existing markup.
- **Speech/audio player.** Reuse `inara_player.js` unchanged; strict-mode double-mount is handled with cleanup.
- **Django-filter formatting** (`|date`, `|timesince`, `|floatformat`, `widthratio`). Shared util functions, unit-tested against the Django output.
- **Ported pages are first replicated, then improved.** Existing visual bugs stay in a faithful port unless the owner approves a fix (Phase 7).
