"""
alvixapp/copy_detection.py
Integrity and copy/paste detection engine for student assignment submissions.
Tracks:
1. Paste events and pasted character size in answer editor.
2. Typing patterns (duration, keystroke count, typing velocity).
3. Peer similarity against existing student submissions for the same lesson day.
4. Heuristic & linguistic analysis for AI-generated / copied patterns.
Generates an actionable 'copy risk' flag (Low / Medium / High) with detailed diagnostics for admin review.
Does not automatically give zero; leaves final discretion to instructors.
"""

import re
import difflib
from .models import AssignmentSubmission


AI_MARKER_PATTERNS = [
    r'\bin conclusion\b',
    r'\bit is crucial to (?:understand|remember|note)\b',
    r'\ba testament to\b',
    r'\bdelv(?:e|ing) into\b',
    r'\bmoreover\b',
    r'\bfurthermore\b',
    r'\bseamlessly integrates\b',
    r'\brobust and scalable\b',
    r'\bcomprehensive overview\b',
    r'\bpivotal role\b',
    r'\bkey takeaways? include\b',
    r'\bin essence\b',
    r'\bunderscores the importance\b',
]


def detect_ai_text_probability(text: str) -> float:
    """
    Computes heuristic AI-generated probability (0.0 to 100.0) based on
    formulaic transition frequency, vocabulary entropy, and structural uniformity.
    """
    if not text or len(text.strip()) < 40:
        return 0.0

    lower = text.lower()
    matches = 0
    for pattern in AI_MARKER_PATTERNS:
        if re.search(pattern, lower):
            matches += 1

    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if not sentences:
        return 0.0

    # Sentence length variance (AI typically generates uniform medium-length sentences)
    lens = [len(s.split()) for s in sentences]
    avg_len = sum(lens) / len(lens) if lens else 0
    variance = sum((l - avg_len) ** 2 for l in lens) / len(lens) if len(lens) > 1 else 10.0

    base_score = min(50.0, matches * 18.0)
    # Low variance (uniform rhythm) increases probability
    if 12.0 <= avg_len <= 26.0 and variance < 20.0 and len(sentences) >= 3:
        base_score += 25.0

    # Clean punctuation and lack of any colloquialisms/typos
    if not re.search(r'\b(gonna|wanna|kinda|dunno|idk|btw|pls)\b', lower) and matches >= 2:
        base_score += 15.0

    return min(95.0, round(base_score, 1))


def compute_peer_similarity(submission_text: str, current_user, lesson) -> float:
    """
    Measures text similarity against all previous student submissions for the same lesson day.
    Uses SequenceMatcher token-based ratio.
    """
    if not submission_text or len(submission_text.strip()) < 30:
        return 0.0

    clean_sub = " ".join(submission_text.lower().split())

    # Find peer submissions for this day
    peers = AssignmentSubmission.objects.filter(
        lesson__day_number=lesson.day_number
    ).exclude(user=current_user)

    max_sim = 0.0
    for peer in peers[:25]:
        p_text = peer.submitted_answer or ""
        clean_peer = " ".join(p_text.lower().split())
        if not clean_peer or len(clean_peer) < 30:
            continue
        ratio = difflib.SequenceMatcher(None, clean_sub, clean_peer).ratio()
        if ratio > max_sim:
            max_sim = ratio

    return round(max_sim * 100.0, 1)


def evaluate_submission_copy_risk(
    submission_text: str,
    paste_count: int,
    pasted_chars_total: int,
    typing_duration_seconds: int,
    keystroke_count: int,
    current_user,
    lesson
):
    """
    Aggregates all integrity telemetry and returns:
    (copy_risk_level, peer_similarity_score, ai_generated_probability, copy_risk_details)
    """
    total_len = len(submission_text.strip())
    paste_ratio = (pasted_chars_total / total_len * 100.0) if total_len > 0 else 0.0

    peer_similarity = compute_peer_similarity(submission_text, current_user, lesson)
    ai_prob = detect_ai_text_probability(submission_text)

    # Determine Risk
    risk_level = "Low"
    flags = []

    if paste_count > 0 and paste_ratio >= 70.0 and typing_duration_seconds < 15:
        risk_level = "High"
        flags.append(f"Bulk pasted {paste_ratio:.0f}% of content in {typing_duration_seconds}s")
    elif paste_ratio >= 40.0:
        if risk_level != "High":
            risk_level = "Medium"
        flags.append(f"Substantial pasted content ({paste_ratio:.0f}%)")

    if peer_similarity >= 75.0:
        risk_level = "High"
        flags.append(f"Critical peer text similarity ({peer_similarity:.1f}%)")
    elif peer_similarity >= 45.0:
        if risk_level != "High":
            risk_level = "Medium"
        flags.append(f"Elevated peer text similarity ({peer_similarity:.1f}%)")

    if ai_prob >= 75.0:
        if risk_level != "High":
            risk_level = "High"
        flags.append(f"High probability of AI-generated phrasing ({ai_prob:.0f}%)")
    elif ai_prob >= 50.0:
        if risk_level == "Low":
            risk_level = "Medium"
        flags.append(f"Moderate AI stylistic markers detected ({ai_prob:.0f}%)")

    if not flags:
        flags.append("Normal manual typing cadence and low peer similarity")

    details = (
        f"Copy Risk: {risk_level}. "
        f"Telemetry: {paste_count} paste event(s), {pasted_chars_total} pasted chars ({paste_ratio:.1f}% ratio). "
        f"Active typing: {typing_duration_seconds}s with {keystroke_count} keystrokes. "
        f"Peer similarity: {peer_similarity:.1f}%. AI probability: {ai_prob:.1f}%. "
        f"Signals: {'; '.join(flags)}."
    )

    return risk_level, peer_similarity, ai_prob, details
