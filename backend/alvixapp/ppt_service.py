"""
ALVIX PowerPoint Presentation & AI Explanation Service  (FIXED VERSION)

What this module does
---------------------
1. Reads a teacher .pptx upload (python-pptx) and extracts every slide.
2. Builds the slide deck that the student SLIDE PLAYER shows:
      uploaded PPT slides  ->  OR  ->  the same generated deck that the
      "Download PPT" button uses (ppt_generator.get_or_generate_lesson_lecture).
3. Adds an easy explanation + real-world example + key takeaway for every slide.
4. Converts every slide narration to voice (edge-tts if installed, else gTTS)
   in a BACKGROUND thread, so the page never waits for audio.
5. Stores everything in DailyLesson.presentation_data + PresentationSlide.

Fixes compared to the old version
---------------------------------
* The missing import of get_or_generate_lesson_lecture (this was why the
  player always showed 7 hard-coded sample slides instead of the real PPT).
* Old saved "sample" decks are detected and regenerated automatically.
* The slide payload keeps ALL original slide fields (concepts, invariants ...).
* Audio is no longer cut to 160 characters, and audio_url is only set when
  the mp3 file really exists (no more 404 -> double speech).
* Page load is fast: no Gemini call per slide unless use_ai=True.
"""

import os
import re
import copy
import json
import logging
import threading

from django.conf import settings
from django.db import transaction

from .models import DailyLesson, PresentationSlide

logger = logging.getLogger(__name__)

PLACEHOLDER_TITLE_PREFIX = "Introduction & Core Objectives"
MIN_NARRATION_WORDS = 150          # shorter text is not used as a lecture narration
AUDIO_BYTES_PER_WORD = 700        # smaller mp3 than this = truncated / broken file


# ==============================================================================
# 1. SMALL HELPERS
# ==============================================================================

def clean_text_for_tts(text):
    """Cleans text so it sounds smooth and natural when spoken by TTS."""
    if not text:
        return ""
    text = str(text)
    text = re.sub(r'<[^>]+>', ' ', text)                                   # html tags
    text = re.sub(r'```[\s\S]*?```', ' code example omitted for audio narration. ', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'[*_~#]', '', text)                                     # markdown marks
    text = re.sub(r'^[•\-\*>\d\.\)]+\s*', '', text, flags=re.MULTILINE)    # bullet markers
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [value]


def _join(values):
    return " ".join(str(v).strip() for v in _as_list(values) if str(v).strip())


def _word_count(text):
    return len(str(text or "").split())


def _course_title(lesson):
    try:
        if lesson.generated_course and lesson.generated_course.admin_course:
            return lesson.generated_course.admin_course.title
        if lesson.course_level and lesson.course_level.parent_course:
            return lesson.course_level.parent_course.title
    except Exception:
        pass
    return ""


# ==============================================================================
# 2. PPTX EXTRACTION
# ==============================================================================

def extract_text_from_shape(shape):
    """Recursively extracts text from a PPT shape (text box, table, or group)."""
    texts = []
    try:
        if getattr(shape, 'has_text_frame', False) and shape.has_text_frame:
            for paragraph in shape.text_frame.paragraphs:
                p_text = paragraph.text.strip()
                if p_text:
                    texts.append(p_text)
        elif getattr(shape, 'has_table', False) and shape.has_table:
            for row in shape.table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    texts.append(" | ".join(row_cells))
        else:
            from pptx.enum.shapes import MSO_SHAPE_TYPE
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                for sub_shape in shape.shapes:
                    texts.extend(extract_text_from_shape(sub_shape))
    except Exception as e:
        logger.debug(f"Error extracting shape text: {e}")
    return texts


def _ppt_stream(field_file):
    """Reads a stored PPT (local disk or Supabase bucket) into memory for python-pptx."""
    import io
    with field_file.storage.open(field_file.name, 'rb') as fh:
        return io.BytesIO(fh.read())


def extract_slides_from_pptx(pptx_path_or_stream):
    """Reads every slide of a .pptx and returns title, bullets, notes, code and category."""
    from pptx import Presentation   # imported here so the whole service still loads without python-pptx

    prs = Presentation(pptx_path_or_stream)
    extracted_slides = []

    for idx, slide in enumerate(prs.slides):
        slide_number = idx + 1
        slide_title = ""
        slide_bullets = []
        speaker_notes = ""

        title_shape = slide.shapes.title
        if title_shape is not None and title_shape.has_text_frame and title_shape.text.strip():
            slide_title = title_shape.text.strip()

        for shape in slide.shapes:
            if title_shape is not None and shape == title_shape:
                continue
            for txt in extract_text_from_shape(shape):
                if not slide_title and len(txt) < 80:
                    slide_title = txt
                elif txt:
                    slide_bullets.append(txt)

        if not slide_title:
            slide_title = f"Slide {slide_number}: Key Concepts"

        try:
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                speaker_notes = slide.notes_slide.notes_text_frame.text.strip()
        except Exception:
            speaker_notes = ""

        code_snippet = ""
        for bullet in slide_bullets:
            if any(sym in bullet for sym in ["def ", "class ", "import ", "const ", "function", "var ", "{", "}", "SELECT ", "<div>"]):
                code_snippet = bullet
                break

        raw_text = f"Title: {slide_title}\n" + "\n".join(slide_bullets)
        if speaker_notes:
            raw_text += f"\nNotes: {speaker_notes}"

        category = "Concept"
        t = slide_title.lower()
        if idx == 0 or "welcome" in t or "overview" in t or "introduction" in t:
            category = "Overview"
        elif "case study" in t or "industry" in t or "scenario" in t:
            category = "Case Study"
        elif "code" in t or "implementation" in t or "syntax" in t or code_snippet:
            category = "Code"
        elif "pitfall" in t or "best practice" in t or "tip" in t:
            category = "Pro Tips"
        elif "assignment" in t or "lab" in t or "challenge" in t or "exercise" in t:
            category = "Lab Challenge"
        elif "summary" in t or "conclusion" in t or "takeaway" in t:
            category = "Summary"

        extracted_slides.append({
            'slide_number': slide_number,
            'title': slide_title,
            'bullet_points': slide_bullets,
            'raw_text': raw_text,
            'speaker_notes': speaker_notes,
            'code_snippet': code_snippet,
            'slide_category': category,
        })

    return extracted_slides


