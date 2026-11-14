"""Public / auth page logic shared by the legacy template views and /api/v1/public/.

signup (2 steps), the legacy verify-otp page, suggested courses and certificate verification.
"""

import logging
import random
import re
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from ..emails import VERIFICATION_EXPIRY_MINUTES, send_verification_email
from ..course_tier_service import create_course_tiers_and_curriculum, fetch_and_enroll_student_in_level
from ..models import (
    AdminCourse,
    Certificate,
    CourseLevel,
    Profile,
    StudentAssessment,
    generate_unique_student_id,
)

logger = logging.getLogger('alvixapp.views')

SESSION_KEYS = ('signup_verification_code', 'pending_signup_data', 'signup_data', 'signup_code_sent_at')


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------
def finalize_student_registration(request, pending_data):
    """
    Creates user, ensures unique student_id on Profile, creates StudentAssessment,
    picks the 1 best matching AdminCourse from database, and sets up session.
    """
    from ..views import find_best_matching_admin_course  # lives in views.py (owned elsewhere)

    full_name = (pending_data.get('full_name') or pending_data.get('username', '')).strip()
    username = pending_data.get('username', '').strip()
    email = pending_data.get('email', '').strip()
    password_hash = pending_data.get('password_hash')
    raw_password = pending_data.get('password')  # legacy sessions only
    interest = pending_data.get('interest', '').strip()
    knowledge_level = pending_data.get('knowledge_level', 'Beginner')
    purpose = pending_data.get('purpose', 'Improvement of Skills')

    # 1. Create User
    user = User.objects.create_user(
        username=username,
        email=email,
        password=raw_password,
        first_name=full_name
    )
    if password_hash:
        user.password = password_hash
        user.save(update_fields=['password'])

    # 2. Ensure Profile & Unique Student ID
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.full_name = full_name
    if not profile.student_id:
        profile.student_id = generate_unique_student_id()
    profile.goal = purpose
    profile.save()

    # 3. Find 1 Best Course Suggestion from Database
    suggested_course = find_best_matching_admin_course(interest, knowledge_level, purpose)

    # 4. Create StudentAssessment record
    StudentAssessment.objects.create(
        user=user,
        student_id=profile.student_id,
        full_name=full_name,
        email=email,
        knowledge_level=knowledge_level,
        learning_goal=purpose,
        interest=suggested_course,
        interest_topic=interest,
        selected_course=suggested_course.title if suggested_course else None
    )

    # 5. Store assessment and suggestion data in session
    request.session['student_name'] = profile.full_name
    request.session['student_id'] = profile.student_id
    request.session['recommended_course_id'] = suggested_course.id if suggested_course else None
    request.session['assessment_purpose'] = purpose
    request.session['assessment_level'] = knowledge_level
    request.session['assessment_interest'] = interest

    # 6. Log in the student
    login(request, user)

    return user, suggested_course


def _get(data, key, default=''):
    value = data.get(key, default)
    return default if value is None else value


