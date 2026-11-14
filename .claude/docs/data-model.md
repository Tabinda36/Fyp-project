# ALVIX data model

Source: `alvixapp/models.py` (latest migration `0015_assignment_output_image_and_unlock_all`). All models are in the single `alvixapp` app and use `django.contrib.auth.models.User`.

## Users & profile
| Model | Key fields | Notes |
|---|---|---|
| `Profile` (1:1 User, `related_name='profile'`) | `student_id` (`ALVIX-YYYY-NNNN`, unique), `full_name`, `phone`, `goal`, `dob`, `gender`, `profile_picture`, `interest_area`, `expectations`, `assessment_completed` | Auto-created by a `post_save` signal on `User`. `assessment_completed=False` forces the assessment page after login. |
| `UserSettings` (1:1 User, `related_name='settings'`) | `theme`, notification toggles, `sound_effects`, `autoplay_videos`, `public_profile` | Auto-created with Profile. |
| `StudentAssessment` (FK User) | `education_level`, `knowledge_level`, `interest` (FK AdminCourse), `interest_topic`, `learning_goal`, `learning_style`, `expectations` | A new row per assessment/retake (history). |

## Course catalog (admin-owned)
| Model | Key fields | Notes |
|---|---|---|
| `AdminCourse` | `course_code` (`ALV-CRS-YYYY-NNNN`), `slug`, `title`, `description`, `image`, `course_type` (Theoretical 7d / Practical 10d / Mixed 12d), `is_active` | The catalog entry. |
| `CourseLevel` (FK AdminCourse, unique per level) | `level` (Beginner/Intermediate/Advanced), `benchmark` (Harvard CS50 / MIT / Stanford-CMU), `slug`, `level_code`, `content_topics` JSON, `is_deep_generated`, totals | One per tier; created by `course_tier_service.create_course_tiers_and_curriculum`. |
| `CourseModule` | FK to `Course` / `CourseLevel` / `AdminCourse` (all nullable), `title`, `learning_objectives` JSON, `order` | Academic module. |
| `AcademicLesson` (FK module, level) | `reading_content`, `code_examples` JSON, `use_cases` JSON, `assignment_prompt`, `assignment_rubric`, `quiz_data` JSON | "Deep" curriculum from `deep_curriculum_service`. |
| `PresentationSlide` | FK `AcademicLesson` or `DailyLesson`; `slide_number`, `bullet_points` JSON, `speaker_notes`, `code_snippet`, `explanation`, `audio_file` | Slide deck rows. |
| `Course`, `Enrollment` | legacy public course + enrollment | Older models; largely superseded by AdminCourse/GeneratedCourse. |

## Student enrollment & learning
| Model | Key fields | Notes |
|---|---|---|
| `GeneratedCourse` (FK User, AdminCourse, CourseLevel) | `level`, `pace`, `course_type`, `content_topics`, `objective`, `ai_model` | **A student's enrolment instance.** Most student pages pick "active course" from here. |
| `DailyLesson` | FK `generated_course` (student copy) **or** `course_level` with `generated_course=NULL` (canonical template lesson); `day_number`, `content`, `video_url`, `is_unlocked`, `is_completed`, `deadline`, `presentation_data` JSON, `ppt_file`, `watch_time_seconds`, `required_watch_seconds` (180), `assignment_issued_at`, `quiz_issued_at` | Day N of the plan. Canonical lessons are copied to students on enrolment. All days are unlocked (`is_unlocked` default True since 0015). `assignment_issued_at` + `deadline` (2 days) are set when the student first opens that day's assignment. |
| `LessonTask` (1:1 DailyLesson) | `assignment_question`, `assignment_data` JSON, `quiz_data` JSON | Generated assignment & quiz. |
| `AssignmentSubmission` | `submitted_answer`, `file_submission`, `output_image` (code output screenshot), `marks`/`total_marks` (10), `ai_feedback`, integrity telemetry (`paste_count`, `pasted_chars_total`, `typing_duration_seconds`, `keystroke_count`, `peer_similarity_score`, `ai_generated_probability`, `copy_risk_level`), `admin_reviewed` | One per user+lesson (updated on resubmit). |
| `QuizSubmission` | `score`, `total_questions`, `percentage`, `wrong_answers_explanation` JSON, `question_summary` (HTML) | One attempt per lesson (enforced in `submit_quiz`). |
| `StudentProgress`, `StudentCourse`, `StudentReport`, `Performance` | legacy/aggregate progress | `Performance` is 1:1 User summary. |
| `Certificate` (FK User, GeneratedCourse) | `certificate_id` (unique), `is_unlocked`, `is_valid`, `overall_percentage`, `performance_grade`, `qr_code_data_uri`, `verification_url` | Recomputed on every submission by `certificate_service.update_or_create_student_certificate`. Unlocks at `COURSE_PASS_MARK` (35 %). |

## Communication & admin
| Model | Notes |
|---|---|
| `Report` | Student problem report (`technical`/`course_content`/`quiz_issue`/`other`, status pending → resolved). |
| `Notification` + `StudentNotificationStatus` | Admin broadcast; `post_save` fans out a status row per recipient (`all_students` → every User, `specific_student` → one). `enrolled_students` currently fans out to nobody. |
| `AIGenerationLog` | Audit of every AI prompt/response. |
| `AvatarSettings` (singleton id=1) | AI teacher "Inara" name, pronunciation, developer credit, intro behaviour. `get_settings()` returns/creates it. |

## Scoring settings (`alvix/settings.py`)
- `COURSE_PLAN_DURATIONS`: Theoretical 7, Practical 10, Mixed 12 days.
- `DAY_SCORE_WEIGHTS`: watch time 20 %, assignment 40 %, quiz 40 % (used by `certificate_service`).
- `COURSE_PASS_MARK = 35`.
- Dashboard, My Course and Performance all use `calculate_course_performance` (20/40/40) on the student's newest enrolment.