def _extracted_to_slide(e):
    """Turns one extracted PPT slide into the slide dict used by the player."""
    bullets = list(e.get('bullet_points') or [])
    return {
        'slide_number': e.get('slide_number', 1),
        'type': 'concept',                       # generic renderer shows ALL bullets (+ code if any)
        'badge': str(e.get('slide_category', 'Concept')).upper(),
        'slide_category': e.get('slide_category', 'Concept'),
        'title': e.get('title', ''),
        'key_points': bullets,
        'bullet_points': bullets,
        'speaker_notes': e.get('speaker_notes', ''),
        'code_snippet': e.get('code_snippet', ''),
        'slide_text': e.get('raw_text', ''),
    }


# ==============================================================================
# 3. EXPLANATIONS (AI optional + deterministic fallback)
# ==============================================================================

_gemini_quota_exhausted = False


def generate_slide_explanation_with_gemini(slide_data, lesson_title, course_title=""):
    """Optional: explanation + real-world example from Gemini. Returns dict or None."""
    global _gemini_quota_exhausted
    if _gemini_quota_exhausted:
        return None

    api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = f"""
You are an elite university professor and master educator in {course_title or 'Computer Science and Technology'}.
Deliver an exhaustive, comprehensive academic lecture for the following slide to an eager student.

Lesson Title: {lesson_title}
Slide Number: {slide_data.get('slide_number', 1)}
Slide Title: {slide_data.get('title', '')}
Slide Content & Bullets:
{slide_data.get('raw_text', '')}

Your explanation must be easy-to-understand, engaging, deeply informative, and directly applicable.
Respond in valid JSON format with exactly these four keys:
{{
  "concept_explanation": "A friendly, crystal-clear 2-3 paragraph explanation of the core concepts on this slide. Use simple language without unnecessary academic jargon.",
  "real_world_example": "A concrete, real-world industry scenario (e.g., Netflix streaming optimization, Spotify playlist syncing, Amazon checkout scale, Uber dispatch, or Stripe payment safety) showing how this concept works in real life.",
  "key_takeaway": "A concise, memorable 1-2 sentence golden takeaway rule for the student.",
  "spoken_narration": "A comprehensive, highly detailed spoken lecture narration of 300 to 420 words (about 2 to 3 minutes of spoken audio). Deeply explain the why and how, walk through the mechanics, elaborate on the real-world case with concrete details, discuss common pitfalls, and conclude with the golden takeaway. Do NOT use bullet points, markdown stars, or code syntax in the narration."
}}
"""
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        if response and response.text:
            return json.loads(response.text)
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Quota exceeded" in err_str:
            _gemini_quota_exhausted = True
            logger.info("Gemini quota exhausted (429); using deterministic generator.")
        else:
            logger.warning(f"Gemini slide explanation generation failed: {e}")
    return None


