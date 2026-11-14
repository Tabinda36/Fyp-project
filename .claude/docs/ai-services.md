# ALVIX AI & content-generation layer

All modules are in `alvixapp/`. SDK: `google-genai` (`genai.Client(api_key=...).models.generate_content`), model **`gemini-2.5-flash`**, `response_mime_type="application/json"`, temperature 0.3–0.4. Key: `GEMINI_API_KEY` (env/settings). Every AI path has a deterministic fallback, so the app runs without keys.

| Module | Responsibility | Main entry points | External calls |
|---|---|---|---|
| `ai_services.py` | Course curriculum, level content & day plan, assignment + quiz per day, topic slide decks | `generate_course_with_gemini` (= `generate_course_content_with_ai`), `get_curated_level_content_and_plan`, `generate_level_content_and_plan_with_ai`, `build_track_assignment_and_quiz`, `generate_lesson_slide_deck_with_ai` | Gemini |
| `ai_helpers.py` | Key getters, `log_ai_generation` → `AIGenerationLog`, YouTube lookup, assignment/quiz gen, certificate remarks (rule-based) | `fetch_top_mentor_video`, `generate_assignment_and_quiz` | YouTube Data API v3 search (timeout 8 s), Gemini |
| `course_recommendation.py` | Filter catalog by interest/goal, ask Gemini to pick 1 course + level + reason; validated against DB | `suggest_best_fit_course_with_ai(user, interest_area, goal, expectations) -> (course, reason, level)` | Gemini |
| `course_tier_service.py` | Create Beginner/Intermediate/Advanced `CourseLevel`s, canonical lessons, clone them per student | `create_course_tiers_and_curriculum`, `fetch_and_enroll_student_in_level`, `sync_student_lessons_from_canonical` | none (`use_ai=False`) |
| `deep_curriculum_service.py` | University-benchmarked modules → academic lessons → slides → canonical `DailyLesson` + `LessonTask` | `generate_deep_university_curriculum(level, force, use_ai)` | Gemini (timeout misconfigured, see known issues) |
| `ppt_generator.py` | Build 13+ slide lecture from lesson content, 450–650-word narrations, render `.pptx` (python-pptx), MP3 narration | `build_dynamic_slides_from_content`, `enrich_lecture_with_narrations`, `get_or_generate_lesson_lecture`, `generate_lesson_ppt_bytes` | edge-tts (`en-US-ChristopherNeural`) → `MEDIA_ROOT/lectures/lesson_<id>/slide_N.mp3` |
| `ppt_service.py` | Teacher-uploaded PPTX → slides + explanations + audio (background thread); player payload | `process_lesson_ppt_upload`, `ensure_lesson_slides_and_explanations`, `build_player_payload` | Gemini per slide, edge-tts → gTTS |
| `copy_detection.py` | Assignment integrity: paste telemetry + peer similarity (difflib) + AI-text heuristic | `evaluate_submission_copy_risk(...) -> (level, peer_sim, ai_prob, details)` | none |
| `certificate_service.py` | Per-day score (20/40/40), grade bands, pass at 35 %, create/refresh `Certificate` | `calculate_course_performance`, `update_or_create_student_certificate` | none |
| `certificate_pdf.py` | Draw certificate with Pillow → PDF | `generate_certificate_pdf_bytes(cert)` | none (uses Windows fonts dir) |
| `qr_generator.py` | Hand-written QR encoder (v1–4, ECC L) → data URI | `generate_qr_base64_data_uri` | none |
| `pdf_utils.py` | Lesson PDF — **broken, unused** | `create_lesson_pdf` | — |

## Lifecycle (student)
1. Signup → OTP (console email) → login → **assessment** (`StudentProfileAssessmentForm`: interest, goal, expectations ≥ 20 chars).
2. `suggest_best_fit_course_with_ai` → `/suggested_courses/` → enrol: `create_course_tiers_and_curriculum` + `fetch_and_enroll_student_in_level` clones canonical `DailyLesson`s into a `GeneratedCourse`.
3. Daily lesson page builds/caches `presentation_data` (slides + narration); the browser plays it with the Inara avatar and speech synthesis, pinging `/lesson/<id>/watch-time/` while it plays.
4. Assignment (with paste/typing telemetry → copy risk) and quiz (≥ 50 % unlocks next day).
5. Each submission recalculates the `Certificate`; unlocks when all days are done and score ≥ 35 %. Public verify page + PDF + QR.

## Root-level dev scripts (not runtime)
- `generate_avatar_assets.py` — draws the 4 Inara PNG frames into `public/assets/avatar/` (keep).
- `update_ai_services.py` — stale source-patching script with a wrong path; do not re-run.
- `check_overlays.py`, `inspect_*.py` — debug greps hard-coded to another machine's path (`d:/ALIF/...`); safe to delete.
