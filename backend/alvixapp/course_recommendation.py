"""
alvixapp/course_recommendation.py
Handles intelligent catalog filtering and AI-driven course suggestions based on:
1. Interest Area (Creativity, Development, Designing, Marketing)
2. Goal (Practical, Theory, Mixed)
3. Student Expectation Text (minimum 20 characters)
"""

import os
import re
import json
import logging
from django.conf import settings
from google import genai
from google.genai import types
from .models import AdminCourse, CourseLevel, AIGenerationLog
from .ai_helpers import log_ai_generation

logger = logging.getLogger(__name__)

DOMAIN_KEYWORDS = {
    'creativity': [
        'creativ', 'content', 'media', 'writing', 'copywriting',
        'video', 'multimedia', 'animation', 'art', 'arts', 'storytelling',
        'journalism', 'audio', 'music', 'production', 'graphical', 'graphics'
    ],
    'development': [
        'develop', 'developer', 'development', 'web', 'python', 'software',
        'programming', 'code', 'coding', 'django', 'javascript', 'frontend',
        'backend', 'full stack', 'full-stack', 'html', 'css', 'react', 'node',
        'mobile', 'app', 'android', 'flutter', 'engineering', 'tech', 'ai', 'automation',
        'hacking', 'algorithms', 'data structures'
    ],
    'designing': [
        'design', 'designing', 'designer', 'ui', 'ux', 'ui/ux', 'graphic', 'graphical',
        'figma', 'product design', 'visual', 'adobe', 'photoshop', 'illustrator',
        'wireframe', 'prototype', 'branding', 'creative design'
    ],
    'marketing': [
        'marketing', 'digital marketing', 'social media', 'advertising',
        'seo', 'sem', 'campaign', 'brand', 'branding', 'growth',
        'content marketing', 'email marketing', 'sales', 'market research', 'analytics', 'data analytics'
    ]
}

def determine_course_type(course):
    """
    Infers whether a course is Practical, Theoretical, or Mixed based on model field or title/description.
    """
    if hasattr(course, 'course_type') and course.course_type:
        return 'Theory' if course.course_type == 'Theoretical' else course.course_type
    
    text = f"{course.title} {course.description or ''}".lower()
    
    theoretical_signals = ['data structures', 'algorithms', 'architecture', 'principles', 'theory', 'foundations', 'cs50', 'logic']
    practical_signals = ['development', 'engineering', 'programming', 'application', 'full stack', 'full-stack', 'mobile', 'graphical', 'hacking', 'python', 'web']
    
    t_count = sum(1 for w in theoretical_signals if w in text)
    p_count = sum(1 for w in practical_signals if w in text)
    
    if p_count > t_count:
        return 'Practical'
    elif t_count > p_count:
        return 'Theory'
    else:
        return 'Mixed'


def filter_catalog_by_interest_and_goal(interest_area, goal):
    """
    Filters the existing course catalog in code:
    1. Filter by interest area.
    2. Prefer courses whose type (Practical, Theory, Mixed) matches the student's goal.
    """
    active_courses = list(AdminCourse.objects.filter(is_active=True))
    if not active_courses:
        active_courses = list(AdminCourse.objects.all())

    interest_lower = (interest_area or '').strip().lower()
    goal_lower = (goal or '').strip().lower()

    # 1. Filter by interest area
    matched_courses = []
    keywords = DOMAIN_KEYWORDS.get(interest_lower, [])
    
    for c in active_courses:
        text = f"{c.title} {c.description or ''}".lower()
        score = 0
        if interest_lower in text:
            score += 20
        for kw in keywords:
            if kw in text:
                score += 5
        if score > 0:
            matched_courses.append((score, c))

    # Sort by interest relevance score
    matched_courses.sort(key=lambda x: x[0], reverse=True)
    candidate_courses = [item[1] for item in matched_courses]

    if not candidate_courses:
        candidate_courses = active_courses

    # 2. Prefer courses whose type matches student's goal
    def goal_rank(c):
        c_type = determine_course_type(c)
        if goal_lower in c_type.lower() or c_type.lower() in goal_lower:
            return 0  # Highest priority
        elif c_type == 'Mixed':
            return 1  # Secondary priority
        return 2

    candidate_courses.sort(key=goal_rank)
    return candidate_courses