def signup_start(request, data):
    """Step 1 (registration form). `data` is request.POST or request.data.

    Returns {'ok': True, 'step': 'verify', 'email', 'verification_code_debug'} or
    {'ok': False, 'error', 'saved_data'} (same values the template rendered).
    """
    full_name = str(_get(data, 'full_name')).strip()
    username = str(_get(data, 'username')).strip()
    email = str(_get(data, 'email')).strip()
    password = str(_get(data, 'password'))
    confirm_password = str(_get(data, 'confirm_password'))

    # Assessment fields
    interest = str(data.get('interest') or _get(data, 'topic')).strip()
    knowledge_level = str(data.get('knowledge_level') or _get(data, 'level', 'Beginner')).strip()
    purpose = str(data.get('purpose') or _get(data, 'learning_goal', 'Improvement of Skills')).strip()

    if not full_name:
        full_name = username

    error = None
    if password != confirm_password:
        error = "Passwords do not match."
    elif User.objects.filter(username__iexact=username).exists():
        error = "Username is already taken. Please choose another one."
    elif User.objects.filter(email__iexact=email).exists():
        error = "An account with this email already exists."
    else:
        candidate = User(username=username, email=email, first_name=full_name)
        try:
            validate_password(password, user=candidate)
        except DjangoValidationError as validation_error:
            error = ' '.join(validation_error.messages)
        if not error and not (
            re.search(r'[A-Z]', password)
            and re.search(r'[a-z]', password)
            and re.search(r'\d', password)
            and re.search(r'[^A-Za-z0-9]', password)
        ):
            error = "Use an uppercase letter, a lowercase letter, a number, and a symbol in your password."
    if error:
        return {'ok': False, 'error': error, 'saved_data': data}

    # Generate 6-digit verification code
    verification_code = random.randint(100000, 999999)

    pending_data = {
        'full_name': full_name,
        'username': username,
        'email': email,
        'password_hash': make_password(password),
        'interest': interest,
        'knowledge_level': knowledge_level,
        'purpose': purpose,
        'otp': str(verification_code),
    }

    request.session['signup_verification_code'] = verification_code
    request.session.pop('signup_otp_attempts', None)
    request.session['pending_signup_data'] = pending_data
    request.session['signup_data'] = pending_data
    request.session['signup_code_sent_at'] = time.time()

    # Send the branded verification email (templates/emails/verification_code.*)
    try:
        send_verification_email(full_name, email, verification_code)
    except Exception as mail_err:
        logger.error(f"Mail sending failed: {mail_err}")
        print(f"--- DEBUG VERIFICATION CODE FOR {email}: {verification_code} ---")

    return {
        'ok': True,
        'step': 'verify',
        'email': email,
        'verification_code_debug': verification_code if settings.DEBUG else None,
    }


def pending_signup(request):
    return request.session.get('pending_signup_data') or request.session.get('signup_data')


def _code_expired(request):
    """True when the emailed code is older than VERIFICATION_EXPIRY_MINUTES (no timestamp = legacy session, never expires)."""
    sent_at = request.session.get('signup_code_sent_at')
    return bool(sent_at) and time.time() - float(sent_at) > VERIFICATION_EXPIRY_MINUTES * 60


EXPIRED_MESSAGE = 'This code has expired. Use "Resend code" to get a new one.'


def _clear_signup_session(request):
    for key in SESSION_KEYS:
        request.session.pop(key, None)


MAX_OTP_ATTEMPTS = 5


def _too_many_attempts(request):
    """Count a failed code; after MAX_OTP_ATTEMPTS the pending signup is discarded (stops brute force)."""
    attempts = request.session.get('signup_otp_attempts', 0) + 1
    request.session['signup_otp_attempts'] = attempts
    if attempts >= MAX_OTP_ATTEMPTS:
        _clear_signup_session(request)
        request.session.pop('signup_otp_attempts', None)
        return True
    return False


def signup_verify(request, entered_code):
    """Step 2 as handled by signup_view.

    Returns {'ok': True, 'user'} or {'ok': False, 'error', 'step', 'email'}
    ('step'/'email' only set when the template stayed on the verification step).
    """
    entered_code = (entered_code or '').strip()
    session_code = request.session.get('signup_verification_code') or (request.session.get('signup_data', {}).get('otp'))
    pending_data = pending_signup(request)

    if not session_code or not pending_data:
        return {'ok': False, 'error': "Session expired. Please fill the registration form again.", 'step': None, 'email': None}

    if _code_expired(request):
        return {'ok': False, 'error': EXPIRED_MESSAGE, 'step': 'verify', 'email': pending_data.get('email')}

    if entered_code != str(session_code):
        if _too_many_attempts(request):
            return {'ok': False, 'error': "Too many invalid codes. Please fill the registration form again.", 'step': None, 'email': None}
        return {'ok': False, 'error': "Invalid verification code. Please try again.",
                'step': 'verify', 'email': pending_data.get('email')}

    try:
        user, _suggested = finalize_student_registration(request, pending_data)
        _clear_signup_session(request)
        return {'ok': True, 'user': user}
    except Exception as e:
        logger.error(f"Registration finalize error: {e}")
        return {'ok': False, 'error': f"Registration Error: {str(e)}", 'step': None, 'email': None}