_DOMAINS = [
    {
        "keys": ["database", "sql", "query", "orm", "index", "postgres", "table"],
        "example_title": "Production Database Optimization (e.g. Amazon / Instagram Scale)",
        "example_desc": (
            "Consider an online shopping platform like Amazon during Black Friday. When millions of shoppers search for items simultaneously, "
            "running unoptimized queries or scanning full tables causes severe latency spikes and connection pool starvation. By implementing "
            "the structured principles on this slide, such as composite relational indexing, cached querysets, and atomic transaction boundaries, "
            "the server retrieves customer orders in single-digit milliseconds without locking the underlying database tables or dropping customer carts."
        ),
        "mechanics": (
            "Under the hood, relational database engines rely on balanced B-Tree index structures to minimize expensive disk I/O operations. "
            "When a query filter maps directly to an index page, the database traverses the tree in logarithmic time, jumping directly to the data blocks. "
            "However, if developers write queries with functions wrapped around indexed columns or fail to declare appropriate foreign key constraints, "
            "the query planner degrades to a full sequential table scan, multiplying CPU cycles and stalling other concurrent transactions."
        ),
        "pitfalls": (
            "A critical pitfall in production ORMs is the notorious N-plus-one query problem, where iterating over a queryset triggers dozens of "
            "redundant roundtrips to the database. Always profile queries with EXPLAIN ANALYZE and leverage eager loading techniques."
        ),
        "takeaway": "Always design queries to touch only necessary columns and leverage index-backed lookups to avoid catastrophic production bottlenecks.",
    },
    {
        "keys": ["api", "rest", "endpoint", "http", "request", "response", "json", "header"],
        "example_title": "Real-Time Microservices (e.g. Uber / Food Delivery Dispatch)",
        "example_desc": (
            "Imagine Uber matching a rider with the nearest driver in fractions of a second. The rider's mobile app sends a structured JSON payload to the backend API. "
            "The server authenticates the session token, validates input parameters, routes the request through an API gateway, and returns driver coordinates. "
            "The principles shown on this slide ensure API contracts remain backwards-compatible, resilient against dropped network packets, and safe from malformed payloads."
        ),
        "mechanics": (
            "Modern distributed architectures rely on standard HTTP verbs and semantic status codes to enforce explicit contracts between independent services. "
            "GET, PUT, and DELETE operations must remain idempotent, meaning repeating the request under unstable mobile network conditions causes no unwanted side effects. "
            "POST requests, which initiate state transitions, require idempotency keys so that duplicated cellular packets do not double-charge a user's wallet."
        ),
        "pitfalls": (
            "Common beginner mistakes include returning generic HTTP 200 responses with embedded error strings, or leaking sensitive internal stack traces "
            "in unhandled exception handlers. Always return standardized JSON error envelopes with actionable error codes."
        ),
        "takeaway": "An API is a binding contract between systems: validate strictly on arrival, process idempotently, and return standard status codes.",
    },
    {
        "keys": ["security", "auth", "token", "password", "jwt", "csrf", "xss", "permission"],
        "example_title": "Enterprise Banking Security (e.g. Stripe / Revolut Transactions)",
        "example_desc": (
            "Think of a banking application handling high-stakes funds transfer. A malicious attacker might attempt cross-site request forgery, SQL injection, "
            "or session hijacking. By implementing strict role-based access control, cryptographic hashing with salt, and automated token expiration as highlighted "
            "in this slide, the system verifies cryptographic identity on every privileged action, ensuring that unauthorized parties can never tamper with account ledgers."
        ),
        "mechanics": (
            "Security in modern computing follows the principle of defense in depth. Raw passwords must never be stored in plain text or reversible encryption; "
            "instead, slow cryptographic algorithms like Argon2 or bcrypt incorporate adaptive work factors to neutralize brute-force GPU attacks. "
            "Stateless authentication tokens like JSON Web Tokens include cryptographically signed payloads, allowing decentralized microservices to verify claims "
            "without hammering a centralized session store, while short expiration windows limit the blast radius of compromised tokens."
        ),
        "pitfalls": (
            "Never store authentication secrets, API keys, or private tokens in client-side code repositories or local browser storage. Enforce HTTPS everywhere "
            "and apply HttpOnly, Secure, and SameSite cookie attributes on all session identifiers."
        ),
        "takeaway": "Never trust client-side input: enforce cryptographic authentication and least-privilege permissions on every backend route.",
    },
    {
        "keys": ["state", "react", "component", "frontend", "dom", "ui", "view", "render"],
        "example_title": "Interactive User Interface (e.g. Netflix Video Browser / YouTube Feed)",
        "example_desc": (
            "When scrolling through Netflix, thumbnail images load lazily, category carousels scroll smoothly, and your watchlist updates instantly. "
            "The architecture detailed on this slide ensures the UI state remains unidirectional and predictable. When user actions trigger changes, "
            "only the necessary sub-tree re-renders, preventing UI stuttering and delivering a frictionless 60 FPS user experience."
        ),
        "mechanics": (
            "Client-side user interfaces are essentially mathematical projections of state into DOM trees. When state changes, modern rendering engines "
            "perform virtual DOM reconciliation to compute the minimal set of native browser mutations required. By lifting state to common ancestors "
            "and treating state objects as immutable, developers ensure that child components re-render only when their explicit properties change, "
            "preventing layout thrashing and unnecessary garbage collection pauses."
        ),
        "pitfalls": (
            "A frequent performance mistake is storing derived values in state or mutating objects directly in memory, which breaks shallow change detection. "
            "Always derive computed values during render and maintain clean component lifecycle boundaries to avoid memory leaks."
        ),
        "takeaway": "Keep state minimal, derive computed values rather than duplicating them, and separate presentation components from business logic.",
    },
    {
        "keys": ["algorithm", "data structure", "tree", "graph", "hash", "complexity", "big o"],
        "example_title": "High-Speed Route Computation (e.g. Google Maps Navigation)",
        "example_desc": (
            "When you search for directions on Google Maps, the engine analyzes millions of road intersections across the country. "
            "A naive search algorithm would take hours to evaluate every route. By utilizing the optimal data structures and asymptotic algorithmic "
            "approaches shown here, the system prunes unviable paths instantly and returns the fastest route in fractions of a second."
        ),
        "mechanics": (
            "Algorithmic efficiency is defined by asymptotic growth rates in time and memory consumption. Selecting a hash table provides expected constant-time "
            "lookups through efficient mathematical distribution across buckets, whereas tree-based structures maintain sorted order with logarithmic time guarantees. "
            "When traversing complex networks of nodes, algorithms like Dijkstra's leverage priority queues to greedily explore the most promising paths first, "
            "reducing the exponential search space down to manageable polynomial bounds."
        ),
        "pitfalls": (
            "Do not confuse worst-case time complexity with average-case behavior. A hash map degrades to linear time if poorly chosen keys cause high collision rates. "
            "Always consider input distribution and memory cache locality when choosing data structures for critical performance paths."
        ),
        "takeaway": "Choose the right data structure for the access pattern: the computational complexity you choose dictates your production ceiling.",
    },
]

_DEFAULT_DOMAIN = {
    "example_title": "Production Cloud Platform Architecture (e.g. High-Traffic Web Services)",
    "example_desc": (
        "In modern cloud systems handling thousands of concurrent users, the principles in '{title}' serve as the foundation of reliability. "
        "By breaking monolithic complexity down into modular components, engineering teams can iterate rapidly, isolate points of failure, "
        "and scale individual service tiers horizontally as user traffic expands."
    ),
    "mechanics": (
        "Cloud-native software design relies on clean boundary isolation, stateless worker processes, and asynchronous messaging queues. "
        "When user requests arrive at the edge, load balancers distribute connections across healthy compute nodes. By delegating long-running "
        "background tasks to message queues, the synchronous request-response pipeline remains responsive, while distributed telemetry "
        "and health checks provide instant visibility into latency percentiles and error budgets."
    ),
    "pitfalls": (
        "Avoid introducing tight couplings between microservices that result in distributed monoliths. Always design systems to degrade gracefully "
        "when third-party dependencies fail, utilizing circuit breakers and exponential backoff retry patterns."
    ),
    "takeaway": "Mastering {title} empowers you to build robust, maintainable systems that scale smoothly under production demand.",
}