def suggest_best_fit_course_with_ai(user, interest_area, goal, expectations):
    """
    Sends filtered catalog courses and student expectations text to Gemini AI.
    AI must return strictly JSON: { course_id, reason, suggested_level }.
    Reason is exactly 2 sentences referring to the student's expectations.
    Validates course_id against the database. The AI must never invent a course.
    """
    candidates = filter_catalog_by_interest_and_goal(interest_area, goal)
    if not candidates:
        return None, "No active courses available in the catalog.", "Beginner"

    # Prepare catalog candidates for AI
    catalog_payload = []
    for c in candidates[:8]:
        catalog_payload.append({
            "course_id": c.id,
            "title": c.title,
            "description": c.description[:200] if c.description else c.title,
            "type": determine_course_type(c)
        })

    api_key = os.environ.get('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', '')
    prompt = f"""
You are the ALVIX Academic Placement Director and Senior Academic Advisor.
Recommend the single best-fit course from the provided catalog for a student with the following assessment answers:

STUDENT ASSESSMENT:
- Interest Area: "{interest_area}"
- Learning Goal: "{goal}"
- Expectations: "{expectations}"

FILTERED CATALOG COURSES (Prefer type matching "{goal}"):
{json.dumps(catalog_payload, indent=2)}

STRICT REQUIREMENTS:
1. Select exactly ONE course from the catalog list above that best fulfills the student's expectations.
2. Select a suggested_level from: "Beginner", "Intermediate", "Advanced".
3. Write a reason of EXACTLY 2 sentences. The reason MUST directly refer to the student's specific expectations text: "{expectations}".
4. CRITICAL: You must choose ONLY from the course_id values in the list above. Do NOT invent a course.

Return STRICT JSON ONLY matching this format:
{{
    "course_id": <int from the list above>,
    "reason": "<sentence 1 referring to expectations>. <sentence 2 referring to expectations>.",
    "suggested_level": "Beginner" | "Intermediate" | "Advanced"
}}
"""

    suggested_course = None
    reason = ""
    suggested_level = "Beginner"
    is_validated = False
    response_json = {}

    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            clean_json = re.sub(r'```json\s*|```\s*', '', response.text).strip()
            data = json.loads(clean_json)
            response_json = data

            if isinstance(data, dict) and 'course_id' in data:
                cid = data.get('course_id')
                # Validate course_id against the database
                matched_db_course = AdminCourse.objects.filter(id=cid, is_active=True).first()
                if matched_db_course:
                    suggested_course = matched_db_course
                    reason = str(data.get('reason', '')).strip()
                    lvl = str(data.get('suggested_level', 'Beginner')).strip().capitalize()
                    if lvl in ['Beginner', 'Intermediate', 'Advanced']:
                        suggested_level = lvl
                    is_validated = True
        except Exception as e:
            logger.error(f"Gemini AI course recommendation failed: {e}")

    # Fallback to top filtered course if AI failed or returned invalid ID
    if not suggested_course:
        suggested_course = candidates[0]
        c_type = determine_course_type(suggested_course)
        exp_summary = (expectations or '').strip()
        if len(exp_summary) > 70:
            exp_summary = exp_summary[:67] + "..."
        exp_summary = exp_summary.rstrip('.!? ')
        reason = (
            f"You told us: “{exp_summary}”. {suggested_course.title} provides the ideal structured curriculum to achieve those capabilities. "
            f"Its {c_type.lower()} focus directly aligns with your {goal.lower()} goal in {interest_area}."
        )
        suggested_level = "Beginner"
        response_json = {
            "course_id": suggested_course.id,
            "reason": reason,
            "suggested_level": suggested_level,
            "fallback": True
        }
        is_validated = True

    # Audit log prompt and model used
    log_ai_generation(
        user=user,
        item_type='course_suggestion',
        item_id=str(suggested_course.id),
        model_used='gemini-2.5-flash' if is_validated and not response_json.get('fallback') else 'deterministic_fallback',
        prompt=prompt,
        response_json=response_json,
        is_validated=is_validated
    )

    return suggested_course, reason, suggested_level
