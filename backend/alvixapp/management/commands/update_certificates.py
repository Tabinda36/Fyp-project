"""
alvixapp/management/commands/update_certificates.py
Daily scheduled background job that updates duration, performance grade,
and AI review for all enrolled student courses so certificates always reflect the latest performance.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from alvixapp.models import GeneratedCourse
from alvixapp.certificate_service import update_or_create_student_certificate

class Command(BaseCommand):
    help = "Daily scheduled job to update student certificates with current duration, grade, and AI review."

    def handle(self, *args, **options):
        courses = GeneratedCourse.objects.select_related('user', 'admin_course').all()
        updated_count = 0

        self.stdout.write(f"[{timezone.now()}] Starting daily certificate update for {courses.count()} courses...")

        for course in courses:
            try:
                cert, perf = update_or_create_student_certificate(course.user, course)
                updated_count += 1
            except Exception as e:
                self.stderr.write(f"Failed to update certificate for course {course.id} ({course.user.username}): {e}")

        self.stdout.write(self.style.SUCCESS(
            f"[{timezone.now()}] Successfully updated {updated_count} student certificates."
        ))
