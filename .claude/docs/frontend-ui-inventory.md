# ALVIX frontend UI inventory (source of truth for the React port)

32 Django templates in `alvixapp/templates/` + `static/js/inara_player.js`. Every page carries its CSS inline in `<style>` blocks; there are no shared CSS files. Copy those blocks as they are.

## Libraries (CDN) — reuse the same versions in React
| Library | Version | Where |
|---|---|---|
| Bootstrap CSS | **5.3.3** | student base + children, signup, suggested_courses |
| Bootstrap CSS | **5.3.0** | admin base + children, certificate_verify |
| Bootstrap JS bundle | 5.3.3 / 5.3.0 | only dashboard.html, suggested_courses.html, user_management.html |
| Bootstrap Icons | 1.11.3 (1.11.1 on certificate_verify) | almost everywhere |
| Google Fonts | Plus Jakarta Sans, Poppins, Cinzel, Cormorant Garamond, Montserrat, JetBrains Mono | per page |

No Tailwind, Chart.js, jQuery or Font Awesome. Analytics uses Bootstrap progress bars only.

## Theme tokens ("emerald + gold", light)
- Primary green `#064e3b`. Other greens: `#047857`, `#065f46`, `#043e2e` (hover), `#022C22`, `#0A5C46`. Separate families: `#1B5E20` / `#2E7D32` (student base) and `#01411C` (generate_course, course_details).
- Gold `#d4af37`. Darker golds: `#b8860b`, `#AA771C`. Creams: `#F9E076`, `#FEF9E7`, `#fdfbf7`, `#FCFBF7`.
- Backgrounds: `#ffffff`, `#f8fafc`, `#f0fdf4`, `#f1f7f4`, `#f2f6f4`, `#eef2f0`.
- Patterns:
  - Buttons: `linear-gradient(135deg,#064e3b,#047857)` with a gold border.
  - Cards: white with a 1.5–2px gold border and 14–24px radius.
  - Focus ring: `0 0 0 3px rgba(212,175,55,.2)`.
- Tier badges: Harvard `#A51C30`, MIT `#0f172a` with `#38bdf8` text, Stanford `#8C1515`.
- Dark mode exists only on the student base: `body.dark-mode` when `user.settings.theme == 'Dark'` (bg `#042f2e`, cards `#064e3b`, headings `#fbbf24`).
- Dark-background pages: suggested_courses (`#09130e`), verify_otp (`#0f172a`), certificate (`#0F172A`), certificate_verify (green gradient).

## Layout inheritance → React layouts
| Django base | Children | React layout |
|---|---|---|
| `student_dashboard/dashboard.html` (`{% block content %}`): fixed 260px white sidebar with a gold border, 7 links, mobile off-canvas `toggleMenu()`, "ALVIX" watermark | assessment, profile, mycourse, notifications, performance, reports, settings, certificate_locked, course_data/{generate_course, course_content, daily_lesson, assignment, quiz} | `StudentLayout` |
| `admin_db/admindashboard.html` (`{% block admin_content %}`): Bootstrap grid sidebar (col-lg-2), hard-coded admin profile, animated "A L V I X" wordmark + cap | all other admin_db pages | `AdminLayout` |
| standalone | mainpage, login, signup, verify_otp, suggested_courses, logout, certificate_verify, course_data/certificate | standalone pages |

Child pages put `<style>`/`<link>` inside the block and override `body{}` globally. To keep the look identical in React, a page's global CSS must apply only while that page is mounted (inject on mount, remove on unmount). Otherwise styles leak between routes, which never happened in multi-page Django.