def generate_dynamic_fallback_explanation(slide_data, lesson_title, course_title=""):
    """Deterministic explanation + real-world example + spoken narration (no AI needed)."""
    title = slide_data.get('title', 'Core Concept')
    bullets = slide_data.get('bullet_points', []) or []
    slide_num = slide_data.get('slide_number', 1)

    lower_ctx = f"{title} {' '.join(str(b) for b in bullets)} {lesson_title}".lower()

    domain = None
    for d in _DOMAINS:
        if any(k in lower_ctx for k in d["keys"]):
            domain = d
            break
    if domain is None:
        domain = {k: (v.format(title=title) if isinstance(v, str) else v) for k, v in _DEFAULT_DOMAIN.items()}

    example_title = domain["example_title"]
    example_desc = domain["example_desc"]
    mechanics_detail = domain["mechanics"]
    pitfalls = domain["pitfalls"]
    takeaway = domain["takeaway"]

    if bullets:
        b0 = str(bullets[0])
        parts = [f"First, examine that {b0}" if b0.endswith('.') else f"First, examine how {b0}."]
        if len(bullets) > 1:
            b1 = str(bullets[1])
            parts.append(f"Furthermore, {b1}" if b1.endswith('.') else f"Furthermore, notice that {b1}.")
        if len(bullets) > 2:
            b2 = str(bullets[2])
            parts.append(f"Finally, {b2}" if b2.endswith('.') else f"Finally, ensure that {b2}.")
    else:
        parts = [f"This slide establishes key foundations for {lesson_title}, emphasizing practical implementation techniques and clean architectural design."]

    concept_text = (
        f"In this slide, titled '{title}', we focus directly on core architectural mechanics. "
        + " ".join(parts)
        + " Understanding these foundational points is essential before moving to hands-on deployment."
    )

    spoken_narration = (
        f"Welcome to Slide {slide_num}: {clean_text_for_tts(title)}. "
        f"In today's lecture on {clean_text_for_tts(lesson_title)}, this slide represents an essential theoretical and practical milestone. "
        f"{clean_text_for_tts(concept_text)} "
        f"Let us dissect the underlying engineering mechanics in detail. {clean_text_for_tts(mechanics_detail)} "
        f"To illustrate how this functions in industry scale, consider the following real-world scenario: {clean_text_for_tts(example_desc)} "
        f"Notice how the senior engineering team resolved the operational challenge not by adding arbitrary complexity, "
        f"but by strictly applying the fundamental patterns detailed on this slide. "
        f"As you write code for today's challenge, keep these practical guidelines in mind. {clean_text_for_tts(pitfalls)} "
        f"To conclude this slide, anchor your understanding around this golden takeaway rule: {clean_text_for_tts(takeaway)}"
    )

    return {
        "concept_explanation": concept_text,
        "real_world_example": f"{example_title}: {example_desc}",
        "key_takeaway": takeaway,
        "spoken_narration": spoken_narration,
    }


def _typed_explanation(s):
    """Uses the real content of generated slides (case study, code, tips ...) as the explanation."""
    t = str(s.get('type', '')).lower()
    out = {}
    try:
        if t == 'overview':
            out = {'concept': s.get('teacher_briefing') or '', 'takeaway': s.get('teacher_core_rule') or ''}
        elif t == 'case_study':
            example = " ".join(x for x in [s.get('company_context'), s.get('solution_architecture'), s.get('key_metric_impact')] if x)
            out = {'concept': s.get('problem_statement') or '', 'example': example, 'takeaway': s.get('key_metric_impact') or ''}
        elif t == 'code':
            obs = _as_list(s.get('teacher_observations'))
            out = {'concept': _join(obs), 'takeaway': str(obs[-1]) if obs else ''}
        elif t == 'tips_and_pitfalls':
            mistakes, tips = _join(s.get('common_mistakes')), _join(s.get('pro_tips'))
            tip_list = _as_list(s.get('pro_tips'))
            out = {
                'concept': f"Common beginner mistakes: {mistakes}" if mistakes else '',
                'example': f"Teacher pro tips: {tips}" if tips else '',
                'takeaway': str(tip_list[0]) if tip_list else '',
            }
        elif t == 'assignment':
            out = {'concept': _join(s.get('assignment_tasks')), 'takeaway': s.get('next_day_preview') or ''}
        elif t == 'complexity':
            out = {
                'concept': f"Time complexity: {s.get('time_complexity', '')}. Space complexity: {s.get('space_complexity', '')}.",
                'example': f"Cache locality: {s.get('cache_locality', '')}. Trade-offs: {_join(s.get('trade_offs'))}",
            }
        elif t == 'concepts':
            names = []
            for k in ('concept_1', 'concept_2', 'concept_3'):
                c = s.get(k)
                if isinstance(c, dict):
                    names.append(f"{c.get('name', '')}: {_join(c.get('points'))}")
            for c in _as_list(s.get('concepts')):
                if isinstance(c, dict):
                    names.append(f"{c.get('name', '')}: {_join(c.get('points'))}")
            out = {'concept': " ".join(names)}
        elif t == 'architecture':
            out = {'concept': _join(s.get('architecture_layers')) or _join(s.get('invariants')), 'example': s.get('data_flow') or '',
                   'takeaway': _join(s.get('key_invariants'))}
        elif t == 'verification':
            out = {'concept': _join(s.get('checklist')), 'takeaway': s.get('next_milestone') or ''}
    except Exception as e:
        logger.debug(f"typed explanation failed: {e}")
        out = {}
    return {k: v for k, v in out.items() if v and str(v).strip()}


