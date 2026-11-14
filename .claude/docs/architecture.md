# ALVIX architecture

ALVIX is a final-year project: an AI-powered adaptive learning platform.
- Students take an assessment and get an AI-recommended course at a university-benchmarked tier (Harvard / MIT / Stanford style). They then follow a daily plan.
- Each day has a narrated slide lecture by the AI teacher avatar "Inara", an assignment with integrity checks, and a quiz. Scores feed into a verifiable certificate.
- Admins manage courses, tiers, curriculum, users, reports and notifications.

## Stack
| Layer | Tech |
|---|---|
| Frontend | React 19 + React Router 7 + Vite 8 (`frontend/`), plain JS/JSX. Bootstrap 5.3 + Bootstrap Icons + Google Fonts from CDN, loaded **per page** exactly as each original template did |
| API | Django REST Framework 3.18, `/api/v1/`, session auth + CSRF (same origin) |
| Backend | Django 6.1 (`backend/`), Python 3.14, single app `alvixapp` |
| DB | SQLite (`backend/db.sqlite3`, git-ignored) |
| AI | Google Gemini `gemini-2.5-flash` via `google-genai`; edge-tts / gTTS narration; YouTube Data API v3 |
| Files | python-pptx (PPTX), Pillow (certificate PDF), reportlab, xhtml2pdf |
| Static | WhiteNoise for `/static/`; Django serves `/public/` (avatar frames) and, in react mode, `frontend/dist` |

## Folder structure
```
Fyp-project/
├── .claude/                       Claude Code: agents/, skills/, docs/, settings.json
├── CLAUDE.md  README.md  .env.example  .gitignore
├── .env                           secrets (git-ignored)
├── .venv/                         Python virtualenv
├── backend/
│   ├── manage.py  requirements.txt
│   ├── alvix/                     settings.py (env-driven), urls.py, test_runner.py (hermetic), wsgi/asgi
│   ├── alvixapp/
│   │   ├── models.py  admin.py  forms.py  permissions.py  spa.py  urls.py  views.py (legacy template views)
│   │   ├── api/                   auth, public, student, learning, lessons, admin, admin_courses, common, exceptions
│   │   ├── page_context/          context builders shared by API + legacy views
│   │   ├── ai_services.py ai_helpers.py assignment_grading.py course_recommendation.py
│   │   ├── course_tier_service.py deep_curriculum_service.py ppt_generator.py ppt_service.py
│   │   ├── copy_detection.py certificate_service.py certificate_pdf.py qr_generator.py pdf_utils.py
│   │   ├── management/commands/   seed_university_curriculum, update_certificates
│   │   ├── migrations/            0001 … 0012
│   │   ├── templates/             legacy pages + server-side PDF templates
│   │   └── tests.py, test_api_*.py
│   ├── static/                    images, logo, js/inara_player.js (legacy copy)
│   ├── public/assets/avatar/      Inara PNG frames
│   └── scripts/                   one-off dev scripts (not runtime)
└── frontend/
    ├── index.html  vite.config.js  eslint.config.js  package.json
    └── src/
        ├── main.jsx  App.jsx  cdn.js
        ├── api/client.js          fetch wrapper (cookies, CSRF, errors)
        ├── hooks/                 usePageAssets, usePageData, useApi, useAuth, useFlash
        ├── utils/djangoFormat.js  |date, |timesince, |truncatechars … equivalents
        ├── layouts/               StudentLayout, AdminLayout (+ verbatim base CSS)
        ├── routes/                guards + one route table per area
        ├── pages/                 public/ student/ learning/ lessons/ admin/  (Page.jsx + verbatim Page.css)
        └── player/inara_player.js lesson player + avatar engine
```

## Request flow
```
Browser ─► React SPA (same URLs as before) ─► fetch /api/v1/*  ─► DRF APIView ─► page_context builder / services ─► models
                                     │
                                     └─► plain links for downloads: /lesson/<id>/download-ppt/, /certificate/<id>/download-pdf/,
                                         /download-assignment-pdf/<id>/ ; player pings /lesson/<id>/watch-time/
```
- **Dev:** Vite (:5173) proxies backend paths to Django (:8000), so cookies and CSRF behave as same-origin.
- **Prod / single server:** `ALVIX_FRONTEND=react` makes every original page URL return `frontend/dist/index.html`. URL names stay registered, so `reverse()` still works for certificate links and redirects. Unknown paths fall through to the React 404.
- **Legacy mode:** `ALVIX_FRONTEND=templates` serves the original Django template views. Both modes share the same `page_context` logic.

## Auth & permissions
- Django session auth.
- `alvixapp/permissions.py:is_alvix_admin`: staff or superuser only (never derived from editable data like email). Grant with `manage.py grant_admin`.
- `can_access_lesson` enforces lesson ownership (admins may preview any lesson).
- React guards: `RequireAuth`, `RequireAdmin`.