def verify_otp(request, entered_otp):
    """Legacy /verify-otp/ handling (verify_otp_view). Call only when pending_signup(request) is set.

    Returns {'ok': True, 'user'} or {'ok': False, 'error', 'email'}.
    """
    pending_data = pending_signup(request)
    entered_otp = (entered_otp or '').strip()
    session_otp = str(request.session.get('signup_verification_code') or pending_data.get('otp', ''))

    if _code_expired(request):
        return {'ok': False, 'error': EXPIRED_MESSAGE, 'email': pending_data.get('email')}

    if entered_otp == session_otp:
        try:
            user, _suggested = finalize_student_registration(request, pending_data)
            _clear_signup_session(request)
            return {'ok': True, 'user': user}
        except Exception as e:
            return {'ok': False, 'error': f"Verification Error: {str(e)}", 'email': pending_data.get('email')}
    if _too_many_attempts(request):
        return {'ok': False, 'error': "Too many invalid codes. Please fill the registration form again.", 'email': None}
    return {'ok': False, 'error': "Invalid verification code. Please try again.", 'email': pending_data.get('email')}


# ---------------------------------------------------------------------------
# Suggested courses
# ---------------------------------------------------------------------------
def resolve_course_suggestion(request):
    """Shared top half of the suggested_courses view (may call the AI recommender)."""
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    student_name = profile_obj.full_name or request.user.get_full_name() or request.user.username
    student_id = profile_obj.student_id

    interest_area = profile_obj.interest_area or request.session.get('assessment_interest', 'Development')
    goal = profile_obj.goal or request.session.get('assessment_purpose', 'Practical')
    expectations = profile_obj.expectations or "Comprehensive mastery of core concepts and practical real-world skills."

    # Retrieve or generate the AI course suggestion
    from ..course_recommendation import suggest_best_fit_course_with_ai

    course_id = request.session.get('recommended_course_id')
    reason = request.session.get('ai_suggestion_reason')
    suggested_level = request.session.get('ai_suggested_level', 'Beginner')

    suggested_course = None
    if course_id:
        suggested_course = AdminCourse.objects.filter(id=course_id, is_active=True).first()

    if not suggested_course or not reason:
        suggested_course, reason, suggested_level = suggest_best_fit_course_with_ai(
            user=request.user,
            interest_area=interest_area,
            goal=goal,
            expectations=expectations
        )
        if suggested_course:
            request.session['recommended_course_id'] = suggested_course.id
            request.session['ai_suggestion_reason'] = reason
            request.session['ai_suggested_level'] = suggested_level

    # Fallback if catalog had no matching courses
    if not suggested_course:
        suggested_course = AdminCourse.objects.filter(is_active=True).first() or AdminCourse.objects.first()

    return {
        'student_name': student_name,
        'student_id': student_id,
        'interest_area': interest_area,
        'goal': goal,
        'expectations': expectations,
        'suggested_course': suggested_course,
        'ai_reason': reason,
        'suggested_level': suggested_level,
    }


