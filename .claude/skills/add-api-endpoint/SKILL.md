---
name: add-api-endpoint
description: Conventions for adding a JSON REST endpoint to the ALVIX Django backend (Django REST Framework, session auth, CSRF, ownership checks, tests). Use whenever a React page needs data or an action from the backend.
---

# Add an ALVIX API endpoint

## Location & naming
- Code: `alvixapp/api/` package — `serializers.py`, `views.py`, `urls.py` (split per area as it grows: `api/student.py`, `api/admin.py`, `api/courses.py`).
- Mounted at `/api/v1/` in `alvix/urls.py`. Resource-style paths, kebab-case: `/api/v1/lessons/<id>/watch-time/`.

## Auth & security
- Session authentication (same cookie as the Django site) + CSRF. React reads `csrftoken` cookie and sends `X-CSRFToken`. Do not use `csrf_exempt`.
- Student endpoints: `IsAuthenticated` + filter querysets by `user=request.user`.
- Admin endpoints: custom `IsAlvixAdmin` permission mirroring `admin_required` in `views.py` (move that helper to `alvixapp/permissions.py`, drop hardcoded usernames/emails).
- Never return password hashes, OTPs, raw AI prompts, or another student's data.

## Shape
- Success: the resource JSON (or `{ "ok": true, "message": "..." }` for actions).
- Validation error: HTTP 400 `{ "ok": false, "errors": { "field": ["msg"] } }` — messages identical to the old template's messages.
- Use the existing service functions; do not duplicate logic from `views.py` — extract it into a service first if needed, and have both the old view and the API call it.

## Files & downloads
- Uploads: `multipart/form-data` via `MultiPartParser` (profile picture, assignment file, lesson PPT, course image).
- PDF/PPT downloads stay as normal Django URLs (`/certificate/<id>/download-pdf/` etc.); React links to them with a plain `<a href>`.

## Test checklist
- Anonymous → 403/401; wrong user → 404; admin-only → 403 for students.
- Response keys match what the React page reads.
- Gemini/YouTube mocked.