def build_slide_explanation(slide, slide_data, lesson_title, course_title="", use_ai=False):
    """Returns concept/example/takeaway/spoken narration for one slide."""
    typed = _typed_explanation(slide)
    ai = generate_slide_explanation_with_gemini(slide_data, lesson_title, course_title) if use_ai else None
    if not (isinstance(ai, dict) and ai.get("concept_explanation")):
        ai = None
    fb = generate_dynamic_fallback_explanation(slide_data, lesson_title, course_title)

    concept = (ai or {}).get("concept_explanation") or typed.get('concept') or fb["concept_explanation"]
    example = (ai or {}).get("real_world_example") or typed.get('example') or fb["real_world_example"]
    takeaway = (ai or {}).get("key_takeaway") or typed.get('takeaway') or fb["key_takeaway"]
    spoken = (ai or {}).get("spoken_narration") or fb["spoken_narration"]

    formatted = (
        f"### 💡 Core Concept Explanation\n{concept}\n\n"
        f"### 🌟 Real-World Practical Example\n{example}\n\n"
        f"### 📌 Key Takeaway\n*{takeaway}*"
    )
    return {
        "formatted_explanation": formatted,
        "concept_explanation": concept,
        "real_world_example": example,
        "key_takeaway": takeaway,
        "spoken_narration": clean_text_for_tts(spoken),
    }


def generate_slide_explanation(slide_data, lesson_title, course_title="", use_ai=True):
    """Backward compatible entry point (Gemini first, deterministic fallback)."""
    return build_slide_explanation({}, slide_data, lesson_title, course_title, use_ai=use_ai)


# ==============================================================================
# 4. TEXT-TO-VOICE  (edge-tts first, gTTS fallback, always in background)
# ==============================================================================

_AUDIO_LOCK = threading.Lock()
_AUDIO_JOBS = set()


def _audio_dir(lesson_id):
    return os.path.join(settings.MEDIA_ROOT, 'lectures', f'lesson_{lesson_id}')


def _audio_path(lesson_id, slide_no):
    return os.path.join(_audio_dir(lesson_id), f'slide_{slide_no}.mp3')


def _audio_url(lesson_id, slide_no):
    return f"{settings.MEDIA_URL}lectures/lesson_{lesson_id}/slide_{slide_no}.mp3"


def _audio_ok(path, words):
    """True only if the mp3 exists and is long enough for the narration (not truncated)."""
    try:
        if not os.path.exists(path):
            return False
        return os.path.getsize(path) >= max(1000, int(words * AUDIO_BYTES_PER_WORD))
    except OSError:
        return False


def _clear_audio(lesson_id):
    folder = _audio_dir(lesson_id)
    if not os.path.isdir(folder):
        return
    for name in os.listdir(folder):
        if name.startswith('slide_') and name.endswith('.mp3'):
            try:
                os.remove(os.path.join(folder, name))
            except OSError:
                pass


