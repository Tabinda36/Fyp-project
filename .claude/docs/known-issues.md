# Known issues and their status

Audit: 2026-11-14 (full project read). Fixes were applied during the React migration on the same date.
Severity: **H** = crash, security or data loss · **M** = wrong behaviour · **L** = cosmetic or cleanup.

## Fixed
| # | Sev | Issue | Fix |
|---|---|---|---|
| B1 | H | `evaluate_submission_with_ai` was undefined, so every assignment submission crashed | `alvixapp/assignment_grading.py`: Gemini rubric grading with a deterministic heuristic fallback |
| B2 | H | Redirects to non-existent URL names `student_dashboard` / `admindashboard` | Now `dashboard` / `admin_dashboard`; `LOGIN_REDIRECT_URL='dashboard'` |
| B3 | H | `profile` and `mark_notification_read` had no login check | `@login_required` added |
| B4 | H | Admin granted to hard-coded usernames/email | `permissions.is_alvix_admin`: staff/superuser only; `manage.py grant_admin <email>` |
| B5 | H | `DEBUG=True`, `ALLOWED_HOSTS=['*']` hard-coded | env-driven (`DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`); secure cookies when not DEBUG |
| B6 | H | Watch-time endpoint was `csrf_exempt` | CSRF enforced (the player sends `X-CSRFToken`) |
| B7 | H | Plain signup password stored in the session | Only a `make_password` hash is stored until OTP verification |
| B8 | M | `DEFAULT_FROM_EMAIL` unset | Configured via env, along with SMTP settings |
| B13 | H | Any student could open another student's lesson or certificate by id | `can_access_lesson` + ownership filters (admins may preview) |
| B14 | H | Profile save always crashed (template has no `goal` input → NULL into a NOT NULL column) | `goal` only updated when sent |
| B15 | H | Unlocked certificate page always 500 (`certificate_id` missing from context) | Added to the context; React shows the security code |
| B16 | H | Admin PPT upload always crashed (`process_lesson_ppt_upload` returns a dict, not a tuple) | Handled; errors become messages |
| B17 | M | Assignment PDF download used a tuple as the prompt | Fixed (`[0]`) |
| B18 | H | `?preview=1` let any student view/download an unearned certificate | Preview is admin-only (page + PDF) |
| B19 | M | An admin previewing a student's certificate created a certificate in the admin's name | Certificate is always issued to the course's student |
| B21 | H | (review) Anonymous login/signup/OTP API endpoints skipped CSRF | `CsrfSessionAuthentication` enforces CSRF on every unsafe request |
| B22 | H | (review) Profile email unvalidated: duplicates, `None` crash | Validated (format, unique); empty keeps current |
| B23 | H | (review) Uploads unvalidated, so `.html`/`.svg` served from /media = stored XSS | `upload_safety.py`: real images only for pictures; executable/HTML types blocked for assignments |
| B24 | H | (review) `/delete_user/<id>/` and `.../regenerate/` acted on a plain page open | Delete no longer happens on open (use the confirm modal); regenerate always confirms |
| B25 | M | (review) Legacy `/submit-lesson/<id>/` had no ownership check | `can_access_lesson` |
| B26 | M | (review) Signup OTP could be guessed without limit | 5 attempts, then the pending signup is discarded |
| B27 | M | (review) With `DJANGO_DEBUG=False` uploaded media was not served | `/media/` served by Django (`ALVIX_SERVE_MEDIA`) |
| B20 | M | Admin pages showed empty/wrong data: course cards (all "Stanford", empty fields, "7 Days"), enrolment/telemetry tables, analytics students/rating/activity, two analytics bars (`84%%`) | Context builders now supply the real values (fixes legacy + React) |
| A8 | M | Tests called live Gemini when a key was present | `alvix.test_runner.HermeticTestRunner` blanks AI keys |
| F1 | M | Admin pages never loaded Bootstrap JS (dead tabs/collapses/modals) | Bootstrap bundle loaded globally in React |
| F2 | M | Assignment telemetry inputs were never populated | React page tracks paste count, pasted characters, keystrokes and typing time |
| F3 (part) | M | Assignment score shown "/5" while marked out of 10; history headers in swapped order | Shows real `total_marks`; header order fixed |
| F5 | L | generate_course doubled the 260px left margin | Fixed in React |
| F7 (part) | L | `#fullscreenBtn` did nothing; "Export Analytics" did nothing | Fullscreen API; client-side CSV export |
| F8 (part) | L | Certificate showed email under "STUDENT ID" | Shows the student ID |
| — | L | No dependency manifest | `backend/requirements.txt`, `.env.example` |
| F3 (scores) | M | Dashboard / My Course progress (40/30/30 estimate, oldest course, fake watch time) never matched the Performance page | Both now use `certificate_service.calculate_course_performance` (20/40/40) on the same course as the Performance page (2026-11-14 student testing) |
| Q1 | M | A quiz attempt could be recorded twice (double click / retry) | `submit_quiz` locks the lesson row and records one attempt per lesson; old duplicates are listed once (latest), never deleted |
| P1 | M | Jumping to a slide while the lecture played skipped onward: the cancelled speech's `onerror` counted as "slide finished" | `narrationId` guard in `inara_player.js` (jump, mute, audio play rejections) |
| L1 | — | Owner request: daily lessons no longer unlock one by one | All days unlocked (creation paths + migration 0015); Assignment/Quiz pages without `lesson_id` open the first day without a submission of that kind |
| S1 | — | Owner request: assignment code-output screenshot | `AssignmentSubmission.output_image` (validated image), shown in the history; grader is told it was attached |

## Open (not changed: either design/copy decisions or outside the migration scope)
| # | Sev | Issue |
|---|---|---|
| A1 | H | Gemini, edge-tts and gTTS run synchronously inside requests. The `ThreadPoolExecutor` timeouts don't work, and `deep_curriculum_service` passes `timeout: 15.0` (likely read as milliseconds). → Move generation to a management command or a background worker |
| A2 | H | `sync_student_lessons_from_canonical` can delete and recreate lessons (`force=True`) during enrolment, orphaning progress |
| A3 | M | Fallback AI output is logged as `is_validated=True` |
| A4 | M | Quiz schema differs between generation paths (`correct_answer` index vs `correct` string) |
| A5 | M | Copy detection compares peers by `day_number` across unrelated courses |
| A6 | M | Hand-written QR encoder likely produces unscannable codes (use `segno`/`qrcode`) |
| A7 | M | Certificate PDF always prints "VERIFIED"; uses Windows-only font paths; verify URL falls back to `127.0.0.1` |
| F4 | M | AI/lesson HTML rendered unescaped (`|safe` → `dangerouslySetInnerHTML`, `innerHTML` in `inara_player.js`) |
| B9–B12 | L | Unrouted `submit_report`; duplicate URL names (kept on purpose for compatibility); `enrolled_students` notifications fan out to nobody; dashboard `popup_notification` is hard-coded `None` |
| F6 | L | Inter/Poppins declared but not loaded on some pages (kept for visual parity) |
| A9, A10 | L | Joke fallback YouTube video; dead code (`pdf_utils.create_lesson_pdf`, `generate_teacher_lecture_json`) |
| T1 | L | Backend test suite is slow (~8 min); password hashing and course generation per test dominate |
| — | L | Not yet verified in a real browser by a human: lesson player lifecycle (speech, audio, fullscreen), Bootstrap modals on admin pages |
