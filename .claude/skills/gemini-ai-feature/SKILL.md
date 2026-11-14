---
name: gemini-ai-feature
description: Pattern for adding or changing a Google Gemini-powered feature in ALVIX (generation, grading, recommendation) with strict JSON output, fallbacks, audit logging and tests. Use when touching ai_services.py or any *_service.py that calls Gemini.
---

# Gemini feature pattern

1. **Prompt** — build in a dedicated function `build_<feature>_prompt(...) -> str`. Ask for JSON only, give the exact schema and one short example.
2. **Call** — use the shared client helper in `ai_services.py` (`google.genai`), model name from settings. Set a timeout; catch every exception.
3. **Parse** — strip markdown fences, `json.loads`, validate required keys/types, clamp numbers (scores, percentages).
4. **Fallback** — if no `GEMINI_API_KEY`, an exception, or invalid JSON → return deterministic content from the curated fallbacks (see `get_curated_level_content_and_plan`). The UI must never show an empty page.
5. **Log** — write an `AIGenerationLog(user, item_type, item_id, model_used, prompt, response_json, is_validated)` row.
6. **Persist** — save generated content on the model (e.g. `DailyLesson.presentation_data`, `LessonTask.quiz_data`) so it's generated once and served from the DB afterwards.
7. **Test** — patch the client; test valid JSON, invalid JSON → fallback, and no-key → fallback.

Never put API keys in code, logs, prompts, or the frontend. The React app must never call Gemini directly — always via the Django API.
