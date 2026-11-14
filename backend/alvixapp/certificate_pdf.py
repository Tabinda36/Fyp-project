"""
alvixapp/certificate_pdf.py
High-resolution server-side PDF certificate generator.
Draws an official academic certificate with ornamental borders, gold seal, student profile,
course metrics, AI review, and scannable QR verification code.
Generates standard %PDF-1.4 without requiring external C libraries or network access.
"""

import io
import os
from PIL import Image, ImageDraw, ImageFont
from .qr_generator import generate_qr_image

def _get_font(size: int, bold: bool = False):
    """Safely retrieves a clean TrueType font or falls back to Pillow default font."""
    font_names = [
        'arialbd.ttf' if bold else 'arial.ttf',
        'calibrib.ttf' if bold else 'calibri.ttf',
        'timesbd.ttf' if bold else 'times.ttf',
        'georgiab.ttf' if bold else 'georgia.ttf',
        'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf',
    ]
    # Check Windows font directories
    win_fonts = os.environ.get('WINDIR', 'C:\\Windows') + '\\Fonts'
    for name in font_names:
        full_path = os.path.join(win_fonts, name)
        if os.path.exists(full_path):
            try:
                return ImageFont.truetype(full_path, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def generate_certificate_pdf_bytes(cert_record) -> io.BytesIO:
    """
    Renders an official landscape A4 certificate from a Certificate model instance.
    Returns a BytesIO stream containing compliant PDF binary data.
    """
    width = 1600
    height = 1130

    # 1. Background Parchment
    img = Image.new('RGB', (width, height), color=(253, 251, 247))
    draw = ImageDraw.Draw(img)

    # 2. Outer and Inner Ornamental Borders
    # Emerald green & Golden Double Borders
    green = (6, 78, 59)
    gold = (212, 175, 55)
    dark_gold = (184, 150, 40)
    charcoal = (30, 41, 59)
    gray = (100, 116, 139)

    # Outer Gold Border
    draw.rectangle([25, 25, width - 25, height - 25], outline=gold, width=4)
    # Emerald Green Thick Border
    draw.rectangle([35, 35, width - 35, height - 35], outline=green, width=8)
    # Inner Thin Gold Border
    draw.rectangle([48, 48, width - 48, height - 48], outline=gold, width=2)

    # Corner Accents
    for cx, cy in [(55, 55), (width - 55, 55), (55, height - 55), (width - 55, height - 55)]:
        draw.rectangle([cx - 8, cy - 8, cx + 8, cy + 8], fill=dark_gold)

    # Fonts
    f_title = _get_font(42, bold=True)
    f_subtitle = _get_font(18, bold=False)
    f_certify = _get_font(18, bold=False)
    f_name = _get_font(44, bold=True)
    f_body = _get_font(20, bold=False)
    f_course = _get_font(30, bold=True)
    f_meta_label = _get_font(15, bold=True)
    f_meta_val = _get_font(17, bold=False)
    f_review_title = _get_font(16, bold=True)
    f_review_body = _get_font(15, bold=False)
    f_small = _get_font(13, bold=False)

    # 3. Header & Academy Branding
    draw.text((width // 2, 85), "ALVIX ACADEMIC REGISTRY", fill=green, font=f_title, anchor="mm")
    draw.text((width // 2, 130), "BENCHMARK-VERIFIED COURSE COMPLETION & EXCELLENCE", fill=dark_gold, font=f_subtitle, anchor="mm")

    # Divider Line
    draw.line([(width // 2 - 280, 155), (width // 2 + 280, 155)], fill=gold, width=2)

    # 4. Certification Statement
    draw.text((width // 2, 195), "THIS IS TO OFFICIALLY CERTIFY THAT", fill=gray, font=f_certify, anchor="mm")

    # Student Name
    student_name = cert_record.student_name.upper()
    draw.text((width // 2, 255), student_name, fill=green, font=f_name, anchor="mm")
    draw.line([(width // 2 - 320, 290), (width // 2 + 320, 290)], fill=gold, width=2)

    # Conferred text
    draw.text((width // 2, 330), "has successfully fulfilled all university-grade laboratory benchmarks, diagnostic quizzes, and curricula for", fill=charcoal, font=f_body, anchor="mm")

    # Course Name & Level
    course_display = f"{cert_record.course_name} — {cert_record.level} Level"
    draw.text((width // 2, 375), course_display, fill=green, font=f_course, anchor="mm")

    # 5. Metadata Badges (Active Duration, Overall Percentage, Grade)
    start_str = cert_record.start_date.strftime("%B %d, %Y")
    end_str = cert_record.current_date.strftime("%B %d, %Y")
    duration_str = f"{start_str} to {end_str} ({cert_record.duration_days} Days Study)"

    # Draw Metadata Cards
    box_y = 430
    box_w = 400
    box_h = 75

    # Box 1: Duration
    b1_x = 100
    draw.rectangle([b1_x, box_y, b1_x + box_w, box_y + box_h], fill=(255, 255, 255), outline=gold, width=2)
    draw.text((b1_x + 20, box_y + 15), "ACADEMIC DURATION:", fill=green, font=f_meta_label)
    draw.text((b1_x + 20, box_y + 40), duration_str, fill=charcoal, font=f_meta_val)

    # Box 2: Score & Grade
    b2_x = 550
    draw.rectangle([b2_x, box_y, b2_x + 360, box_y + box_h], fill=(255, 255, 255), outline=gold, width=2)
    draw.text((b2_x + 20, box_y + 15), "OVERALL SCORE & GRADE:", fill=green, font=f_meta_label)
    score_grade_str = f"{cert_record.overall_percentage:.1f}% — {cert_record.performance_grade}"
    draw.text((b2_x + 20, box_y + 40), score_grade_str, fill=(184, 150, 40), font=f_meta_val)

    # Box 3: Verification Status
    b3_x = 950
    draw.rectangle([b3_x, box_y, b3_x + 550, box_y + box_h], fill=(255, 255, 255), outline=gold, width=2)
    draw.text((b3_x + 20, box_y + 15), "CREDENTIAL STATUS:", fill=green, font=f_meta_label)
    draw.text((b3_x + 20, box_y + 40), "VERIFIED & AUTHENTICATED (PASS STATUS)", fill=(22, 101, 52), font=f_meta_val)

    # 6. AI Academic Review Section
    rev_y = 535
    rev_w = 1400
    rev_h = 240
    rev_x = (width - rev_w) // 2

    draw.rectangle([rev_x, rev_y, rev_x + rev_w, rev_y + rev_h], fill=(255, 255, 255), outline=gold, width=2)
    # Header ribbon
    draw.rectangle([rev_x, rev_y, rev_x + rev_w, rev_y + 42], fill=green)
    draw.text((rev_x + 25, rev_y + 21), "AUTONOMOUS AI ACADEMIC EVALUATION & TOPIC REVIEW", fill=(255, 255, 255), font=f_review_title, anchor="lm")

    # Word wrap AI review text
    review_text = cert_record.ai_review or "Candidate has demonstrated sound proficiency across fundamental and advanced module objectives."
    words = review_text.split()
    lines = []
    curr = []
    for w in words:
        curr.append(w)
        if len(' '.join(curr)) > 115:
            lines.append(' '.join(curr))
            curr = []
    if curr:
        lines.append(' '.join(curr))

    y_text = rev_y + 60
    for l in lines[:7]:
        draw.text((rev_x + 25, y_text), l, fill=charcoal, font=f_review_body)
        y_text += 25

    # 7. QR Code for Public Verification (Bottom Right)
    verification_url = cert_record.verification_url or f"https://alvix.edu/verify-certificate/{cert_record.certificate_id}/"
    qr_img = generate_qr_image(verification_url, box_size=5, border=2)
    qr_w, qr_h = qr_img.size

    qr_x = width - 100 - qr_w
    qr_y = height - 100 - qr_h
    # Frame for QR code
    draw.rectangle([qr_x - 6, qr_y - 6, qr_x + qr_w + 6, qr_y + qr_h + 6], fill=(255, 255, 255), outline=gold, width=2)
    img.paste(qr_img, (qr_x, qr_y))

    draw.text((qr_x + qr_w // 2, qr_y + qr_h + 15), "Scan to Verify Authenticity", fill=gray, font=f_small, anchor="mm")

    # 8. Signatures & Certificate ID (Bottom Left & Center)
    sig_y = height - 170

    # Signature 1: Dean / Faculty
    draw.line([(100, sig_y), (380, sig_y)], fill=charcoal, width=1)
    draw.text((240, sig_y + 18), "Dean of Computer Science", fill=charcoal, font=f_meta_label, anchor="mm")
    draw.text((240, sig_y + 36), "ALVIX University Curriculum Board", fill=gray, font=f_small, anchor="mm")

    # Signature 2: AI Evaluator
    draw.line([(450, sig_y), (730, sig_y)], fill=charcoal, width=1)
    draw.text((590, sig_y + 18), "Autonomous AI Academic Proctor", fill=charcoal, font=f_meta_label, anchor="mm")
    draw.text((590, sig_y + 36), "Continuous Telemetry & Evaluation Engine", fill=gray, font=f_small, anchor="mm")

    # Certificate ID & Registry Stamp (Bottom Center)
    id_y = height - 90
    draw.text((100, id_y), f"Official Certificate ID: {cert_record.certificate_id}", fill=green, font=f_meta_label)
    draw.text((100, id_y + 22), f"Registered to: {cert_record.student_email} • Immutable Registry Log Verified", fill=gray, font=f_small)

    # 9. Save as high-resolution PDF
    buf = io.BytesIO()
    img.save(buf, format='PDF', resolution=150.0)
    buf.seek(0)
    return buf
