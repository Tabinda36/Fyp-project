# ALVIX — instructions for Claude Code

AI-powered adaptive learning platform (final-year project).
- **Frontend:** React 19 + Vite in `frontend/`. It is a 1:1 port of the original Django templates.
- **Backend:** Django 6.1 + DRF JSON API in `backend/` (Python 3.14). Database: Supabase PostgreSQL when `DB_HOST` is set in `.env` (IPv4 session pooler), otherwise local SQLite.
- The legacy templates still exist and can be switched on with `ALVIX_FRONTEND=templates`.

## Start here
- Architecture and folder layout: `.claude/docs/architecture.md`
- Models: `.claude/docs/data-model.md`
- Routes and API: `.claude/docs/url-map.md`
- AI/services: `.claude/docs/ai-services.md`
- UI/theme inventory: `.claude/docs/frontend-ui-inventory.md`
- How pages are ported and built: `.claude/docs/porting-conventions.md`
- Bugs and status: `.claude/docs/known-issues.md`
- Migration plan/checklist: `.claude/docs/react-migration-plan.md`

## Commands (PowerShell)
```powershell
# backend (from backend/)
..\.venv\Scripts\python.exe manage.py runserver      # http://127.0.0.1:8000
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py test alvixapp
..\.venv\Scripts\python.exe manage.py makemigrations alvixapp
# frontend (from frontend/)
npm run dev        # http://localhost:5173, proxies to Django
npm run lint
npm run build
```

## Rules
- **UI parity is sacred.** No page may change its look, theme, colours, fonts, copy or behaviour unless the owner explicitly asks.
  - Each page's CSS is the template's `<style>` copied verbatim, loaded per page with `usePageAssets`.
  - Each page loads exactly the CDN stylesheets its template loaded.
- Business logic lives in Python. `page_context/` builders are shared by the API views and the legacy template views; don't duplicate logic in React or in API views.
- API:
  - Lives under `/api/v1/` with session auth and CSRF.
  - Admin endpoints use `IsAlvixAdmin`.
  - Student endpoints enforce ownership.
  - Downloads (PDF/PPTX) stay plain Django URLs.
- Never read, print or commit `.env`. Secrets come from `settings` / `os.environ` only.
- Every AI call needs a fallback. Tests never hit the network (hermetic test runner).
- Model changes need migrations that are safe for existing rows. Never delete student progress as a side effect.
- Report test results honestly. Don't commit or push unless asked.

## Subagents (`.claude/agents/`)
- `django-backend-engineer`
- `react-frontend-engineer`
- `ui-parity-reviewer`
- `ai-services-engineer`

## Skills (`.claude/skills/`)
- `port-template-to-react`
- `add-api-endpoint`
- `gemini-ai-feature`
- `run-dev-stack`
