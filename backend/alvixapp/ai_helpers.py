import os
import re
import json
import logging
import requests  # type: ignore
from django.conf import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


def get_gemini_api_key():
    """Retrieves the Gemini API key from environment variables or Django settings."""
    return os.environ.get('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', '')


def get_youtube_api_key():
    """Retrieves the YouTube Data API key from environment variables or Django settings."""
    return os.environ.get('YOUTUBE_API_KEY') or getattr(settings, 'YOUTUBE_API_KEY', '')


def log_ai_generation(user=None, item_type='unknown', item_id=None, model_used='gemini-2.5-flash', prompt='', response_json=None, is_validated=False):
    """Stores the prompt, model used, and validated response for every generated item."""
    try:
        from .models import AIGenerationLog
        return AIGenerationLog.objects.create(
            user=user if getattr(user, 'is_authenticated', False) else None,
            item_type=item_type,
            item_id=str(item_id) if item_id else None,
            model_used=model_used,
            prompt=prompt,
            response_json=response_json or {},
            is_validated=is_validated
        )
    except Exception as e:
        logger.error(f"Failed to record AI generation log: {e}")
        return None


def fetch_top_mentor_video(topic):
    """Fetches a top-viewed mentor video embed URL via YouTube Data API v3."""
    youtube_key = get_youtube_api_key()
    if not youtube_key or youtube_key == "PASTE_YOUR_YOUTUBE_KEY_HERE":
        return "https://www.youtube.com/embed/dQw4w9WgXcQ"

    query = f"{topic} tutorial full course"
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={query}&type=video&order=viewCount&key={youtube_key}"
    
    try:
        response = requests.get(url, timeout=8).json()
        items = response.get('items', [])
        if items:
            video_id = items[0]['id']['videoId']
            return f"https://www.youtube.com/embed/{video_id}"
    except Exception as e:
        logger.error(f"YouTube Fetch Error: {e}")
        
    return "https://www.youtube.com/embed/dQw4w9WgXcQ"  # Fallback video


def generate_assignment_and_quiz(lesson_title, lesson_content, user=None):
    """
    Generates practical assignments and multiple-choice questions using Gemini AI.
    Strictly returns JSON only and validates the response before saving/returning.
    Stores the prompt and model used for this generated item.
    """
    api_key = get_gemini_api_key()
    model_name = 'gemini-2.5-flash'
    prompt = f"""
    Based on the lesson topic '{lesson_title}' and explanation '{lesson_content[:500]}':
    1. Provide 1 practical assignment task.
    2. Provide 3 Multiple Choice Questions (MCQs) with options A, B, C, D and the correct answer.
    
    Return STRICT JSON ONLY matching this format:
    {{
        "assignment": "Assignment question text here...",
        "quiz": [
            {{"id": 1, "question": "Q1 text", "options": ["Option A", "Option B", "Option C", "Option D"], "answer": "Option A"}},
            {{"id": 2, "question": "Q2 text", "options": ["Option A", "Option B", "Option C", "Option D"], "answer": "Option B"}},
            {{"id": 3, "question": "Q3 text", "options": ["Option A", "Option B", "Option C", "Option D"], "answer": "Option C"}}
        ]
    }}
    """
    
    if api_key and api_key != "PASTE_YOUR_GEMINI_KEY_HERE":
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            cleaned_json = re.sub(r'```json\s*|```\s*', '', response.text).strip()
            data = json.loads(cleaned_json)

            # Strict validation
            if (
                isinstance(data, dict)
                and 'assignment' in data
                and isinstance(data['assignment'], str)
                and 'quiz' in data
                and isinstance(data['quiz'], list)
                and len(data['quiz']) > 0
            ):
                log_ai_generation(
                    user=user,
                    item_type='assignment_and_quiz',
                    item_id=lesson_title,
                    model_used=model_name,
                    prompt=prompt,
                    response_json=data,
                    is_validated=True
                )
                return data
            else:
                logger.warning("Gemini response did not match assignment_and_quiz schema.")
        except Exception as e:
            logger.error(f"Gemini assignment and quiz generation failed: {e}")

    # Deterministic validated fallback
    fallback_data = {
        "assignment": f"Implement a complete hands-on project demonstrating the foundational principles of {lesson_title}.",
        "quiz": [
            {
                "id": 1,
                "question": f"What is the primary objective of {lesson_title}?",
                "options": [
                    f"Understanding core concepts of {lesson_title}",
                    "Server maintenance",
                    "Database backup",
                    "Network configuration"
                ],
                "answer": f"Understanding core concepts of {lesson_title}"
            },
            {
                "id": 2,
                "question": f"Which best practice is emphasized in {lesson_title}?",
                "options": [
                    "Modular architecture and clean code hygiene",
                    "Skipping documentation",
                    "Manual deployment",
                    "Hardcoding secrets"
                ],
                "answer": "Modular architecture and clean code hygiene"
            },
            {
                "id": 3,
                "question": f"How do you verify your work in {lesson_title}?",
                "options": [
                    "Writing test assertions and reviewing output",
                    "Ignoring compiler warnings",
                    "Disabling error logs",
                    "Bypassing validation"
                ],
                "answer": "Writing test assertions and reviewing output"
            }
        ]
    }
    log_ai_generation(
        user=user,
        item_type='assignment_and_quiz_fallback',
        item_id=lesson_title,
        model_used='deterministic_fallback',
        prompt=prompt,
        response_json=fallback_data,
        is_validated=True
    )
    return fallback_data


def generate_ai_certificate_remarks(student_name, course_title, percentage, grade):
    """Generates tailored AI remarks for the student's certificate completion."""
    try:
        score = float(percentage)
    except (TypeError, ValueError):
        score = 0.0

    if score >= 90:
        return f"Outstanding mastery of {course_title}! {student_name} demonstrated exceptional critical thinking, dedication, and top-tier performance throughout the curriculum with a grade of {grade}."
    elif score >= 80:
        return f"Great work by {student_name} in mastering {course_title}. Consistent engagement, strong problem-solving skills, and a grade of {grade} resulted in a commendable performance."
    else:
        return f"Successful completion of {course_title} by {student_name} with a grade of {grade}. A solid effort in understanding core concepts and fulfilling all curriculum requirements."