## Pages
| Page | Key UI | Forms / endpoints | Inline JS |
|---|---|---|---|
| mainpage | Centred card, logo, 3 feature cards, gold text-stroke h1, drifting glows | link to signup | none |
| login | Gradient card, icon inputs | POST `email`, `password`, `remember_account`; `error` | password toggle |
| signup | 2-step pills; step 1 form, step 2 OTP | POST `full_name, username, email, password, confirm_password`; then `verify_code_submit, verification_code` | spinner on submit |
| verify_otp | Minimal dark page (legacy) | POST `otp_code` | none |
| suggested_courses | AI recommendation card + choices B / C1 / C2 (tabs) / A | POST `action` + `level` / `other_course_id, other_level` / `custom_course_title, custom_level, custom_pace` | BS tabs, spinner |
| dashboard (home) | Profile topbar, enrolled course cards, performance + certificate card, notification modal | `fetch POST /notifications/read/<id>/` | modal auto-show (localStorage `dismissed_notif_<id>`) |
| assessment | Option tiles + char counter | POST `interest_area, goal, expectations` (≥20) | tile select, counter, guard |
| profile | Avatar upload with preview | POST multipart `profile_picture, full_name, email, phone, dob, gender` | FileReader preview |
| mycourse | Hero, 5-tab horizontal nav (content / lessons / assignment / quiz / overview), course switcher | links only | tab switch + URL hash |
| course_content | Hero, Lesson Plan / Content pills, collapsible topics | links only | collapse button text swap |
| daily_lesson | Slide player, Inara intro stage, corner avatar, captions, explanation drawer, completion overlay | watch-time POST JSON | `inara_player.js` + glue |
| assignment | Prompt, rubric, submission form, popups, history | POST multipart `student_submission, file_submission` + hidden telemetry | overlays, 60s reset |
| quiz | MCQ radios `q_<id>`, result popups, history | POST | overlays, 60s reset |
| performance | Score banner, per-day table, certificate status | links | none |
| reports | Report form, toast messages | POST `course_name, problem_type, problem_title, problem_description` | toast fade |
| notifications | List with read state | `fetch POST /notifications/read/<id>/` | reload on success |
| settings | Theme + toggles | POST form widgets | none |
| logout | Confirm card | POST | `history.back()` |
| certificate_locked | Requirements + progress | links | none |
| certificate | 1050px canvas, SVG flourishes, signatures, seal, QR, print CSS | PDF link, verify link | `window.print()` |
| certificate_verify | Valid / invalid card | none | none |
| admin dashboard | 4 stat cards, welcome | none | wordmark animation |
| user_management | Table + edit/delete modals | POST `action=edit/delete, user_id, username, email, phone, dob, password` | search filter, modal prefill |
| courses_info | Tier cards, filter pills, search | GET `tier, search` | none |
| add_course | Form + tier preview | POST multipart `title, image, description` | none |
| course_details | Tiers → modules → lessons accordions, enrolments | none | manual toggle-all |
| level_course_view | 4 tabs, PPT upload modal per lesson | POST multipart `ppt_file`; GET regenerate | toggle-all |
| level_users_telemetry | KPIs + table | none | table filter |
| admin_reports | Report rows | POST `feedback`; POST delete | confirm |
| admin_notifications | Compose + history | POST `target_recipient, specific_student_id, category_type, subject_heading, notification_body` | recipient toggle |
| analytics | KPI cards, progress bars, top courses, activity | none | none |
| admin_settings | Avatar settings form + asset grid | POST form widgets | none |

## inara_player.js (port as-is, wrap in React)
`window.AvatarPlayer`, `window.IntroSequence`, `window.LecturePlayer` are plain ES classes that query fixed DOM ids (`slideViewport`, `mainPlayPauseBtn`, `prevSlideBtn`, `nextSlideBtn`, `slideDotsContainer`, `captionBar`, `completionOverlay`, `lessonWatchTimeBadge`, `inaraIntroStage`, `introAvatarImg`, …).

What it does:
- Uses Web Speech API (female voice heuristic) and HTML5 Audio with Web Audio analyser lip-sync.
- Keyboard: Space toggles play/pause, ←/→ change slide.
- Watch-time: POSTs `{seconds}` to `/lesson/<id>/watch-time/` every 5 seconds of active, visible playback.

Port strategy: the React `DailyLessonPage` renders the identical DOM, then instantiates the three classes in a `useEffect` (cleanup: cancel speech, pause audio, clear intervals). Do not rewrite the player during the port.

## Existing UI defects to preserve, not silently "fix", during a 1:1 port (see known-issues.md)
- The admin base has no Bootstrap JS, so tabs, collapses, modals and alert dismiss do nothing on course_details, level_course_view and admin_settings.
- generate_course double-applies the 260px margin.
- Pages declare Inter/Poppins without loading them.
- Scoring copy is inconsistent (40/30/30 vs 20/40/40; quiz /5 vs /10).
- Assignment telemetry inputs are never filled.
- `#fullscreenBtn` has no handler.
- certificate.html prints the email under "STUDENT ID".
