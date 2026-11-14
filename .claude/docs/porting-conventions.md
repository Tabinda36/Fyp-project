# Porting conventions: Django template → React page + API (binding for every page)

Repo: `backend/` (Django; run with `..\.venv\Scripts\python.exe manage.py ...` from `backend/`) and `frontend/` (Vite + React 19, plain JavaScript/JSX).

## Golden rule
The React page must look and behave **identically** to the original template:
- same DOM structure, ids, class names, inline styles, copy (including emojis and non-English text), icons, links and forms;
- same CSS: copy every `<style>` block **verbatim** into `XxxPage.css`;
- same CDN stylesheets: student/admin child pages inherit them from the layouts. Extra `<link>`s the child template loaded go in `usePageAssets({ links })`.

Do not redesign, restyle or "clean up" markup. Allowed changes (owner-approved "fix broken behaviour only") are listed per area in your brief.

## Already built (use; don't rewrite)
| File | Purpose |
|---|---|
| `frontend/src/hooks/usePageAssets.js` | `usePageAssets({ links, css, bodyClass, title })` adds the page's stylesheets/CSS/body class on mount and removes them on unmount |
| `frontend/src/cdn.js` | `BOOTSTRAP_533`, `BOOTSTRAP_530`, `ICONS_1113`, `ICONS_1111`, `googleFont(query)`, `FONT_ADMIN`, `LOGO` |
| `frontend/src/api/client.js` | `apiFetch(path, { method, body, query })` (path relative to `/api/v1`; JSON or `FormData`; CSRF handled), `ApiError` (`.status`, `.data`, `.errors`), `toFormData(obj)`, `getCookie` |
| `frontend/src/hooks/usePageData.js` | `const { data, loading, error, reload, setData, notFound, ready } = usePageData('/student/dashboard/', query)`; handles `redirect`/`messages` in the payload and 401/403 → login |
| `frontend/src/hooks/useFlash.jsx` | Django `messages` replacement: `const { addMessage, addMessages } = useFlash()`; `const messages = useFlashMessages()` returns `[{id, tags, message}]`; `bootstrapTag(tags)` maps `error` → `danger` |
| `frontend/src/hooks/useAuth.jsx` | `const { user, refresh, setUser, logout } = useAuth()`; `user` = `/api/v1/auth/me/` payload (same fields templates read from `request.user`, `request.user.profile`, `request.user.settings`) |
| `frontend/src/utils/djangoFormat.js` | `djDate(iso, 'd M Y, h:i A')` (= `|date`), `timesince`, `truncatechars`, `truncatewords`, `floatformat`, `dflt` (= `|default`), `widthratio`, `lines` |
| `frontend/src/layouts/StudentLayout.jsx` / `AdminLayout.jsx` | The two base templates (sidebar + main area). Pages are rendered inside them via routes; `children` is also supported for standalone use |
| `frontend/src/player/inara_player.js` | Copy of `backend/static/js/inara_player.js` (defines `window.AvatarPlayer/IntroSequence/LecturePlayer`) |
| `backend/alvixapp/api/common.py` | `IsAlvixAdmin`, `user_payload`, `file_url`, `dt` (ISO in server TZ), `display(obj, field)`, `pick`, `ok(message, level, **data)`, `form_errors(form)`, `collect_messages(request)` |
| `backend/alvixapp/permissions.py` | `is_alvix_admin(user)`, `can_access_lesson(user, lesson)` |
| Auth API | `GET /api/v1/auth/csrf/`, `GET /api/v1/auth/me/`, `POST /api/v1/auth/login/ {email,password}` → `{ok, redirect, user}` or 400 `{ok:false, error}`, `POST /api/v1/auth/logout/` |

## Backend pattern
1. **Share logic, don't copy it.** Move the body of the original view that builds the template context into a function in `backend/alvixapp/page_context/<area>.py` (e.g. `build_dashboard_context(request)` returning the same dict of model objects). Then change the original view in `views.py` to `return render(request, template, build_..._context(request))`.
   - For POST handlers, extract the action into a function returning a result the view and the API both use.
   - The legacy template views must keep working: the 40 existing tests run against them.
   - **`views.py` is edited by several agents in parallel.** Only touch your own view functions, Read the file right before each Edit, and keep edits small.
2. Write DRF `APIView`s in your area module (`backend/alvixapp/api/<area>.py`, its `urlpatterns` already included under `/api/v1/<area>/`).
   - GET returns everything the template used, serialized to plain JSON. Keep the template's variable names as keys and nest exactly what the template dereferences. Use `dt()` for dates, `file_url()` for files, `display()` for `get_*_display`.
   - Pre-compute anything the template computed with filters, or format it in React with `djangoFormat.js`.
3. Permissions: default is `IsAuthenticated`. Admin endpoints use `[IsAuthenticated, IsAlvixAdmin]`. Public endpoints use `AllowAny`. Enforce ownership exactly as (or stricter than) the old view.
4. Actions return `ok(message, level, redirect='/path/', ...)` or 400 with `{ok: false, errors: {...}}` / `{ok: false, error: '...'}`, reusing the template's exact message text. Use `redirect` wherever the old view redirected.
5. Tests: create `backend/alvixapp/test_api_<area>.py`. Cover auth/permission checks, ownership, and the response keys the page reads. Never call Gemini/YouTube (the test runner blanks keys; mock anything slow). Run `..\.venv\Scripts\python.exe manage.py test alvixapp.test_api_<area>` and make sure `manage.py check` passes.

## Frontend pattern
- Files: `frontend/src/pages/<area>/<Name>Page.jsx` + `<Name>Page.css` (verbatim template CSS, imported as `import css from './<Name>Page.css?raw'` and passed to `usePageAssets({ css })`).
- Register routes in your area's routes file only (`frontend/src/routes/<area>Routes.jsx`). Paths equal the Django paths, e.g. `<Route key="dashboard" path="/dashboard/" element={<DashboardPage />} />`, `<Route key="lesson" path="/daily-lesson/:lessonId/" element={...} />`.
- Translation rules:
  - `class` → `className`, `for` → `htmlFor`
  - inline `style="a:b"` → `style={{ a: 'b' }}` (same values)
  - `onclick` → React handlers
  - `{% url %}` → React `<Link to>` for SPA pages; plain `<a href>` for backend URLs (PDF/PPTX downloads, `/admin/`)
  - `{% static 'x' %}` → `/static/x`
  - `|safe` → `dangerouslySetInnerHTML` (same as before)
  - `{% csrf_token %}` → nothing (apiFetch sends the header)
- Forms: controlled or uncontrolled inputs with the **same `name`s**. Submit via `apiFetch`, then `addMessages(res.messages)` and navigate to `res.redirect` (or `reload()` when it redirects to itself). On 400, show errors where the template showed them.
- Inline `<script>` behaviour → `useEffect`/handlers. Bootstrap JS (`window.bootstrap`) is loaded globally, so `data-bs-toggle` tabs/collapses/modals work. Create programmatic instances in `useEffect` with cleanup.
- While loading, render nothing (`if (!ready) return null;`). Server pages never showed spinners.
- The template's `{% if messages %}` blocks → `useFlashMessages()` with identical markup.
- Run `npm run lint` and `npm run build` in `frontend/`. Both must pass with zero errors.

## Definition of done (per page)
API endpoint(s) + tests passing · React page with verbatim CSS and markup · route registered · lint/build green · legacy template view still works · a short parity self-review against the template (every `{{ }}`/`{% if %}`/`{% for %}` branch, every link and form field).
