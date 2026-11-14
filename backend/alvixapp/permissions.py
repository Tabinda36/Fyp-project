"""Single source of truth for "is this user an ALVIX administrator?"."""


def is_alvix_admin(user):
    """Only Django staff/superusers are administrators.

    Admin rights are never derived from mutable profile data such as the email address
    (students can edit their own email). Grant admin with:
        python manage.py grant_admin <email-or-username>
    """
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def can_access_lesson(user, lesson):
    """A student may open only lessons of their own enrolment; admins may preview any lesson."""
    if is_alvix_admin(user):
        return True
    return bool(lesson.generated_course_id) and lesson.generated_course.user_id == user.id