def synthesize_speech(text, out_path):
    """Converts the FULL text to an mp3 file. Returns True on success."""
    text = clean_text_for_tts(text)
    if len(text) < 10:
        text = "This slide covers key principles and practical steps for today's lesson."
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp_path = out_path + ".part"

    def _finish():
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1000:
            os.replace(tmp_path, out_path)
            return True
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False

    # 1) edge-tts: natural voice, fast, no length limit
    try:
        import asyncio
        import edge_tts

        async def _run():
            communicate = edge_tts.Communicate(text, 'en-US-ChristopherNeural', rate='+5%')
            await communicate.save(tmp_path)

        asyncio.run(_run())
        if _finish():
            return True
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"edge-tts failed, trying gTTS: {e}")

    # 2) gTTS: splits long text internally, slower but reliable
    try:
        from gtts import gTTS
        gTTS(text=text, lang='en', slow=False).save(tmp_path)
        if _finish():
            return True
    except ImportError:
        logger.error("Neither edge-tts nor gTTS is installed. Run: pip install edge-tts gTTS")
    except Exception as e:
        logger.warning(f"gTTS audio synthesis failed: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
    return False


def generate_slide_audio_gtts(spoken_text, output_mp3_path):
    """Backward compatible name. Now converts the WHOLE text (no 160 character cut)."""
    return synthesize_speech(spoken_text, output_mp3_path)


def _start_audio_thread(owner_id, jobs):
    """Creates the mp3 files one by one in a daemon thread (never blocks the page)."""
    if not jobs:
        return
    with _AUDIO_LOCK:
        if owner_id in _AUDIO_JOBS:
            return
        _AUDIO_JOBS.add(owner_id)

    def _run():
        try:
            for text, path in jobs:
                try:
                    synthesize_speech(text, path)
                except Exception as err:
                    logger.warning(f"Background audio error: {err}")
        finally:
            with _AUDIO_LOCK:
                _AUDIO_JOBS.discard(owner_id)

    threading.Thread(target=_run, daemon=True, name=f"alvix-audio-{owner_id}").start()


# ==============================================================================
# 5. DECK BUILDING
# ==============================================================================

def is_placeholder_deck(pdata):
    """True for the old hard-coded 'sample' deck that earlier versions saved by mistake."""
    if not isinstance(pdata, dict):
        return False
    if pdata.get('source') == 'placeholder':
        return True
    if pdata.get('source'):
        return False
    slides = pdata.get('slides_list') or []
    return bool(slides) and str(slides[0].get('title', '')).startswith(PLACEHOLDER_TITLE_PREFIX)


def is_presentation_complete(pdata):
    """Deck is ready: real slides, each with explanation + narration (audio is handled separately)."""
    if not isinstance(pdata, dict) or is_placeholder_deck(pdata):
        return False
    slides = pdata.get('slides_list') or []
    if not slides:
        return False
    return all(s.get('concept_explanation') and s.get('narration') for s in slides)


def extract_slide_bullets(s):
    """Finds the bullet points of ANY slide type."""
    for key in ('key_points', 'bullet_points', 'learning_objectives', 'trade_offs', 'assignment_tasks'):
        vals = _as_list(s.get(key))
        if vals:
            return [str(v) for v in vals]
    if s.get('invariants') or s.get('key_invariants'):
        return [f"System Invariant: {x}" for x in _as_list(s.get('invariants')) + _as_list(s.get('key_invariants'))]
    if s.get('architecture_layers'):
        return [str(x) for x in _as_list(s.get('architecture_layers'))]
    if s.get('checklist'):
        return [f"Verification: {x}" for x in _as_list(s.get('checklist'))]
    pts = []
    for c in _as_list(s.get('concepts')) + [s.get(k) for k in ('concept_1', 'concept_2', 'concept_3')]:
        if isinstance(c, dict):
            for p in _as_list(c.get('points')):
                pts.append(f"{c.get('name', '')}: {p}" if c.get('name') else str(p))
        elif isinstance(c, str) and c.strip():
            pts.append(c)
    if pts:
        return pts
    pts = [f"Pitfall: {m}" for m in _as_list(s.get('common_mistakes'))] + [f"Pro Tip: {t}" for t in _as_list(s.get('pro_tips'))]
    if pts:
        return pts
    if s.get('pipeline_flow'):
        flow = s.get('pipeline_flow')
        return [f"Pipeline Stage: {x}" for x in (flow if isinstance(flow, list) else [flow])]
    if s.get('questions'):
        out = []
        for i, q in enumerate(_as_list(s.get('questions')), start=1):
            if isinstance(q, dict):
                out.append(f"Q{i}: {q.get('question') or q.get('text') or ''}")
        if out:
            return out
    return [
        f"Master foundational mechanics for {s.get('title', 'this topic')}",
        "Review execution trace and state invariants",
        "Apply production engineering best practices",
    ]


def _placeholder_slides(lesson):
    """Last resort only (when both the PPT file and the generator fail). Never saved to the database."""
    t = lesson.title
    items = [
        ("OVERVIEW", f"Overview: {t}", ["Understand the core objectives", "Explore practical patterns", "Review real-world constraints"]),
        ("CONCEPT", "Core Concepts", ["State and lifecycle", "Input validation", "Execution flow"]),
        ("CASE STUDY", "Real-World Case Study", ["High-concurrency production load", "Defensive fault boundaries", "Scalability under traffic"]),
        ("CODE", "Implementation Blueprint", ["Syntax walkthrough", "Defensive error handling", "Idempotent processing"]),
        ("PRO TIPS", "Best Practices & Pitfalls", ["Common beginner mistakes", "Memory leak prevention", "Verification checklist"]),
        ("LAB CHALLENGE", "Hands-On Lab Challenge", ["Challenge requirements", "Testing benchmarks", "Daily milestone checklist"]),
        ("SUMMARY", "Summary & Takeaways", ["Review the core rules", "Prepare for tomorrow", "Next level roadmap"]),
    ]
    return [{"slide_number": i, "type": "concept", "badge": b, "title": ti, "key_points": pts}
            for i, (b, ti, pts) in enumerate(items, start=1)]


def _collect_slides(lesson):
    """
    Finds the slides for this lesson. Returns (slides_list, source).
    Order: saved deck  ->  uploaded .pptx file  ->  the generator used by 'Download PPT'  ->  placeholder.
    """
    pdata = lesson.presentation_data if isinstance(lesson.presentation_data, dict) else None

    if pdata and is_placeholder_deck(pdata):
        logger.warning(f"Lesson {lesson.id}: old sample deck found, regenerating real slides.")
        lesson.presentation_data = None
        try:
            lesson.save(update_fields=['presentation_data'])
        except Exception:
            pass
        pdata = None

    if pdata and pdata.get('slides_list') and len(pdata['slides_list']) >= 10:
        return list(pdata['slides_list']), (pdata.get('source') or 'existing')

    # Uploaded teacher PPT that was never processed
    try:
        if lesson.ppt_file and lesson.ppt_file.storage.exists(lesson.ppt_file.name):
            extracted = extract_slides_from_pptx(_ppt_stream(lesson.ppt_file))
            if extracted:
                return [_extracted_to_slide(e) for e in extracted], 'uploaded_ppt'
    except Exception as e:
        logger.error(f"Lesson {lesson.id}: could not read uploaded PPT: {e}", exc_info=True)

    # Same generator the Download PPT button uses (so player and PPT always match)
    try:
        from .ppt_generator import get_or_generate_lesson_lecture   # <-- this import was missing before
        data = get_or_generate_lesson_lecture(lesson, ensure_audio=False)
        slides = data.get('slides_list') if isinstance(data, dict) else None
        if slides:
            return list(slides), 'generated'
        logger.error(f"Lesson {lesson.id}: generator returned no slides.")
    except Exception as e:
        logger.error(f"Lesson {lesson.id}: slide generation failed: {e}", exc_info=True)

    return _placeholder_slides(lesson), 'placeholder'


def _pick_narration(s, explanation):
    for cand in (s.get('narration'), s.get('teacher_narration'), s.get('speaker_notes')):
        if cand and _word_count(cand) >= MIN_NARRATION_WORDS:
            return clean_text_for_tts(cand)
    spoken = explanation.get('spoken_narration')
    if spoken:
        return spoken
    return clean_text_for_tts(f"{s.get('title', '')}. {explanation.get('concept_explanation', '')} {explanation.get('key_takeaway', '')}")


def build_slide_payload(s, idx, lesson, course_title="", use_ai=False):
    """One slide for storage / player. Keeps ALL original fields and adds the explanation fields."""
    title = str(s.get('title') or f"Slide {idx}")
    bullets = [str(b) for b in extract_slide_bullets(s)]
    category = str(s.get('badge') or s.get('slide_category') or 'Concept')
    code_snippet = s.get('code_snippet') or ''
    raw_text = s.get('slide_text') or "\n".join(bullets) or title

    slide_data = {
        'slide_number': idx, 'title': title, 'bullet_points': bullets,
        'raw_text': raw_text, 'slide_category': category, 'code_snippet': code_snippet,
    }

    if s.get('concept_explanation') and s.get('real_world_example') and s.get('key_takeaway'):
        expl = {
            'concept_explanation': s['concept_explanation'],
            'real_world_example': s['real_world_example'],
            'key_takeaway': s['key_takeaway'],
            'formatted_explanation': s.get('explanation') or (
                f"### 💡 Core Concept Explanation\n{s['concept_explanation']}\n\n"
                f"### 🌟 Real-World Practical Example\n{s['real_world_example']}\n\n"
                f"### 📌 Key Takeaway\n*{s['key_takeaway']}*"),
            'spoken_narration': '',
        }
    else:
        expl = build_slide_explanation(s, slide_data, lesson.title, course_title, use_ai=use_ai)

    narration = _pick_narration(s, expl)

    item = dict(s)
    item.update({
        'slide_number': idx,
        'type': s.get('type') or ('code' if code_snippet else 'concept'),
        'badge': category.upper(),
        'title': title,
        'key_points': bullets,
        'bullet_points': bullets,
        'speaker_notes': narration,
        'narration': narration,
        'explanation': expl['formatted_explanation'],
        'concept_explanation': expl['concept_explanation'],
        'real_world_example': expl['real_world_example'],
        'key_takeaway': expl['key_takeaway'],
        'code_snippet': code_snippet,
        'slide_text': raw_text,
    })
    return item


def _persist_deck(lesson, payload):
    """Saves the deck in DailyLesson.presentation_data and PresentationSlide rows."""
    try:
        with transaction.atomic():
            PresentationSlide.objects.filter(daily_lesson=lesson).delete()
            rows = []
            for s in payload['slides_list']:
                rows.append(PresentationSlide(
                    daily_lesson=lesson,
                    course_level=lesson.course_level,
                    slide_number=s['slide_number'],
                    title=str(s['title'])[:255],
                    bullet_points=s.get('bullet_points', []),
                    speaker_notes=s.get('narration', ''),
                    code_snippet=s.get('code_snippet', '') or '',
                    slide_category=str(s.get('badge', 'Concept'))[:50],
                    slide_text=s.get('slide_text', '') or '',
                    explanation=s.get('explanation', '') or '',
                    audio_file=s.get('audio_url', '') or '',
                ))
            PresentationSlide.objects.bulk_create(rows)
            lesson.presentation_data = payload
            lesson.save(update_fields=['presentation_data'])
        return True
    except Exception as e:
        logger.error(f"Lesson {lesson.id}: could not save presentation: {e}", exc_info=True)
        return False


def generate_and_save_admin_lesson_ppt_and_audio(lesson, generate_audio=True, use_ai=False, slides_override=None, source=None):
    """
    Master pipeline for ONE lesson:
    slides (real PPT / generated deck) -> explanations -> narration -> save -> mp3 files in background.
    """
    course_title = _course_title(lesson)

    if slides_override is not None:
        slides_list, src = list(slides_override), (source or 'uploaded_ppt')
    else:
        slides_list, src = _collect_slides(lesson)

    persist = (src != 'placeholder')
    if src == 'existing':
        src = 'generated'

    payload_slides, audio_jobs = [], []
    for idx, s in enumerate(slides_list, start=1):
        item = build_slide_payload(s, idx, lesson, course_title, use_ai=use_ai)
        mp3 = _audio_path(lesson.id, idx)
        if _audio_ok(mp3, _word_count(item['narration'])):
            item['audio_url'] = _audio_url(lesson.id, idx)
        else:
            item['audio_url'] = ''
            if generate_audio and persist:
                audio_jobs.append((item['narration'], mp3))
        payload_slides.append(item)

    payload = {
        'lesson_id': lesson.id,
        'lesson_title': lesson.title,
        'course_title': course_title,
        'day_number': lesson.day_number,
        'source': src,
        'total_slides': len(payload_slides),
        'slides_list': payload_slides,
    }

    if persist:
        _persist_deck(lesson, payload)
    _start_audio_thread(lesson.id, audio_jobs)

    logger.info(f"Lesson {lesson.id}: deck ready ({len(payload_slides)} slides, source={src}).")
    return payload


def _sync_audio(lesson, pdata, generate_audio=True):
    """Fills audio_url for mp3 files that now exist and starts creating the missing ones."""
    changed, jobs = False, []
    for idx, s in enumerate(pdata.get('slides_list', []), start=1):
        mp3 = _audio_path(lesson.id, idx)
        words = _word_count(s.get('narration'))
        url = _audio_url(lesson.id, idx) if _audio_ok(mp3, words) else ''
        if s.get('audio_url', '') != url:
            s['audio_url'] = url
            changed = True
        if not url and generate_audio and words:
            jobs.append((s['narration'], mp3))

    if changed:
        try:
            lesson.presentation_data = pdata
            lesson.save(update_fields=['presentation_data'])
            for idx, s in enumerate(pdata.get('slides_list', []), start=1):
                PresentationSlide.objects.filter(daily_lesson=lesson, slide_number=idx).update(audio_file=s.get('audio_url', ''))
        except Exception as e:
            logger.warning(f"Lesson {lesson.id}: could not save audio urls: {e}")

    _start_audio_thread(lesson.id, jobs)
    return pdata


# ==============================================================================
# 6. PLAYER PAYLOAD (what daily_lesson.html receives)
# ==============================================================================

def normalize_slide_for_player(slide):
    """
    Returns a COPY of the slide in the exact shape the JavaScript slide player expects.
    (The stored data is not changed, so 'Download PPT' keeps working.)
    """
    s = copy.deepcopy(slide)
    t = str(s.get('type', '')).lower()

    if t == 'concepts' and not s.get('concepts'):
        cs = [s[k] for k in ('concept_1', 'concept_2', 'concept_3') if isinstance(s.get(k), dict)]
        if cs:
            s['concepts'] = cs

    if t == 'architecture':
        inv = [str(x) for x in _as_list(s.get('architecture_layers')) + _as_list(s.get('invariants')) + _as_list(s.get('key_invariants'))]
        s['invariants'] = inv
        flow = s.get('pipeline_flow') or s.get('data_flow') or ''
        if isinstance(flow, str):
            stages = [p.strip() for p in re.split(r'→|->|\n', flow) if p.strip()]
        else:
            stages = [str(p) for p in _as_list(flow)]
        s['pipeline_flow'] = stages

    if t == 'complexity':
        s['trade_offs'] = [str(x) for x in _as_list(s.get('trade_offs'))]

    for key in ('learning_objectives', 'common_mistakes', 'pro_tips', 'assignment_tasks',
                'success_checklist', 'checklist', 'teacher_observations'):
        if key in s:
            s[key] = [str(x) for x in _as_list(s.get(key))]

    s['key_points'] = [str(x) for x in _as_list(s.get('key_points'))]
    s['title'] = str(s.get('title') or '')
    s['narration'] = str(s.get('narration') or '')
    s['audio_url'] = s.get('audio_url') or ''
    return s


def build_player_payload(pdata):
    out = {k: v for k, v in pdata.items() if k != 'slides_list'}
    slides = [normalize_slide_for_player(x) for x in pdata.get('slides_list', [])]
    out['slides_list'] = slides
    out['total_slides'] = len(slides)
    return out


def ensure_lesson_slides_and_explanations(lesson, generate_audio=True, use_ai=False):
    """
    Called by the lesson page. Returns the deck for the slide player.
    * A student lesson uses the admin (canonical) lesson of the same level/day, so every student
      sees the same PPT slides.
    * Everything is created once and then reused (fast for the next students).
    """
    owner = lesson
    if lesson.generated_course_id and lesson.course_level_id:
        canonical = DailyLesson.objects.filter(
            course_level=lesson.course_level,
            day_number=lesson.day_number,
            generated_course__isnull=True,
        ).first()
        if canonical:
            owner = canonical

    pdata = owner.presentation_data
    if is_presentation_complete(pdata):
        pdata = _sync_audio(owner, pdata, generate_audio=generate_audio)
    else:
        pdata = generate_and_save_admin_lesson_ppt_and_audio(owner, generate_audio=generate_audio, use_ai=use_ai)

    # keep the student's own lesson in sync (also lets "Download PPT" use the same slides)
    if owner is not lesson and pdata.get('source') != 'placeholder':
        fields = []
        if lesson.presentation_data != pdata:
            lesson.presentation_data = pdata
            fields.append('presentation_data')
        if owner.ppt_file and lesson.ppt_file != owner.ppt_file:
            lesson.ppt_file = owner.ppt_file
            fields.append('ppt_file')
        if fields:
            try:
                lesson.save(update_fields=fields)
            except Exception as e:
                logger.warning(f"Could not sync lesson {lesson.id}: {e}")

    return build_player_payload(pdata)


# ==============================================================================
# 7. ADMIN PPT UPLOAD
# ==============================================================================

def process_lesson_ppt_upload(lesson, uploaded_file):
    """
    Admin uploads a teacher .pptx for a lesson:
    extract ALL slides -> explanation + example for each (AI if available) -> save -> voice in background.
    Upload it on the ADMIN lesson (generated_course empty): students read the slides from there.
    """
    lesson.ppt_file = uploaded_file
    lesson.save(update_fields=['ppt_file'])

    logger.info(f"Processing uploaded PPT for lesson {lesson.id} at {lesson.ppt_file.name}")

    extracted = extract_slides_from_pptx(_ppt_stream(lesson.ppt_file))
    if not extracted:
        raise ValueError("No slides could be extracted from the uploaded PowerPoint file.")

    _clear_audio(lesson.id)   # old mp3 files belong to the old PPT
    slides = [_extracted_to_slide(e) for e in extracted]

    payload = generate_and_save_admin_lesson_ppt_and_audio(
        lesson, generate_audio=True, use_ai=True, slides_override=slides, source='uploaded_ppt'
    )
    player = build_player_payload(payload)
    return {
        'success': True,
        'slides_count': len(player['slides_list']),
        'slides_list': player['slides_list'],
    }