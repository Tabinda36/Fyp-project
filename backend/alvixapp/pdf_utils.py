import os
from django.conf import settings
from reportlab.lib.pagesizes import letter # pyright: ignore[reportMissingModuleSource]
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer # pyright: ignore[reportMissingModuleSource]
from reportlab.lib.styles import getSampleStyleSheet # pyright: ignore[reportMissingModuleSource]

def create_lesson_pdf(daily_lesson):
    file_name = f"course_{daily_lesson.generated_course.id}_day_{daily_lesson.day_number}.pdf"
    relative_path = os.path.join('generated_pdfs', file_name)
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    doc = SimpleDocTemplate(full_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>{daily_lesson.generated_course.admin_course.title}</b>", styles['Heading2']))
    story.append(Paragraph(f"Day {daily_lesson.day_number}: {daily_lesson.title}", styles['Heading1']))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>Level:</b> {daily_lesson.generated_course.level}", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>Lesson Notes & Explanation:</b>", styles['Heading3']))
    story.append(Spacer(1, 5))
    
    for paragraph in daily_lesson.explanation.split('\n'):
        if paragraph.strip():
            story.append(Paragraph(paragraph, styles['BodyText']))
            story.append(Spacer(1, 6))

    doc.build(story)
    
    daily_lesson.pdf_file = relative_path
    daily_lesson.save()
    return full_path