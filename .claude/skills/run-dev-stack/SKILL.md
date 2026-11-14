---
name: run-dev-stack
description: How to install, run, and test the ALVIX stack locally on Windows — Django backend in backend/ (port 8000) and the React/Vite frontend in frontend/ (port 5173). Use when asked to run, start, test, build or set up the project.
---

# Run ALVIX locally (Windows, PowerShell)

The virtualenv lives at the repo root (`.venv`), Django in `backend/`, React in `frontend/`. `.env` is at the repo root (see `.env.example`).

## Backend (Django)
```powershell
cd "D:\Data science Paper\Fyp-project\backend"
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py seed_university_curriculum   # optional
..\.venv\Scripts\python.exe manage.py createsuperuser              # staff => admin dashboard
..\.venv\Scripts\python.exe manage.py runserver                    # http://127.0.0.1:8000
```
Checks and tests:
```powershell
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe manage.py test alvixapp           # full suite (several minutes)
..\.venv\Scripts\python.exe manage.py test alvixapp.test_api_auth
```

## Frontend (React + Vite)
```powershell
cd "D:\Data science Paper\Fyp-project\frontend"
npm install
npm run dev     # http://localhost:5173 (proxies /api /admin /media /static /public + downloads to :8000)
npm run lint
npm run build   # frontend/dist, served by Django when ALVIX_FRONTEND=react
```

## Modes
- Development: run both servers and open :5173.
- Single server: `npm run build`, set `ALVIX_FRONTEND=react`, open :8000.
- Legacy UI for side-by-side comparison: `ALVIX_FRONTEND=templates` on :8000, with React on :5173. (The default when unset is `react`.)

## Troubleshooting
- `KeyError: 'DJANGO_SECRET_KEY'`: `.env` is missing in the repo root.
- Signup verification code: the console email backend prints it in the runserver terminal (also shown on the page when DEBUG).
- `SyntaxWarning` lines from `google/genai/types.py` on Python 3.14 are harmless.
- Admin access: staff/superuser only. Make an existing account admin with `manage.py grant_admin <email-or-username>`.
