# ALVIX - AI-Powered Learning Platform

ALVIX is an adaptive learning platform for students and administrators.
- A student takes a short assessment and receives an AI-recommended course at a university-benchmarked tier (Beginner / Intermediate / Advanced).
- The course is a daily plan: a narrated slide lecture by the AI teacher avatar **Inara**, an assignment with integrity checks, and a quiz.
- Progress feeds into a verifiable certificate with a QR code.
- Administrators manage courses, tiers, curricula, users, reports and notifications.

## Features

- Student registration with email verification code, login, profile, assessment and dashboard
- AI course recommendation, and AI-assisted curriculum, lesson, slide, quiz and assignment generation (Google Gemini, with offline fallbacks)
- Daily lesson player: slides, speech narration, animated avatar, watch-time tracking
- Assignments with rubric grading and copy-risk telemetry; quizzes with per-answer explanations
- Performance scoring, certificates (PDF + public verification page)
- Admin dashboards: users, course tiers ("Level Studio"), PPT upload, reports, notifications, analytics, AI teacher settings

## Technology

| Layer | Stack |
|---|---|
| Frontend | React 19 + React Router 7, built with Vite. Same Bootstrap 5.3 / Bootstrap Icons look as the original templates |
| Backend | Django 6.1 + Django REST Framework (session auth + CSRF), Python 3.14 |
| Database | SQLite (development) |
| AI & media | Google Gemini (`google-genai`), edge-tts / gTTS, python-pptx, Pillow, reportlab |

## Project structure

```
Fyp-project/
├── backend/                 Django project
│   ├── manage.py
│   ├── requirements.txt
│   ├── alvix/               settings, root URLs, WSGI/ASGI, hermetic test runner
│   ├── alvixapp/            models, services (AI, curriculum, slides, grading, certificates)
│   │   ├── api/             JSON API: /api/v1/{auth,public,student,learning,lessons,admin,admin-courses}
│   │   ├── page_context/    context builders shared by the API and the legacy template views
│   │   ├── templates/       legacy Django templates (kept for comparison and rollback)
│   │   └── test*.py         test suites
│   ├── static/  public/     images, logo, Inara avatar frames
│   └── scripts/             one-off developer scripts
├── frontend/                React app (Vite)
│   └── src/
│       ├── api/  hooks/  utils/        API client, auth, flash messages, Django-style formatting
│       ├── layouts/                    StudentLayout, AdminLayout (ported base templates)
│       ├── pages/                      public/ student/ learning/ lessons/ admin/
│       ├── player/inara_player.js      lesson player + avatar engine
│       └── routes/                     route tables per area
├── .claude/                 Claude Code agents, skills and project docs
├── CLAUDE.md
└── .env.example
```

## Getting started (Windows / PowerShell)

### 1. Backend
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
copy .env.example .env          # then set DJANGO_SECRET_KEY (and optional API keys)
cd backend
python manage.py migrate
python manage.py createsuperuser            # admin account, or: python manage.py grant_admin <email>
python manage.py seed_university_curriculum # optional: pre-generate course tiers and lessons
python manage.py runserver                  # http://127.0.0.1:8000
```

### 2. Frontend (development)
```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api, /media, /static, /public, downloads to Django)
```
Open <http://localhost:5173>. The signup verification code is printed in the Django terminal (console email backend).

### 3. Production-style run (single server)
```powershell
cd frontend; npm run build; cd ..\backend
# .env: ALVIX_FRONTEND=react, DJANGO_DEBUG=False, DJANGO_ALLOWED_HOSTS=<your host>
python manage.py collectstatic --noinput
python manage.py runserver        # or a WSGI server; Django serves the built React app
```
Set `ALVIX_FRONTEND=templates` to switch back to the original server-rendered pages at any time.

## Tests and checks
```powershell
cd backend;  python manage.py check;  python manage.py test alvixapp
cd frontend; npm run lint;  npm run build
```
Tests never call Gemini or YouTube: the test runner blanks the API keys.

## Configuration

See `.env.example`. Important variables:
- `DJANGO_SECRET_KEY` (required)
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `ALVIX_FRONTEND`
- `GEMINI_API_KEY`
- `YOUTUBE_API_KEY`

Keep `.env` private.

## Documentation

Detailed docs are in `.claude/docs/`: architecture, data model, URL/API map, AI services, UI inventory, porting conventions, known issues and the migration plan.