def handle_suggested_courses_action(request, data, ctx):
    """POST choices (b), (c1), (c2). Adds Django messages exactly like the view.

    Returns the redirect path, or None when the view fell through to re-render the page.
    """
    suggested_course = ctx['suggested_course']
    suggested_level = ctx['suggested_level']
    expectations = ctx['expectations']
    action = data.get('action', 'start_suggested')

    try:
        # Choice (b): Start the suggested course
        if action == 'start_suggested':
            chosen_level = data.get('level', suggested_level or 'Beginner')
            create_course_tiers_and_curriculum(suggested_course)
            level_obj = CourseLevel.objects.filter(parent_course=suggested_course, level__iexact=chosen_level).first()
            if not level_obj:
                level_obj = CourseLevel.objects.filter(parent_course=suggested_course).first()

            if level_obj:
                gen_course = fetch_and_enroll_student_in_level(
                    user=request.user,
                    course_level=level_obj,
                    pace='Standard',
                    objective=f"Master {suggested_course.title} ({level_obj.benchmark})"
                )
                messages.success(request, f"Enrolled in '{suggested_course.title}' at {level_obj.level} level!")
                return f"/course_content/?course_id={gen_course.id}"

        # Choice (c1): Pick any other existing course from the catalog
        elif action == 'pick_other_course':
            other_course_id = data.get('other_course_id')
            other_level = data.get('other_level', 'Beginner')
            other_course = AdminCourse.objects.filter(id=other_course_id, is_active=True).first()
            if other_course:
                create_course_tiers_and_curriculum(other_course)
                level_obj = CourseLevel.objects.filter(parent_course=other_course, level__iexact=other_level).first()
                if not level_obj:
                    level_obj = CourseLevel.objects.filter(parent_course=other_course).first()

                if level_obj:
                    gen_course = fetch_and_enroll_student_in_level(
                        user=request.user,
                        course_level=level_obj,
                        pace='Standard',
                        objective=f"Master {other_course.title} ({level_obj.benchmark})"
                    )
                    messages.success(request, f"Enrolled in '{other_course.title}' at {level_obj.level} level!")
                    return f"/course_content/?course_id={gen_course.id}"
            else:
                messages.error(request, "Selected course could not be found.")

        # Choice (c2): Generate a new course from a title typed by student
        elif action == 'generate_new_course':
            custom_title = str(data.get('custom_course_title', '') or '').strip()
            custom_level = data.get('custom_level', 'Beginner')
            custom_pace = data.get('custom_pace', 'Standard')

            if not custom_title:
                messages.error(request, "Please enter a course title to generate.")
                return '/suggested_courses/'

            admin_course = AdminCourse.objects.filter(title__iexact=custom_title).first()
            if not admin_course:
                admin_course = AdminCourse.objects.create(
                    title=custom_title,
                    description=f"AI-generated personalized course on {custom_title}."
                )
            create_course_tiers_and_curriculum(admin_course)

            from ..ai_services import generate_course_with_gemini
            gen_course = generate_course_with_gemini(
                admin_course=admin_course,
                user=request.user,
                level=custom_level,
                pace=custom_pace,
                objective=expectations or f"Master {custom_title}"
            )

            messages.success(request, f"Successfully generated and enrolled in new course '{custom_title}'!")
            return f"/course_content/?course_id={gen_course.id}"

    except Exception as e:
        logger.error(f"Enrollment or generation action error: {e}")
        messages.error(request, f"Action error: {e}")
        return '/suggested_courses/'

    return None


def build_suggested_courses_context(request, ctx):
    """Bottom half of the view: catalog choices + tiers for the suggested course."""
    suggested_course = ctx['suggested_course']

    # Other existing active catalog courses (excluding suggested course)
    other_courses = AdminCourse.objects.filter(is_active=True)
    if suggested_course:
        other_courses = other_courses.exclude(id=suggested_course.id)

    # University benchmark tiers for the suggested course
    available_levels = []
    if suggested_course:
        create_course_tiers_and_curriculum(suggested_course)
        available_levels = suggested_course.course_levels.filter(is_active=True).order_by('id')

    return {
        **ctx,
        'available_levels': available_levels,
        'other_courses': other_courses,
    }


# ---------------------------------------------------------------------------
# Certificate verification
# ---------------------------------------------------------------------------
def build_certificate_verify_context(cert_id):
    cert = Certificate.objects.filter(certificate_id=cert_id).first()
    is_valid = bool(cert and cert.is_valid and cert.is_unlocked)
    return {
        'certificate': cert,
        'cert_id': cert_id,
        'is_valid': is_valid,
        'verification_time': timezone.now(),
    }
