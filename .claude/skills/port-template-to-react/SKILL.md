---
name: port-template-to-react
description: Step-by-step workflow to port one ALVIX Django template page to a pixel-identical React page plus the JSON API endpoint it needs. Use when asked to convert/migrate a specific page (e.g. "port the dashboard page to React").
---

# Port a Django template page to React (zero UI change)

Source of truth = the original template. The React page must look and behave identically.

## 1. Inventory the page
- Open the template in `alvixapp/templates/<area>/<page>.html`.
- Find its view in `alvixapp/views.py` (see `.claude/docs/url-map.md`) and list every context variable it passes.
- List: CDN `<link>`/`<script>` tags, `<style>` blocks, inline `<script>` behaviour, forms (action, method, field names, hidden fields), `{% url %}` links, `messages` usage.

## 2. Backend: add the JSON endpoint (django-backend-engineer)
- Add a read endpoint `GET /api/v1/<resource>/` returning exactly the context data the template used (serialize model instances, keep field names).
- Add write endpoints for each form (`POST/PATCH`) reusing the same validation/service code as the old view. Return `{ "ok": true, "message": "...", ...data }` or `{ "ok": false, "errors": {...} }` with proper status codes.
- Enforce `@login_required` / `admin_required` and object ownership exactly as the old view did.
- Add a test in `alvixapp/tests/` (or `tests.py`) for auth, ownership and response shape.
- Leave the old template view and URL in place (the two run side-by-side until cut-over).

## 3. Frontend: build the page (react-frontend-engineer)
- File: `frontend/src/pages/<area>/<PageName>Page.jsx` + `<PageName>Page.css` (template `<style>` copied verbatim).
- Use the shared layout (`StudentLayout`, `AdminLayout`, `PublicLayout`) only if the template's sidebar/topbar markup is byte-identical to the shared one; otherwise keep the page-specific markup.
- Convert `class=` → `className=`, `for=` → `htmlFor=`, inline `style="..."` → style objects, self-close void tags. Keep ids and class names unchanged.
- Data: `useApi('/api/v1/...')` hook; show the same empty states the template showed.
- Inline scripts → `useEffect` hooks or small components; third-party widgets (Chart.js etc.) initialised in `useEffect` with cleanup.
- Register the route in `frontend/src/routes.jsx` at the SAME path as the Django URL.

## 4. Verify
- `npm run lint && npm run build` in `frontend/`.
- Run both servers (see `run-dev-stack` skill) and compare old (`:8000/<path>`) vs new (`:5173/<path>`) side by side at desktop and mobile widths.
- Hand off to the `ui-parity-reviewer` agent. Fix every blocker before marking the page done.
- Tick the page in the checklist in `.claude/docs/react-migration-plan.md`.
