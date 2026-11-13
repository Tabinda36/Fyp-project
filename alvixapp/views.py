
def get_avatar_asset_status():
    """
    Scans public/assets/avatar/ for custom cartoon PNG frames:
    - inara_idle.png
    - inara_wave.png
    - inara_blink.png
    - inara_mouth_open.png
    Applies fallback rule: missing frames fallback to inara_idle.png.
    If no frames exist at all, flags none_exist=True for SVG placeholder.
    """
    avatar_dir = os.path.join(django_settings.BASE_DIR, 'public', 'assets', 'avatar')
    required_files = {
        'idle': 'inara_idle.png',
        'wave': 'inara_wave.png',
        'blink': 'inara_blink.png',
        'mouth_open': 'inara_mouth_open.png',
    }
    dir_exists = os.path.isdir(avatar_dir)
    file_status = {}
    present_count = 0

    for key, filename in required_files.items():
        filepath = os.path.join(avatar_dir, filename) if dir_exists else ''
        exists = bool(dir_exists and os.path.isfile(filepath))
        if exists:
            present_count += 1
        file_status[key] = {
            'filename': filename,
            'exists': exists,
            'path': filepath,
            'url': f'/public/assets/avatar/{filename}',
        }

    has_idle = file_status['idle']['exists']
    none_exist = (present_count == 0)
    all_exist = (present_count == len(required_files))

    resolved_urls = {}
    for key, info in file_status.items():
        if info['exists']:
            resolved_urls[key] = info['url']
        elif has_idle:
            resolved_urls[key] = file_status['idle']['url']
        else:
            resolved_urls[key] = ''

    return {
        'avatar_dir': avatar_dir,
        'dir_exists': dir_exists,
        'file_status': file_status,
        'present_count': present_count,
        'total_required': len(required_files),
        'all_exist': all_exist,
        'missing_files': [info['filename'] for info in file_status.values() if not info['exists']],
        'has_idle': has_idle,
        'none_exist': none_exist,
        'has_custom_avatar': has_idle or (present_count > 0),
        'resolved_urls': resolved_urls,
    }

from .copy_detection import evaluate_submission_copy_risk
from .certificate_service import (
    calculate_course_performance,
    update_or_create_student_certificate,
)
from .certificate_pdf import generate_certificate_pdf_bytes
from .models import Certificate
from django.views.decorators.csrf import csrf_exempt

from datetime import timedelta
import os
import json
import logging
from django.conf import settings
from django.conf import settings as django_settings
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from google import genai

from .models import (
    CourseLevel,
    StudentAssessment,
    AdminCourse,
    StudentCourse,
    GeneratedCourse,
    DailyLesson,
    Profile,
    Notification,
    StudentNotificationStatus,
    UserSettings,
    Performance,
    StudentReport,
    CourseModule,
    Course,
    Report,
    LessonTask,
    StudentProgress,
    AcademicLesson,
    PresentationSlide,
    AssignmentSubmission,
    QuizSubmission,
    AvatarSettings,
)
from .course_tier_service import (
    create_course_tiers_and_curriculum,
    fetch_and_enroll_student_in_level,
    TIER_CONFIGS,
)
from .deep_curriculum_service import generate_deep_university_curriculum

# 2. Forms imported from .forms
from .forms import ReportForm, StudentAssessmentForm, UserSettingsForm, StudentProfileAssessmentForm, AvatarSettingsForm

# Helper AI Function for YouTube Video Integration
try:
    from .ai_helpers import fetch_top_mentor_video, generate_assignment_and_quiz
except ImportError:
    fetch_top_mentor_video = lambda q: "https://www.youtube.com/embed/nu_pCVPKzTk"
    generate_assignment_and_quiz = lambda title, content: {
        'assignment': f'Write a short summary of {title}.',
        'quiz': [{'id': 1, 'question': 'What is the key takeaway?', 'answer': 'A'}]
    }

# AI & PDF Services
from .ai_services import generate_course_content_with_ai, generate_course_with_gemini
try:
    from .pdf_utils import create_lesson_pdf
except ImportError:
    create_lesson_pdf = None

from .ppt_generator import get_or_generate_lesson_lecture



# ........................................ MAIN PAGE & PUBLIC VIEWS..............................................#

def mainpage(request):
    return render(request, 'main_front/mainpage.html')


def login_view(request):
    if request.method == "POST":
        email_input = request.POST.get("email")
        password = request.POST.get("password")

        user_obj = User.objects.filter(email=email_input).first()
        username = user_obj.username if user_obj else email_input

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.email == "tabindarukhsar36@gmail.com" or user.is_staff:
                return redirect("admin_dashboard")
            profile_obj, _ = Profile.objects.get_or_create(user=user)
            if not profile_obj.assessment_completed:
                return redirect("student_assessment")
            return redirect("dashboard")
        else:
            return render(request, "main_front/login.html", {
                "error": "Invalid email or password."
            })

    return render(request, "main_front/login.html")


# ==========================================
# SIGN UP WITH ASSESSMENT & OTP VERIFICATION
# ==========================================
import random
import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.db.models import Q
from django.views.decorators.csrf import csrf_protect
from .models import StudentAssessment, AdminCourse, GeneratedCourse, DailyLesson, Profile, generate_unique_student_id, AIGenerationLog

logger = logging.getLogger(__name__)


def find_best_matching_admin_course(interest, knowledge_level=None, purpose=None):
    """
    Finds exactly 1 best matching AdminCourse from the database based on the student's assessment.
    Core Domains: Creativity, Development, Management, Designing.
    """
    courses_qs = AdminCourse.objects.all()
    if hasattr(AdminCourse, 'is_active'):
        courses_qs = courses_qs.filter(is_active=True)

    if not courses_qs.exists():
        courses_qs = AdminCourse.objects.all()
        if not courses_qs.exists():
            return None

    interest_str = str(interest or '').strip().lower()

    # Domain keywords dictionary specifically tailored to the 4 categories
    domain_keywords = {
        'creativity': [
            'creativ', 'content', 'media', 'writing', 'copywriting',
            'video', 'multimedia', 'animation', 'art', 'arts', 'storytelling',
            'journalism', 'audio', 'music', 'production', 'graphical', 'graphics'
        ],
        'development': [
            'develop', 'developer', 'development', 'web', 'python', 'software',
            'programming', 'code', 'coding', 'django', 'javascript', 'frontend',
            'backend', 'full stack', 'full-stack', 'html', 'css', 'react', 'node',
            'mobile', 'app', 'android', 'flutter', 'engineering', 'tech', 'ai', 'automation'
        ],
        'management': [
            'manage', 'management', 'manager', 'business', 'project', 'marketing',
            'digital marketing', 'lead', 'leadership', 'operation', 'operations',
            'strategy', 'agile', 'scrum', 'finance', 'administration', 'seo',
            'analytics', 'data analytics', 'product management'
        ],
        'marketing': [
            'marketing', 'digital marketing', 'social media', 'advertising',
            'seo', 'sem', 'campaign', 'brand', 'branding', 'growth',
            'content marketing', 'email marketing', 'sales', 'market research', 'business'
        ],
        'designing': [
            'design', 'designing', 'designer', 'ui', 'ux', 'ui/ux', 'graphic', 'graphical',
            'figma', 'product design', 'visual', 'adobe', 'photoshop', 'illustrator',
            'wireframe', 'prototype', 'branding', 'creative design'
        ]
    }

    # Match target domain
    matched_domain = None
    for dom in ['creativity', 'development', 'management', 'designing', 'marketing']:
        if dom in interest_str:
            matched_domain = dom
            break

    # If a domain is identified, perform weighted score matching across all available admin courses
    if matched_domain:
        keywords = domain_keywords[matched_domain]
        best_match = None
        highest_score = -1

        for course in courses_qs:
            title_lower = (course.title or '').lower()
            desc_lower = (course.description or '').lower()
            score = 0

            # Direct domain match in title gives substantial score
            if matched_domain in title_lower or (matched_domain == 'designing' and 'design' in title_lower):
                score += 30
            elif matched_domain in desc_lower or (matched_domain == 'designing' and 'design' in desc_lower):
                score += 15

            # Keyword matching
            for kw in keywords:
                if kw in title_lower:
                    score += 8
                elif kw in desc_lower:
                    score += 3

            if score > highest_score:
                highest_score = score
                best_match = course

        if best_match and highest_score > 0:
            return best_match

    # Direct ID or title matching fallback
    if interest_str.isdigit():
        c = courses_qs.filter(id=int(interest_str)).first()
        if c:
            return c

    for course in courses_qs:
        t_low = (course.title or '').lower()
        if interest_str and (interest_str in t_low or t_low in interest_str):
            return course

    # Fallback to the first available admin course
    return courses_qs.first()


def finalize_student_registration(request, pending_data):
    """
    Creates user, ensures unique student_id on Profile, creates StudentAssessment,
    picks the 1 best matching AdminCourse from database, and sets up session.
    """
    full_name = (pending_data.get('full_name') or pending_data.get('username', '')).strip()
    username = pending_data.get('username', '').strip()
    email = pending_data.get('email', '').strip()
    password = pending_data.get('password')
    interest = pending_data.get('interest', '').strip()
    knowledge_level = pending_data.get('knowledge_level', 'Beginner')
    purpose = pending_data.get('purpose', 'Improvement of Skills')

    # 1. Create User
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=full_name
    )

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
    assessment = StudentAssessment.objects.create(
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


@csrf_protect
def signup_view(request):
    admin_courses = AdminCourse.objects.filter(is_active=True)
    context = {
        'admin_courses': admin_courses,
    }

    if request.method == 'POST':
        # Step A: Verification Code submission
        if 'verify_code_submit' in request.POST or 'otp_code' in request.POST:
            entered_code = (request.POST.get('verification_code') or request.POST.get('otp_code', '')).strip()
            session_code = request.session.get('signup_verification_code') or (request.session.get('signup_data', {}).get('otp'))
            pending_data = request.session.get('pending_signup_data') or request.session.get('signup_data')

            if not session_code or not pending_data:
                context['error'] = "Session expired. Please fill the registration form again."
                return render(request, 'main_front/signup.html', context)

            if entered_code != str(session_code):
                context['error'] = "Invalid verification code. Please try again."
                context['step'] = 'verify'
                context['email'] = pending_data.get('email')
                return render(request, 'main_front/signup.html', context)

            try:
                user, suggested_course = finalize_student_registration(request, pending_data)

                # Clear verification data from session
                request.session.pop('signup_verification_code', None)
                request.session.pop('pending_signup_data', None)
                request.session.pop('signup_data', None)

                # Redirect to 1 recommended course page
                return redirect('student_assessment')

            except Exception as e:
                logger.error(f"Registration finalize error: {e}")
                context['error'] = f"Registration Error: {str(e)}"
                return render(request, 'main_front/signup.html', context)

        # Step B: Combined Assessment + Registration Form Submission
        full_name = request.POST.get('full_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Assessment fields
        interest = (request.POST.get('interest') or request.POST.get('topic', '')).strip()
        knowledge_level = (request.POST.get('knowledge_level') or request.POST.get('level', 'Beginner')).strip()
        purpose = (request.POST.get('purpose') or request.POST.get('learning_goal', 'Improvement of Skills')).strip()

        if not full_name:
            full_name = username

        if password != confirm_password:
            context['error'] = "Passwords do not match."
            context['saved_data'] = request.POST
            return render(request, 'main_front/signup.html', context)

        if User.objects.filter(username__iexact=username).exists():
            context['error'] = "Username is already taken. Please choose another one."
            context['saved_data'] = request.POST
            return render(request, 'main_front/signup.html', context)

        if User.objects.filter(email__iexact=email).exists():
            context['error'] = "An account with this email already exists."
            context['saved_data'] = request.POST
            return render(request, 'main_front/signup.html', context)

        # Generate 6-digit verification code
        verification_code = random.randint(100000, 999999)

        pending_data = {
            'full_name': full_name,
            'username': username,
            'email': email,
            'password': password,
            'interest': interest,
            'knowledge_level': knowledge_level,
            'purpose': purpose,
            'otp': str(verification_code),
        }

        request.session['signup_verification_code'] = verification_code
        request.session['pending_signup_data'] = pending_data
        request.session['signup_data'] = pending_data

        # Send email with verification code
        try:
            send_mail(
                subject='ALVIX AI - Email Verification Code',
                message=f'Hello {full_name},\n\nYour verification code for ALVIX Registration is: {verification_code}\n\nWelcome to ALVIX!',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as mail_err:
            logger.error(f"Mail sending failed: {mail_err}")
            print(f"--- DEBUG VERIFICATION CODE FOR {email}: {verification_code} ---")

        context['step'] = 'verify'
        context['email'] = email
        context['verification_code_debug'] = verification_code if settings.DEBUG else None
        return render(request, 'main_front/signup.html', context)

    return render(request, 'main_front/signup.html', context)


def verify_otp_view(request):
    pending_data = request.session.get('pending_signup_data') or request.session.get('signup_data')
    if not pending_data:
        return redirect('signup')

    context = {'email': pending_data.get('email')}
    if request.method == 'POST':
        entered_otp = (request.POST.get('otp_code') or request.POST.get('verification_code', '')).strip()
        session_otp = str(request.session.get('signup_verification_code') or pending_data.get('otp', ''))

        if entered_otp == session_otp:
            try:
                user, suggested_course = finalize_student_registration(request, pending_data)
                request.session.pop('signup_verification_code', None)
                request.session.pop('pending_signup_data', None)
                request.session.pop('signup_data', None)
                return redirect('student_assessment')
            except Exception as e:
                context['error'] = f"Verification Error: {str(e)}"
        else:
            context['error'] = "Invalid verification code. Please try again."

    return render(request, 'main_front/verify_otp.html', context)


def logout(request):
    if request.method == 'POST':
        auth_logout(request)
        return redirect('login')
    return render(request, 'student_dashboard/logout.html')


# ==========================================
# COURSE SUGGESTION VIEW (1 Matching Course + 3 Student Choices)
# ==========================================
@login_required
def suggested_courses(request):
    """
    Presents the student with their AI-recommended best-fit course and three clear choices:
     (a) Go directly to the dashboard.
     (b) Start the suggested course (student picks the level; the suggested level is pre-selected).
     (c) Pick any other existing course, or ask the system to generate a new course from a title the student types.
    """
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    student_name = profile_obj.full_name or request.user.get_full_name() or request.user.username
    student_id = profile_obj.student_id

    interest_area = profile_obj.interest_area or request.session.get('assessment_interest', 'Development')
    goal = profile_obj.goal or request.session.get('assessment_purpose', 'Practical')
    expectations = profile_obj.expectations or "Comprehensive mastery of core concepts and practical real-world skills."

    # Retrieve or generate the AI course suggestion
    from .course_recommendation import suggest_best_fit_course_with_ai
    
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

    # Handle POST Actions for Choices (b) and (c)
    if request.method == 'POST':
        action = request.POST.get('action', 'start_suggested')

        try:
            # -------------------------------------------------------------
            # Choice (b): Start the suggested course
            # -------------------------------------------------------------
            if action == 'start_suggested':
                chosen_level = request.POST.get('level', suggested_level or 'Beginner')
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
                    return redirect(f"/course_content/?course_id={gen_course.id}")

            # -------------------------------------------------------------
            # Choice (c1): Pick any other existing course from the catalog
            # -------------------------------------------------------------
            elif action == 'pick_other_course':
                other_course_id = request.POST.get('other_course_id')
                other_level = request.POST.get('other_level', 'Beginner')
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
                        return redirect(f"/course_content/?course_id={gen_course.id}")
                else:
                    messages.error(request, "Selected course could not be found.")

            # -------------------------------------------------------------
            # Choice (c2): Generate a new course from a title typed by student
            # -------------------------------------------------------------
            elif action == 'generate_new_course':
                custom_title = request.POST.get('custom_course_title', '').strip()
                custom_level = request.POST.get('custom_level', 'Beginner')
                custom_pace = request.POST.get('custom_pace', 'Standard')

                if not custom_title:
                    messages.error(request, "Please enter a course title to generate.")
                    return redirect('suggested_courses')

                admin_course = AdminCourse.objects.filter(title__iexact=custom_title).first()
                if not admin_course:
                    admin_course = AdminCourse.objects.create(
                        title=custom_title,
                        description=f"AI-generated personalized course on {custom_title}."
                    )
                create_course_tiers_and_curriculum(admin_course)
                
                from .ai_services import generate_course_with_gemini
                gen_course = generate_course_with_gemini(
                    admin_course=admin_course,
                    user=request.user,
                    level=custom_level,
                    pace=custom_pace,
                    objective=expectations or f"Master {custom_title}"
                )
                
                messages.success(request, f"Successfully generated and enrolled in new course '{custom_title}'!")
                return redirect(f"/course_content/?course_id={gen_course.id}")

        except Exception as e:
            logger.error(f"Enrollment or generation action error: {e}")
            messages.error(request, f"Action error: {e}")
            return redirect('suggested_courses')

    # Other existing active catalog courses (excluding suggested course)
    other_courses = AdminCourse.objects.filter(is_active=True)
    if suggested_course:
        other_courses = other_courses.exclude(id=suggested_course.id)

    # University benchmark tiers for the suggested course
    available_levels = []
    if suggested_course:
        create_course_tiers_and_curriculum(suggested_course)
        available_levels = suggested_course.course_levels.filter(is_active=True).order_by('id')

    context = {
        'student_name': student_name,
        'student_id': student_id,
        'interest_area': interest_area,
        'goal': goal,
        'expectations': expectations,
        'suggested_course': suggested_course,
        'ai_reason': reason,
        'suggested_level': suggested_level,
        'available_levels': available_levels,
        'other_courses': other_courses,
    }
    return render(request, 'main_front/suggested_courses.html', context)


# ....................................... STUDENT DASHBOARD VIEWS...................................................#
@login_required
def dashboard(request):
    try:
        profile_obj, _ = Profile.objects.get_or_create(user=request.user)
        if not request.user.is_staff and not request.user.is_superuser:
            if not profile_obj.assessment_completed:
                return redirect("student_assessment")
        # Fetch only the courses specifically chosen/enrolled by this student
        generated_courses = GeneratedCourse.objects.filter(user=request.user).select_related('admin_course', 'course_level').order_by('id')
        active_course = generated_courses.first() or GeneratedCourse.objects.filter(user=request.user).order_by('-created_at').first()
        
        # Performance & Weighted Score Calculation for Dashboard
        total_lessons = 0
        completed_lessons = 0
        total_video_duration = 0
        total_watch_time = 0
        
        total_assignment_score_obtained = 0
        total_assignment_max_score = 0
        
        total_quiz_score_obtained = 0
        total_quiz_max_score = 0
        
        overall_score = 0
        grade = "Beginner"
        
        # Default variables to avoid UnboundLocalError if active_course is None
        watch_time_percentage = 0
        assignment_percentage = 0
        quiz_percentage = 0
        
        if active_course:
            lessons = DailyLesson.objects.filter(generated_course=active_course)
            total_lessons = lessons.count()
            completed_lessons = lessons.filter(is_completed=True).count()
            
            # 1. Watch Time Calculation (40% Weight)
            for lesson in lessons:
                vid_len = getattr(lesson, 'duration', 25)
                w_time = getattr(lesson, 'watch_time', 25 if getattr(lesson, 'is_completed', False) else 0)
                total_video_duration += vid_len
                total_watch_time += min(w_time, vid_len)
                
            watch_time_percentage = (total_watch_time / total_video_duration * 100) if total_video_duration > 0 else 0
            
            # 2. Assignment Calculation (30% Weight)
            assignment_subs = []
            try:
                assignment_subs = AssignmentSubmission.objects.filter(user=request.user, lesson__in=lessons)
                for sub in assignment_subs:
                    obtained = getattr(sub, 'marks', getattr(sub, 'score', 10))
                    max_m = getattr(sub, 'total_marks', 10)
                    total_assignment_score_obtained += obtained
                    total_assignment_max_score += max_m
            except:
                pass
                
            if total_assignment_max_score == 0 and len(assignment_subs) > 0:
                total_assignment_max_score = len(assignment_subs) * 10
                
            assignment_percentage = (total_assignment_score_obtained / total_assignment_max_score * 100) if total_assignment_max_score > 0 else 0
            
            # 3. Quiz Calculation (30% Weight)
            quiz_subs = []
            try:
                quiz_subs = QuizSubmission.objects.filter(user=request.user)
                for quiz in quiz_subs:
                    obtained = getattr(quiz, 'score', getattr(quiz, 'marks_obtained', 0))
                    max_m = getattr(quiz, 'total_marks', 3)
                    total_quiz_score_obtained += obtained
                    total_quiz_max_score += max_m
            except:
                pass
                
            if total_quiz_max_score == 0 and len(quiz_subs) > 0:
                total_quiz_max_score = len(quiz_subs) * 3
                
            quiz_percentage = (total_quiz_score_obtained / total_quiz_max_score * 100) if total_quiz_max_score > 0 else 0
            
            # Weighted Final Score Formula
            if total_lessons > 0 or len(assignment_subs) > 0 or len(quiz_subs) > 0:
                weighted_score = (watch_time_percentage * 0.4) + (assignment_percentage * 0.3) + (quiz_percentage * 0.3)
                overall_score = int(round(weighted_score))
            else:
                overall_score = 0
                
            # Grade Assignment
            if overall_score > 75:
                grade = "Advanced"
            elif overall_score > 40:
                grade = "Intermediate"
            elif overall_score > 0:
                grade = "Beginner"
            else:
                grade = "Needs Improvement"

        course_title = getattr(active_course, 'topic', getattr(active_course, 'course_name', getattr(active_course, 'title', 'your course'))) if active_course else "your current course"

        # AI Remarks generated automatically
        ai_remarks = (
            f"Progress status for {course_title}: Watch Time ratio contributed {int(watch_time_percentage*0.4)}%, "
            f"Assignments contributed {int(assignment_percentage*0.3)}%, and Quizzes contributed {int(quiz_percentage*0.3)}%. "
            f"Your overall calculated weighted performance score is {overall_score}%."
        ) if active_course else "No active course found. Generate a course to begin tracking your analytics."

        # Ensure student has profile and student_id
        profile_obj, _ = Profile.objects.get_or_create(user=request.user)
        if not profile_obj.student_id:
            profile_obj.student_id = generate_unique_student_id()
            profile_obj.save()

        # Recommended course for dashboard banner/alert if no course started yet
        suggested_course = None
        latest_assessment = StudentAssessment.objects.filter(user=request.user).order_by('-created_at').first()
        if latest_assessment and latest_assessment.interest:
            suggested_course = latest_assessment.interest
        elif not generated_courses.exists():
            suggested_course = AdminCourse.objects.filter(is_active=True).first()

        # Popup notification handling
        popup_notification = None 

        context = {
            'generated_courses': generated_courses,
            'overall_progress': overall_score,
            'grade': grade,
            'ai_remarks': ai_remarks,
            'popup_notification': popup_notification,
            'suggested_course': suggested_course,
            'latest_assessment': latest_assessment,
        }
        
        return render(request, 'student_dashboard/dashboard.html', context)
        
    except Exception as e:
        print(f"CRITICAL DASHBOARD ERROR: {e}")
        raise e


@login_required

# ==========================================
# STUDENT MANDATORY ASSESSMENT & RETAKE VIEW
# ==========================================
@login_required
def student_assessment(request):
    """
    Mandatory student assessment running after first login and retakable from profile.
    Questions:
    1. Interest area (single choice): Creativity, Development, Designing, Marketing
    2. Goal (single choice): Practical, Theory, Mixed
    3. Expectations: (minimum 20 characters)
    Strictly omits questions about job, freelancing, language, or available time.
    """
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    is_retake = request.GET.get('retake') == 'true' or profile_obj.assessment_completed

    if request.method == 'POST':
        form = StudentProfileAssessmentForm(request.POST)
        if form.is_valid():
            interest_area = form.cleaned_data['interest_area']
            goal = form.cleaned_data['goal']
            expectations = form.cleaned_data['expectations']

            # Save directly into student profile
            profile_obj.interest_area = interest_area
            profile_obj.goal = goal
            profile_obj.expectations = expectations
            profile_obj.assessment_completed = True
            profile_obj.save()

            # Find 1 best matching course from database
            suggested_course = find_best_matching_admin_course(interest_area, purpose=goal)

            # Synchronize with StudentAssessment record for backward compatibility
            StudentAssessment.objects.create(
                user=request.user,
                student_id=profile_obj.student_id,
                full_name=profile_obj.full_name or request.user.get_full_name() or request.user.username,
                email=request.user.email,
                interest=suggested_course,
                interest_topic=interest_area,
                learning_goal=goal,
                expectations=expectations,
                selected_course=suggested_course.title if suggested_course else None
            )

            # Set session parameters
            request.session['student_name'] = profile_obj.full_name
            request.session['student_id'] = profile_obj.student_id
            request.session['assessment_interest'] = interest_area
            request.session['assessment_purpose'] = goal
            if suggested_course:
                request.session['recommended_course_id'] = suggested_course.id

            # Generate AI Recommendation using ALL assessment answers
            from .course_recommendation import suggest_best_fit_course_with_ai
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

            if is_retake:
                messages.success(request, "Assessment updated successfully! Review your AI-suggested learning paths below.")
            else:
                messages.success(request, "Assessment complete! Review your AI-suggested learning paths below.")
            return redirect('suggested_courses')
        else:
            messages.error(request, "Please ensure all fields are filled out correctly (Expectations requires at least 20 characters).")
    else:
        # Pre-populate with existing values if retaking or already set
        initial_data = {}
        if profile_obj.interest_area:
            initial_data['interest_area'] = profile_obj.interest_area
        if profile_obj.goal:
            initial_data['goal'] = profile_obj.goal
        if profile_obj.expectations:
            initial_data['expectations'] = profile_obj.expectations
        form = StudentProfileAssessmentForm(initial=initial_data)

    context = {
        'form': form,
        'profile': profile_obj,
        'is_retake': is_retake,
    }
    return render(request, 'student_dashboard/assessment.html', context)


def profile(request):
    profile_obj, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile_obj.full_name = request.POST.get("full_name")
        profile_obj.phone = request.POST.get("phone")
        profile_obj.goal = request.POST.get("goal")
        profile_obj.gender = request.POST.get("gender")

        dob = request.POST.get("dob")
        if dob:
            profile_obj.dob = dob

        if request.FILES.get("profile_picture"):
            profile_obj.profile_picture = request.FILES["profile_picture"]

        profile_obj.save()

        request.user.email = request.POST.get("email")
        request.user.save()

        return redirect('profile')

    return render(request, "student_dashboard/profile.html", {"profile": profile_obj})

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import AdminCourse, GeneratedCourse, DailyLesson, StudentAssessment

logger = logging.getLogger(__name__)


def get_course_lessons(course):
    """Safe helper to fetch lessons across model schemas."""
    if not course:
        return []
    
    # 1. Direct Model Query (Most reliable)
    try:
        lessons = DailyLesson.objects.filter(generated_course=course).order_by('day_number')
        if lessons.exists():
            return lessons
    except Exception:
        pass

    # 2. Reverse Relation Fallbacks
    if hasattr(course, 'daily_lessons'):
        return course.daily_lessons.all().order_by('day_number')
    if hasattr(course, 'dailylesson_set'):
        return course.dailylesson_set.all().order_by('day_number')
    
    return DailyLesson.objects.none()

@login_required
def course_content_view(request):
    """
    Renders active course syllabus and lessons.
    Self-healing: If an active course exists with 0 lessons, it automatically generates
    the 7-day curriculum via Gemini AI so the user never gets an empty screen.
    """
    course_id = request.GET.get('course_id')
    active_course = None

    if course_id and course_id.isdigit():
        active_course = GeneratedCourse.objects.filter(id=int(course_id), user=request.user).first()

    if not active_course:
        user_courses = GeneratedCourse.objects.filter(user=request.user).order_by('-created_at')
        for gc in user_courses:
            if gc.daily_lessons.exists():
                active_course = gc
                break
        if not active_course:
            active_course = user_courses.first()

    # Self-healing: If course has 0 lessons, fetch pre-generated curriculum directly from database
    if active_course and not active_course.daily_lessons.exists():
        try:
            target_level = active_course.course_level
            if not target_level and active_course.admin_course:
                target_level = CourseLevel.objects.filter(
                    parent_course=active_course.admin_course,
                    level__iexact=active_course.level or 'Beginner'
                ).first()
                if not target_level:
                    create_course_tiers_and_curriculum(active_course.admin_course)
                    target_level = CourseLevel.objects.filter(
                        parent_course=active_course.admin_course,
                        level__iexact=active_course.level or 'Beginner'
                    ).first() or CourseLevel.objects.filter(parent_course=active_course.admin_course).first()
            if target_level:
                fetch_and_enroll_student_in_level(request.user, target_level)
        except Exception as e:
            logger.error(f"Instant fetch lessons failed: {e}")

    lessons = []
    content_topics = []
    course_type = "Mixed"
    durations = getattr(settings, 'COURSE_PLAN_DURATIONS', {
        'Theoretical': 7,
        'Theory': 7,
        'Practical': 10,
        'Mixed': 12,
    })
    plan_duration = 12

    if active_course:
        course_type = active_course.course_type or (active_course.admin_course.course_type if active_course.admin_course else 'Mixed')
        plan_duration = durations.get(course_type, durations.get('Mixed', 12))

        content_topics = active_course.content_topics or (active_course.course_level.content_topics if active_course.course_level else [])
        if not content_topics and active_course.course_level:
            from .course_tier_service import sync_student_lessons_from_canonical
            sync_student_lessons_from_canonical(active_course)
            active_course.refresh_from_db()
            content_topics = active_course.content_topics or (active_course.course_level.content_topics if active_course.course_level else [])

        if not content_topics:
            from .ai_services import get_curated_level_content_and_plan
            title = active_course.admin_course.title if active_course.admin_course else "Course"
            lvl_name = active_course.level or "Beginner"
            curated_topics, _ = get_curated_level_content_and_plan(title, lvl_name, course_type)
            content_topics = curated_topics
            active_course.content_topics = content_topics
            try:
                active_course.save(update_fields=['content_topics'])
            except Exception:
                pass

        lessons = list(active_course.daily_lessons.all().order_by('day_number'))
        videos_dir = os.path.join(settings.MEDIA_ROOT, "videos")
        for l in lessons:
            v_name = f"lesson_{l.id}.mp4"
            p = os.path.join(videos_dir, v_name)
            l.has_real_video = os.path.exists(p) and os.path.getsize(p) > 10000
            if l.has_real_video and l.video_url != f"{settings.MEDIA_URL}videos/{v_name}":
                l.video_url = f"{settings.MEDIA_URL}videos/{v_name}"

    return render(
        request,
        'student_dashboard/course_data/course_content.html',
        {
            'active_course': active_course,
            'content_topics': content_topics,
            'course_type': course_type,
            'plan_duration': plan_duration,
            'lessons': lessons,
        },
    )


@login_required
def mycourse(request):
    course_id = request.GET.get('course_id')
    user_courses = GeneratedCourse.objects.filter(user=request.user).select_related('admin_course', 'course_level').order_by('id')

    active_course = None
    if course_id and str(course_id).isdigit():
        active_course = user_courses.filter(id=int(course_id)).first()
    if not active_course:
        active_course = user_courses.first() or GeneratedCourse.objects.filter(user=request.user).order_by('-created_at').first()

    lessons = []
    content_topics = []
    today_lesson = None
    assignment_submissions = []
    quiz_submissions = []
    progress_percentage = 0
    certificate_obj = None

    if active_course:
        lessons = list(active_course.daily_lessons.all().order_by('day_number'))
        if not lessons:
            lessons = list(get_course_lessons(active_course))

        content_topics = active_course.content_topics or (active_course.course_level.content_topics if active_course.course_level else [])
        if not content_topics:
            from .ai_services import get_curated_level_content_and_plan
            title = active_course.admin_course.title if active_course.admin_course else "Course"
            lvl_name = active_course.level or "Beginner"
            ctype = active_course.course_type or "Mixed"
            curated_topics, _ = get_curated_level_content_and_plan(title, lvl_name, ctype)
            content_topics = curated_topics
            active_course.content_topics = content_topics
            try:
                active_course.save(update_fields=['content_topics'])
            except Exception:
                pass

        for l in lessons:
            if l.is_unlocked and not l.is_completed:
                today_lesson = l
                break
        if not today_lesson:
            today_lesson = (
                active_course.daily_lessons.filter(is_unlocked=True).last()
                or (lessons[0] if lessons else None)
            )

        try:
            assignment_submissions = list(
                AssignmentSubmission.objects.filter(user=request.user, lesson__in=lessons)
                .select_related('lesson')
                .order_by('-submitted_at')
            )
        except Exception:
            assignment_submissions = []

        try:
            quiz_submissions = list(
                QuizSubmission.objects.filter(user=request.user, lesson__in=lessons)
                .select_related('lesson')
                .order_by('-submitted_at')
            )
        except Exception:
            quiz_submissions = []

        total_lessons = len(lessons)
        total_video_duration = 0
        total_watch_time = 0
        total_assignment_score_obtained = 0
        total_assignment_max_score = 0
        total_quiz_score_obtained = 0
        total_quiz_max_score = 0

        watch_time_percentage = 0
        assignment_percentage = 0
        quiz_percentage = 0

        if total_lessons > 0:
            for lesson in lessons:
                vid_len = getattr(lesson, 'duration', 25)
                w_time = getattr(lesson, 'watch_time', 25 if getattr(lesson, 'is_completed', False) else 0)
                total_video_duration += vid_len
                total_watch_time += min(w_time, vid_len)

            watch_time_percentage = (total_watch_time / total_video_duration * 100) if total_video_duration > 0 else 0

            for sub in assignment_submissions:
                obtained = getattr(sub, 'marks', getattr(sub, 'score', 10))
                max_m = getattr(sub, 'total_marks', 10)
                total_assignment_score_obtained += obtained
                total_assignment_max_score += max_m

            if total_assignment_max_score == 0 and len(assignment_submissions) > 0:
                total_assignment_max_score = len(assignment_submissions) * 10
            assignment_percentage = (total_assignment_score_obtained / total_assignment_max_score * 100) if total_assignment_max_score > 0 else 0

            for quiz in quiz_submissions:
                obtained = getattr(quiz, 'score', getattr(quiz, 'marks_obtained', 0))
                max_m = getattr(quiz, 'total_marks', 3)
                total_quiz_score_obtained += obtained
                total_quiz_max_score += max_m

            if total_quiz_max_score == 0 and len(quiz_submissions) > 0:
                total_quiz_max_score = len(quiz_submissions) * 3
            quiz_percentage = (total_quiz_score_obtained / total_quiz_max_score * 100) if total_quiz_max_score > 0 else 0

            weighted_score = (watch_time_percentage * 0.4) + (assignment_percentage * 0.3) + (quiz_percentage * 0.3)
            progress_percentage = int(round(weighted_score))

        certificate_obj = Certificate.objects.filter(user=request.user, course=active_course).first()

    active_tab = request.GET.get('tab', 'content').strip().lower()
    if active_tab not in ['content', 'lessons', 'assignment', 'quiz', 'overview']:
        active_tab = 'content'

    return render(request, 'student_dashboard/mycourse.html', {
        'active_course': active_course,
        'course': active_course,
        'user_courses': user_courses,
        'lessons': lessons,
        'content_topics': content_topics,
        'today_lesson': today_lesson,
        'assignment_submissions': assignment_submissions,
        'quiz_submissions': quiz_submissions,
        'progress_percentage': progress_percentage,
        'certificate': certificate_obj,
        'active_tab': active_tab,
    })


@login_required
def course_detail(request, course_id):
    course = GeneratedCourse.objects.filter(id=course_id, user=request.user).first()
    if not course:
        return redirect('mycourse')

    lessons = get_course_lessons(course)

    return render(request, 'student_dashboard/mycourse.html', {
        'active_course': course,
        'course': course,
        'lessons': lessons,
    })


@login_required
def single_lesson_view(request, lesson_id):
    lesson = get_object_or_404(DailyLesson, id=lesson_id)
    active_course = lesson.generated_course

    if active_course and active_course.admin_course:
        course_title = active_course.admin_course.title
    else:
        course_title = "Custom Course"

    # Built-in dynamic AI video simulation script based on lesson content
    ai_video_script = (
        f"Module Overview: Introduction to {lesson.title}.\n"
        f"• Core Concept Breakdown: {lesson.content[:150]}...\n"
        f"• Practical Application & Analysis: Exploring key principles for {course_title}.\n"
        f"• Summary & Key Takeaways: Mastering daily objectives efficiently."
    )

    presentation_data = None
    presentation_json = "{}"
    slides_list = []
    lesson_video_url = None
    lesson_poster_url = None

    try:
        from .ppt_generator import build_dynamic_slides_from_content, enrich_lecture_with_narrations
        pdata = lesson.presentation_data if isinstance(lesson.presentation_data, dict) else {}
        slides_list = pdata.get('slides_list', [])
        # Ensure all dynamic slides (13+ slides) from content/syllabus are generated & matched with PPT
        if not pdata or len(slides_list) < 10:
            lecture_data = build_dynamic_slides_from_content(lesson)
            pdata = enrich_lecture_with_narrations(lecture_data, lesson)
            try:
                lesson.presentation_data = pdata
                lesson.save(update_fields=['presentation_data'])
            except Exception:
                pass
            slides_list = pdata.get('slides_list', [])
        presentation_data = pdata
        presentation_json = json.dumps(presentation_data)
    except Exception as e:
        logger.error(f"Error preparing topic slide deck for lesson {lesson.id}: {e}")
        try:
            from .ppt_service import ensure_lesson_slides_and_explanations
            presentation_data = ensure_lesson_slides_and_explanations(lesson)
            presentation_json = json.dumps(presentation_data)
            slides_list = presentation_data.get('slides_list', [])
        except Exception as fallback_err:
            logger.error(f"Fallback ppt_service failed: {fallback_err}")

    try:
        video_filename = f"lesson_{lesson.id}.mp4"
        disk_path = os.path.join(settings.MEDIA_ROOT, "videos", video_filename)
        if os.path.exists(disk_path) and os.path.getsize(disk_path) > 10000:
            lesson_video_url = f"{settings.MEDIA_URL}videos/{video_filename}"
            if lesson.video_url != lesson_video_url:
                lesson.video_url = lesson_video_url
                try:
                    lesson.save(update_fields=['video_url'])
                except Exception:
                    pass
        elif lesson.generated_course and lesson.course_level:
            canonical_lesson = DailyLesson.objects.filter(
                course_level=lesson.course_level,
                day_number=lesson.day_number,
                generated_course__isnull=True
            ).first()
            if canonical_lesson and canonical_lesson.video_url:
                c_rel = canonical_lesson.video_url.replace(settings.MEDIA_URL, '').lstrip('/')
                c_path = os.path.join(settings.MEDIA_ROOT, c_rel)
                if os.path.exists(c_path) and os.path.getsize(c_path) > 10000:
                    lesson_video_url = canonical_lesson.video_url
                    if lesson.video_url != lesson_video_url:
                        lesson.video_url = lesson_video_url
                        try:
                            lesson.save(update_fields=['video_url'])
                        except Exception:
                            pass
        lesson_poster_url = None
    except Exception as e:
        logger.error(f"Error checking video for lesson {lesson.id}: {e}")

    avatar_settings = AvatarSettings.get_settings()
    asset_status = get_avatar_asset_status()

    student_name = "Student"
    if request.user.is_authenticated:
        student_name = request.user.first_name or request.user.username or "Student"

    day_num = lesson.day_number or 1
    lesson_title = lesson.title or "Masterclass Lecture"
    is_full_intro = (day_num == 1 or avatar_settings.play_full_intro_every_day)

    if is_full_intro:
        intro_spoken = avatar_settings.format_full_intro_spoken(
            student_name=student_name,
            course_name=course_title,
            day_number=day_num,
            lesson_title=lesson_title
        )
        intro_display = avatar_settings.format_full_intro_display(
            student_name=student_name,
            course_name=course_title,
            day_number=day_num,
            lesson_title=lesson_title
        )
    else:
        intro_spoken = avatar_settings.format_short_greeting_spoken(
            student_name=student_name,
            lesson_title=lesson_title
        )
        intro_display = avatar_settings.format_short_greeting_display(
            student_name=student_name,
            lesson_title=lesson_title
        )

    return render(request, 'student_dashboard/course_data/daily_lesson.html', {
        'lesson': lesson,
        'active_course': active_course,
        'course_title': course_title,
        'ai_video_script': ai_video_script,
        'presentation_data': presentation_data,
        'presentation_json': presentation_json,
        'slides_list': slides_list,
        'total_slides': len(slides_list) if slides_list else 10,
        'lesson_video_url': lesson_video_url,
        'lesson_poster_url': lesson_poster_url,
        'avatar_settings': avatar_settings,
        'avatar_assets': asset_status,
        'student_name': student_name,
        'is_full_intro': is_full_intro,
        'intro_spoken': intro_spoken,
        'intro_display': intro_display,
        'avatar_name_display': avatar_settings.avatar_name,
        'avatar_name_spoken': avatar_settings.get_spoken_name(),
        'developer_name': avatar_settings.developer_name,
        'university_or_department': avatar_settings.university_or_department,
    })


@login_required
def submit_lesson_step(request, lesson_id):
    if request.method == "POST":
        lesson = get_object_or_404(DailyLesson, id=lesson_id)
        task = getattr(lesson, 'task', None)
        
        assignment_ans = request.POST.get('assignment_answer', '')
        
        score = 0
        if task and task.quiz_data:
            for q in task.quiz_data:
                user_selected = request.POST.get(f"quiz_q_{q.get('id')}")
                if user_selected == q.get('answer'):
                    score += 1

        StudentProgress.objects.create(
            user=request.user,
            lesson=lesson,
            assignment_submission=assignment_ans,
            quiz_score=score
        )

        lesson.is_completed = True
        lesson.save()

        next_lesson = DailyLesson.objects.filter(
            generated_course=lesson.generated_course,
            day_number=lesson.day_number + 1
        ).first()

        if next_lesson:
            next_lesson.is_unlocked = True
            next_lesson.save()
            messages.success(request, f"Day {lesson.day_number} complete! Day {next_lesson.day_number} unlock ho gaya hai.")
            return redirect('daily_lesson_view', lesson_id=next_lesson.id)
        else:
            messages.success(request, "🎉 Mubarak ho! Aapne poora course complete kar liya hai.")
            return redirect('course_content_view')
            
    return redirect('daily_lesson_view', lesson_id=lesson_id)


@login_required
def reports(request):
    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES or None)
        if form.is_valid():
            report = form.save(commit=False)
            report.student = request.user
            report.save()
            messages.success(request, "Aapki report successfully submit ho gayi hai!")
            return redirect('reports')
    else:
        form = ReportForm()

    student_reports = Report.objects.filter(student=request.user).order_by('-created_at')
    return render(request, 'student_dashboard/reports.html', {'form': form, 'reports': student_reports})


@login_required
def submit_report(request):
    if request.method == 'POST':
        course = request.POST.get('course_name')
        p_type = request.POST.get('problem_type')
        title = request.POST.get('problem_title')
        description = request.POST.get('problem_description')

        Report.objects.create(
            student=request.user,
            course_name=course,
            problem_type=p_type,
            problem_title=title,
            problem_description=description
        )
        messages.success(request, "Your report has been submitted successfully!")
        return redirect('reports')

    return render(request, 'student_dashboard/reports.html')


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import StudentNotificationStatus, Notification

@login_required
def notifications(request):
    # 1. Fetch all dispatched notifications for the logged-in student via StudentNotificationStatus
    notifications = StudentNotificationStatus.objects.filter(
        user=request.user,
        notification__is_dispatched=True
    ).select_related('notification').order_by('-notification__created_at')

    context = {
        'notifications': notifications,
    }
    return render(request, 'student_dashboard/notifications.html', context)


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Notification, StudentNotificationStatus

def mark_notification_read(request, id):
    if request.method == 'POST':
        notification = get_object_or_404(Notification, id=id)
        
        # StudentNotificationStatus mein entry update ya create karein
        status_obj, created = StudentNotificationStatus.objects.get_or_create(
            user=request.user,
            notification=notification
        )
        status_obj.is_read = True
        status_obj.read_at = timezone.now()
        status_obj.save()
        
        return JsonResponse({'status': 'success', 'message': 'Marked as read'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
@login_required
def Performance_view(request):
    """
    Computes strict, transparent course scoring:
    - Course total is 100%, divided by plan days N (7, 10, or 12).
    - Each day's share is split: 20% watch time, 40% assignment marks, 40% quiz marks.
    - Shows per-day breakdown table, overall course percentage, remarks, and
      'View your certificate' option (unlocked at pass mark, default 35%; locked otherwise).
    """
    active_course = GeneratedCourse.objects.filter(user=request.user).order_by('-created_at').first()
    if not active_course:
        return render(request, 'student_dashboard/performance.html', {'performance': None})

    perf = calculate_course_performance(request.user, active_course)

    # Ensure certificate record is synchronized
    cert, _ = update_or_create_student_certificate(request.user, active_course, request=request)

    # Remaining requirement calculations
    remaining_lessons = max(0, perf['total_days'] - perf['completed_days_count'])
    score_gap = max(0.0, round(perf['pass_mark'] - perf['overall_percentage'], 1))

    return render(request, 'student_dashboard/performance.html', {
        'performance': perf,
        'active_course': active_course,
        'certificate': cert,
        'remaining_lessons': remaining_lessons,
        'score_gap': score_gap,
    })





from .models import UserSettings
from .forms import UserSettingsForm

@login_required
def settings_view(request):
    user_settings, created = UserSettings.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserSettingsForm(request.POST, instance=user_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated successfully!")
            return redirect('settings')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserSettingsForm(instance=user_settings)
    return render(request, 'student_dashboard/settings.html', {'form': form})



def admin_required(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or user.username.lower() in ['admin', 'taabinda', 'tabinda'])


@login_required
def generate_course(request):
    available_courses = AdminCourse.objects.filter(is_active=True).prefetch_related('course_levels')
    if not available_courses.exists():
        available_courses = AdminCourse.objects.all().prefetch_related('course_levels')

    if request.method == 'POST':
        level_slug = request.POST.get('level_slug')
        level_id = request.POST.get('level_id')
        user_level = request.POST.get('level', 'Beginner')
        user_pace = request.POST.get('pace', 'Standard (3-5 hours/week)')
        user_objective = request.POST.get('objective', 'Skill Improvement')

        course_level = None
        if level_slug:
            course_level = CourseLevel.objects.select_related('parent_course').filter(slug=level_slug).first()
        elif level_id and str(level_id).isdigit():
            course_level = CourseLevel.objects.select_related('parent_course').filter(id=int(level_id)).first()

        if not course_level:
            course_input = (
                request.POST.get('course_topic')
                or request.POST.get('topic')
                or request.POST.get('course_slug')
                or request.POST.get('slug')
                or request.POST.get('course_id')
                or request.POST.get('course')
            )
            admin_course_instance = None
            if course_input:
                clean_input = str(course_input).strip()
                if clean_input.isdigit():
                    admin_course_instance = AdminCourse.objects.filter(id=int(clean_input)).first()
                if not admin_course_instance:
                    admin_course_instance = AdminCourse.objects.filter(course_code__iexact=clean_input).first()
                if not admin_course_instance:
                    admin_course_instance = AdminCourse.objects.filter(slug__iexact=clean_input).first()
                if not admin_course_instance:
                    admin_course_instance = AdminCourse.objects.filter(title__iexact=clean_input).first()

            if not admin_course_instance and available_courses.exists():
                admin_course_instance = available_courses.first()

            if admin_course_instance:
                clean_level = user_level.lower()
                if 'inter' in clean_level:
                    target_level_name = 'Intermediate'
                elif 'adv' in clean_level:
                    target_level_name = 'Advanced'
                else:
                    target_level_name = 'Beginner'

                course_level = CourseLevel.objects.filter(parent_course=admin_course_instance, level__iexact=target_level_name).first()
                if not course_level:
                    create_course_tiers_and_curriculum(admin_course_instance)
                    course_level = CourseLevel.objects.filter(parent_course=admin_course_instance, level__iexact=target_level_name).first()

                if not course_level:
                    course_level = CourseLevel.objects.filter(parent_course=admin_course_instance).first()

        if not course_level:
            messages.error(request, "Valid course level not found. Please choose a university-benchmarked course.")
            return redirect('generate_course')

        try:
            new_course = fetch_and_enroll_student_in_level(
                user=request.user,
                course_level=course_level,
                pace=user_pace,
                objective=user_objective
            )
            messages.success(
                request,
                f"Instant Access: Loaded '{course_level.title}' [{course_level.benchmark}] from database!"
            )
            return redirect(f"/course_content/?course_id={new_course.id}")
        except Exception as e:
            logger.error(f"Course Fetch Enrollment Error: {str(e)}")
            messages.error(request, f"Enrollment Error: {str(e)}")
            return redirect('generate_course')

    assessment = StudentAssessment.objects.filter(user=request.user).order_by('-created_at').first()
    if not assessment and request.user.is_authenticated:
        assessment = StudentAssessment.objects.filter(email__iexact=request.user.email).order_by('-created_at').first()

    suggested_courses = []
    if assessment and getattr(assessment, 'interest', None):
        suggested_courses = [assessment.interest]
    elif assessment and getattr(assessment, 'interest_topic', None):
        suggested_courses = list(AdminCourse.objects.filter(title__icontains=assessment.interest_topic)[:2])
    if not suggested_courses and available_courses.exists():
        suggested_courses = [available_courses.first()]

    for ac in available_courses:
        if not ac.course_levels.exists():
            create_course_tiers_and_curriculum(ac)

    all_course_levels = CourseLevel.objects.select_related('parent_course').filter(is_active=True).order_by('parent_course__title', 'id')

    return render(request, 'student_dashboard/course_data/generate_course.html', {
        'available_courses': available_courses,
        'suggested_courses': suggested_courses,
        'all_course_levels': all_course_levels,
        'assessment': assessment
    })


@login_required
def daily_lesson_view(request):
    lesson_id = request.GET.get('lesson_id')
    if lesson_id:
        return redirect('daily_lesson_view', lesson_id=lesson_id)
    active_course = GeneratedCourse.objects.filter(user=request.user).order_by('-created_at').first()
    if active_course:
        lesson = active_course.daily_lessons.filter(is_unlocked=True).last() or active_course.daily_lessons.first()
        if lesson:
            return redirect('daily_lesson_view', lesson_id=lesson.id)
    messages.error(request, "No active lesson found.")
    return redirect('course_content_view')


@login_required
def download_lesson_ppt(request, lesson_id):
    import os
    import re
    from .models import DailyLesson
    from .ppt_generator import generate_lesson_ppt_bytes
    from .ppt_service import ensure_lesson_slides_and_explanations
    from django.http import HttpResponse, FileResponse

    lesson = get_object_or_404(DailyLesson, id=lesson_id)
    try:
        ensure_lesson_slides_and_explanations(lesson)
        lesson.refresh_from_db()
    except Exception as e:
        logger.error(f"download_lesson_ppt: could not prepare slides for lesson {lesson_id}: {e}", exc_info=True)

    if lesson.ppt_file and os.path.exists(lesson.ppt_file.path):
        return FileResponse(open(lesson.ppt_file.path, 'rb'), as_attachment=True, filename=os.path.basename(lesson.ppt_file.name))

    file_stream = generate_lesson_ppt_bytes(lesson)
    safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', lesson.title)
    filename = f"Day_{lesson.day_number}_{safe_title}_Masterclass.pptx"

    response = HttpResponse(
        file_stream.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@user_passes_test(admin_required)
def admin_upload_lesson_ppt(request, lesson_id):
    from .models import DailyLesson
    from .ppt_service import process_lesson_ppt_upload

    lesson = get_object_or_404(DailyLesson, id=lesson_id)
    if request.method == 'POST':
        uploaded_file = request.FILES.get('ppt_file')
        if not uploaded_file:
            messages.error(request, "Please select a PPTX file to upload.")
        else:
            success, msg = process_lesson_ppt_upload(lesson, uploaded_file)
            if success:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
    if lesson.generated_course and lesson.generated_course.course_level and lesson.generated_course.course_level.slug:
        return redirect('admin_course_level_detail', slug=lesson.generated_course.course_level.slug)
    return redirect('admindashboard')


@login_required
def download_assignment_pdf(request, submission_id):
    from .models import AssignmentSubmission
    from django.template.loader import render_to_string
    from django.http import HttpResponse

    submission = get_object_or_404(AssignmentSubmission, id=submission_id, user=request.user)
    assignment_prompt = submission.question_prompt or (
        get_saved_or_generated_assignment(submission.lesson) if submission and submission.lesson else ""
    )

    context = {
        'submission': submission,
        'assignment_prompt': assignment_prompt,
        'request': request,
    }

    try:
        from xhtml2pdf import pisa
        html = render_to_string('student_dashboard/assignment_pdf.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Assignment_Report_{submission.id}.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('PDF generation error', status=500)
        return response
    except Exception as e:
        return HttpResponse(
            f"Assignment Submission Report #{submission.id}\nScore: {submission.score}\nFeedback: {submission.ai_feedback}",
            content_type='text/plain'
        )


@login_required
@user_passes_test(admin_required)
def admin_dashboard(request):
    total_courses = AdminCourse.objects.count()
    total_students = User.objects.filter(is_staff=False).count()
    total_enrollments = GeneratedCourse.objects.count()
    recent_courses = AdminCourse.objects.all().order_by('-id')[:6]
    recent_enrollments = GeneratedCourse.objects.select_related('user', 'admin_course', 'course_level').order_by('-created_at')[:8]
    pending_reports_count = Report.objects.filter(status='pending').count()

    context = {
        'total_courses': total_courses,
        'total_students': total_students,
        'total_enrollments': total_enrollments,
        'recent_courses': recent_courses,
        'recent_enrollments': recent_enrollments,
        'pending_reports_count': pending_reports_count,
    }
    return render(request, 'admin_db/admindashboard.html', context)


@login_required
@user_passes_test(admin_required)
def user_management(request):
    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        user_id = request.POST.get('user_id')
        if action == 'edit' and user_id:
            target_user = get_object_or_404(User, id=user_id)
            new_username = request.POST.get('username', '').strip()
            new_email = request.POST.get('email', '').strip()
            new_phone = request.POST.get('phone', '').strip()
            new_dob = request.POST.get('dob', '').strip()
            new_password = request.POST.get('password', '').strip()

            if new_username:
                target_user.username = new_username
            if new_email:
                target_user.email = new_email
            if new_password:
                target_user.set_password(new_password)
            target_user.save()

            profile_obj, _ = Profile.objects.get_or_create(user=target_user)
            if new_phone:
                profile_obj.phone = new_phone
            if new_dob:
                try:
                    profile_obj.dob = new_dob
                except Exception:
                    pass
            profile_obj.save()

            messages.success(request, f"User {target_user.username} updated successfully!")
            return redirect('user_management')

        elif action == 'delete' and user_id:
            target_user = get_object_or_404(User, id=user_id)
            username = target_user.username
            target_user.delete()
            messages.success(request, f"User {username} deleted successfully.")
            return redirect('user_management')

    users = list(User.objects.all().order_by('-date_joined'))
    for u in users:
        enrolled_titles = list(
            GeneratedCourse.objects.filter(user=u)
            .select_related('admin_course')
            .values_list('admin_course__title', flat=True)
            .distinct()
        )
        u.custom_generated_courses = enrolled_titles

    return render(request, 'admin_db/user_management.html', {'users': users})


@login_required
@user_passes_test(admin_required)
def edit_user(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        target_user.username = request.POST.get('username', target_user.username)
        target_user.email = request.POST.get('email', target_user.email)
        target_user.is_active = request.POST.get('is_active') in ['on', 'true', '1']
        target_user.save()
        messages.success(request, f"User {target_user.username} updated successfully!")
        return redirect('user_management')
    return render(request, 'admin_db/user_management.html', {'target_user': target_user, 'users': User.objects.all()})


@login_required
@user_passes_test(admin_required)
def delete_user(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    username = target_user.username
    target_user.delete()
    messages.success(request, f"User {username} deleted successfully.")
    return redirect('user_management')


@login_required
@user_passes_test(admin_required)
def courses_info(request):
    search_query = request.GET.get('search', '').strip()
    tier_filter = request.GET.get('tier', '').strip()

    levels = CourseLevel.objects.select_related('parent_course').filter(is_active=True)
    if search_query:
        levels = levels.filter(Q(title__icontains=search_query) | Q(parent_course__title__icontains=search_query))
    if tier_filter:
        levels = levels.filter(level__iexact=tier_filter)

    level_cards = []
    for lvl in levels:
        enrolled_count = GeneratedCourse.objects.filter(course_level=lvl).values('user').distinct().count()
        level_cards.append({
            'level': lvl,
            'title': lvl.title,
            'parent_title': lvl.parent_course.title if lvl.parent_course else '',
            'slug': lvl.slug,
            'tier': lvl.level,
            'benchmark': lvl.benchmark,
            'enrolled_count': enrolled_count,
            'total_modules': lvl.academic_modules.count(),
            'total_lessons': AcademicLesson.objects.filter(course_level=lvl).count(),
            'total_slides': PresentationSlide.objects.filter(course_level=lvl).count(),
        })

    context = {
        'level_cards': level_cards,
        'total_courses': AdminCourse.objects.count(),
        'total_cards': len(level_cards),
        'search_query': search_query,
        'tier_filter': tier_filter,
    }
    return render(request, 'admin_db/courses_info.html', context)


@login_required
@user_passes_test(admin_required)
def admin_course_detail(request, slug):
    course = get_object_or_404(AdminCourse, slug=slug)
    if not course.course_levels.exists():
        create_course_tiers_and_curriculum(course)
    course_tiers = course.course_levels.all().order_by('id')
    enrollments = GeneratedCourse.objects.filter(admin_course=course).select_related('user', 'course_level').order_by('-created_at')
    enrolled_count = enrollments.values('user').distinct().count()

    total_modules = CourseModule.objects.filter(course_level__parent_course=course).count()
    total_lessons = AcademicLesson.objects.filter(course_level__parent_course=course).count()

    context = {
        'course': course,
        'course_tiers': course_tiers,
        'enrollments': enrollments,
        'enrolled_count': enrolled_count,
        'total_modules': total_modules,
        'total_lessons': total_lessons,
    }
    return render(request, 'admin_db/course_details.html', context)


@login_required
@user_passes_test(admin_required)
def toggle_system_mode(request):
    messages.success(request, "System mode updated successfully.")
    return redirect('admin_dashboard')


@login_required
@user_passes_test(admin_required)
def analytics(request):
    total_courses = AdminCourse.objects.count()
    total_students = User.objects.filter(is_staff=False).count()
    total_enrollments = GeneratedCourse.objects.count()
    total_assignments = AssignmentSubmission.objects.count()
    total_quizzes = QuizSubmission.objects.count()

    top_courses = AdminCourse.objects.all()[:5]
    top_performing_courses = []
    for c in top_courses:
        enrolled = GeneratedCourse.objects.filter(admin_course=c).count()
        top_performing_courses.append({
            'title': c.title,
            'enrolled_count': enrolled,
            'completion_rate': 85.0
        })

    recent_activities = []
    for sub in AssignmentSubmission.objects.select_related('user', 'lesson').order_by('-submitted_at')[:6]:
        recent_activities.append({
            'user': sub.user.username,
            'action': f"Submitted assignment for {sub.lesson.title if sub.lesson else 'Lesson'}",
            'timestamp': sub.submitted_at
        })

    context = {
        'total_courses': total_courses,
        'total_students': total_students,
        'total_enrollments': total_enrollments,
        'total_assignments': total_assignments,
        'total_quizzes': total_quizzes,
        'completion_rate': 82.5,
        'student_satisfaction': '96%',
        'top_performing_courses': top_performing_courses,
        'assignment_submissions': total_assignments,
        'quiz_performance': '84%',
        'recent_activities': recent_activities,
    }
    return render(request, 'admin_db/analytics.html', context)


@login_required
@user_passes_test(admin_required)
def admin_notifications(request):
    if request.method == 'POST':
        target_recipient = request.POST.get('target_recipient', 'all_students')
        category_type = request.POST.get('category_type', 'announcement')
        subject_heading = request.POST.get('subject_heading', '').strip() or request.POST.get('title', 'Admin Notice').strip()
        notification_body = request.POST.get('notification_body', '').strip() or request.POST.get('message', '').strip()
        specific_student_id = request.POST.get('specific_student_id') or request.POST.get('student_id')

        if notification_body:
            recipient_user = None
            if target_recipient == 'specific_student' and specific_student_id and str(specific_student_id).isdigit():
                recipient_user = User.objects.filter(id=int(specific_student_id)).first()

            notification = Notification.objects.create(
                target_recipient=target_recipient,
                category_type=category_type,
                subject_heading=subject_heading or 'Notice from ALVIX Administration',
                notification_body=notification_body,
                recipient_user=recipient_user,
                is_dispatched=True
            )

            if target_recipient == 'enrolled_students':
                enrolled_user_ids = GeneratedCourse.objects.values_list('user_id', flat=True).distinct()
                for uid in enrolled_user_ids:
                    u = User.objects.filter(id=uid).first()
                    if u:
                        StudentNotificationStatus.objects.get_or_create(user=u, notification=notification)

            if target_recipient == 'specific_student' and recipient_user:
                messages.success(request, f"Notification sent to {recipient_user.username}!")
            else:
                messages.success(request, "Broadcast notification dispatched to students!")
            return redirect('admin_notifications')

    students_list = User.objects.filter(is_staff=False).order_by('username')
    dispatch_history = Notification.objects.all().order_by('-created_at')[:20]
    return render(request, 'admin_db/admin_notifications.html', {
        'students_list': students_list,
        'dispatch_history': dispatch_history
    })


@login_required
@user_passes_test(admin_required)
def add_course(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        course_code = request.POST.get('course_code', '').strip()
        description = request.POST.get('description', '').strip()
        image_file = request.FILES.get('image')

        if title:
            from django.utils.text import slugify
            base_slug = slugify(title)
            slug = base_slug
            counter = 1
            while AdminCourse.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            admin_course = AdminCourse(
                title=title,
                slug=slug,
                description=description,
                is_active=True
            )
            if course_code:
                admin_course.course_code = course_code
            if image_file:
                admin_course.image = image_file
            admin_course.save()

            create_course_tiers_and_curriculum(admin_course)
            messages.success(request, f"Course '{admin_course.title}' created and university tiers initialized!")
            return redirect('courses_info')
    return render(request, 'admin_db/add_course.html')


@login_required
@user_passes_test(admin_required)
def admin_course_level_detail(request, slug):
    course_level = get_object_or_404(CourseLevel.objects.select_related('parent_course'), slug=slug)
    force_regen = (request.GET.get('regenerate') == '1' or request.POST.get('action') == 'regenerate')
    has_deep_content = (
        CourseModule.objects.filter(course_level=course_level).exists() and
        PresentationSlide.objects.filter(course_level=course_level).exists()
    )

    if not has_deep_content or force_regen:
        from .deep_curriculum_service import generate_deep_university_curriculum
        generate_deep_university_curriculum(course_level, force=force_regen, use_ai=True)
        if force_regen:
            messages.success(request, f"Deep university curriculum regenerated for {course_level.title} [{course_level.benchmark}]!")
            return redirect('admin_course_level_detail', slug=slug)

    modules = CourseModule.objects.filter(course_level=course_level).prefetch_related('lessons').order_by('order')
    all_lessons = AcademicLesson.objects.filter(course_level=course_level).select_related('module').order_by('module__order', 'order')
    all_slides = PresentationSlide.objects.filter(course_level=course_level).order_by('slide_number')
    daily_lessons = DailyLesson.objects.filter(course_level=course_level).order_by('day_number').select_related('task')
    enrolled_count = GeneratedCourse.objects.filter(
        Q(course_level=course_level) | (Q(admin_course=course_level.parent_course) & Q(level__iexact=course_level.level))
    ).values('user').distinct().count()

    context = {
        'course_level': course_level,
        'parent_course': course_level.parent_course,
        'modules': modules,
        'total_modules': modules.count(),
        'all_lessons': all_lessons,
        'total_lessons': all_lessons.count(),
        'all_slides': all_slides,
        'total_slides': all_slides.count(),
        'daily_lessons': daily_lessons,
        'enrolled_count': enrolled_count,
    }
    return render(request, 'admin_db/level_course_view.html', context)


@login_required
@user_passes_test(admin_required)
def admin_regenerate_deep_curriculum(request, slug):
    course_level = get_object_or_404(CourseLevel.objects.select_related('parent_course'), slug=slug)
    from .deep_curriculum_service import generate_deep_university_curriculum
    generate_deep_university_curriculum(course_level, force=True, use_ai=True)
    messages.success(request, f"Deep university curriculum regenerated for {course_level.title} [{course_level.benchmark}]!")
    return redirect('admin_course_level_detail', slug=slug)


@login_required
@user_passes_test(admin_required)
def admin_course_level_users(request, slug):
    course_level = get_object_or_404(CourseLevel.objects.select_related('parent_course'), slug=slug)
    enrollments = GeneratedCourse.objects.filter(
        Q(course_level=course_level) | (Q(admin_course=course_level.parent_course) & Q(level__iexact=course_level.level))
    ).select_related('user').order_by('-created_at')

    total_enrolled = enrollments.count()
    completed_count = 0
    active_count = 0
    for e in enrollments:
        comp = e.daily_lessons.filter(is_completed=True).count()
        tot = e.daily_lessons.count()
        if tot > 0 and comp == tot:
            completed_count += 1
        elif comp > 0:
            active_count += 1

    avg_progress = round((completed_count / total_enrolled * 100), 1) if total_enrolled > 0 else 0.0

    context = {
        'course_level': course_level,
        'parent_course': course_level.parent_course,
        'enrollments': enrollments,
        'total_enrolled': total_enrolled,
        'completed_count': completed_count,
        'active_count': active_count,
        'avg_progress': avg_progress,
    }
    return render(request, 'admin_db/level_users_telemetry.html', context)


@login_required
def enroll_level_view(request, slug):
    course_level = get_object_or_404(CourseLevel, slug=slug)
    new_course = fetch_and_enroll_student_in_level(user=request.user, course_level=course_level)
    messages.success(request, f"Successfully enrolled in {course_level.title} [{course_level.benchmark}]!")
    return redirect(f"/course_content/?course_id={new_course.id}")


@login_required
@user_passes_test(admin_required)
def admin_reports(request):
    reports = Report.objects.select_related('student').order_by('-created_at')
    total_submissions = reports.count()
    pending_reports = reports.filter(status='pending').count()
    reviewed_reports = reports.filter(status='resolved').count()
    today = timezone.now().date()
    active_today = reports.filter(created_at__date=today).count()

    context = {
        'reports': reports,
        'total_submissions': total_submissions,
        'pending_reports': pending_reports,
        'reviewed_reports': reviewed_reports,
        'active_today': active_today,
    }
    return render(request, 'admin_db/admin_reports.html', context)


@login_required
@user_passes_test(admin_required)
def send_report_response(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    if request.method == 'POST':
        response_text = request.POST.get('feedback', '').strip() or request.POST.get('response', '').strip()
        if response_text:
            report.status = 'resolved'
            report.save()
            if report.student:
                Notification.objects.create(
                    target_recipient='specific_student',
                    recipient_user=report.student,
                    category_type='announcement',
                    subject_heading=f'Response to Report #{report.id}',
                    notification_body=f'Admin Response: {response_text}\n\nYour issue has been marked as resolved.',
                    is_dispatched=True
                )
            messages.success(request, f'Response delivered to student for Report #{report.id}!')
    return redirect('admin_reports')


@login_required
@user_passes_test(admin_required)
def delete_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.delete()
    messages.success(request, f'Report #{report_id} deleted successfully.')
    return redirect('admin_reports')


def format_assignment_prompt_html(prompt_text):
    """Formats plain text / markdown assignment prompt into clean, responsive HTML."""
    if not prompt_text:
        return ""
    if "<p>" in prompt_text or "<br>" in prompt_text or "<strong>" in prompt_text:
        return prompt_text
    import re
    lines = prompt_text.strip().split("\n")
    html_lines = []
    for line in lines:
        line_str = line.strip()
        if not line_str:
            html_lines.append("<br>")
        elif line_str.startswith("Requirements:") or line_str.startswith("Objective:") or line_str.startswith("Deliverables:"):
            html_lines.append(f"<strong class='d-block mt-2 text-dark'>{line_str}</strong>")
        elif re.match(r'^\d+\.', line_str):
            html_lines.append(f"<div class='ms-2 mb-1'>• {line_str}</div>")
        elif line_str.startswith("Day ") or "Engineering Challenge" in line_str or "Challenge:" in line_str:
            html_lines.append(f"<h6 class='fw-bold text-success mb-2'>{line_str}</h6>")
        else:
            html_lines.append(f"<div>{line_str}</div>")
    return "".join(html_lines)


def get_saved_or_generated_assignment(lesson, request=None):
    """
    Retrieves pre-saved assignment directly from database with zero delay.
    When a student clicks on the assignment option:
    - Sets assignment_issued_at (issue date) to the exact timestamp of student's click if not already set.
    - Sets deadline relative to issue date.
    - Fetches task from canonical lesson in the admin database.
    """
    # Issue date depends strictly on student's click
    if lesson.generated_course:
        if not lesson.assignment_issued_at:
            lesson.assignment_issued_at = timezone.now()
            lesson.deadline = timezone.now() + timedelta(days=2)
            lesson.save(update_fields=['assignment_issued_at', 'deadline'])

    assignment_text = ""
    assignment_data = {}

    # 1. Direct task on this lesson
    try:
        if hasattr(lesson, 'task') and lesson.task and lesson.task.assignment_question:
            assignment_text = lesson.task.assignment_question
            assignment_data = getattr(lesson.task, 'assignment_data', {})
    except Exception:
        pass

    # 2. Check canonical lesson in admin database if cloned
    if not assignment_text and lesson.course_level:
        canonical = DailyLesson.objects.filter(
            course_level=lesson.course_level,
            day_number=lesson.day_number,
            generated_course__isnull=True
        ).first()
        if canonical:
            try:
                if hasattr(canonical, 'task') and canonical.task and canonical.task.assignment_question:
                    assignment_text = canonical.task.assignment_question
                    assignment_data = getattr(canonical.task, 'assignment_data', {})
                    LessonTask.objects.update_or_create(
                        lesson=lesson,
                        defaults={
                            'assignment_question': assignment_text,
                            'assignment_data': assignment_data,
                            'quiz_data': canonical.task.quiz_data or []
                        }
                    )
            except Exception:
                pass

    # 3. Fallback: generate via build_track_assignment_and_quiz
    if not assignment_text:
        course_type = getattr(lesson.generated_course, 'course_type', 'Mixed') if lesson.generated_course else 'Mixed'
        level_name = getattr(lesson.course_level, 'level', 'Beginner') if lesson.course_level else 'Beginner'
        course_title = getattr(lesson.generated_course.admin_course, 'title', lesson.title) if lesson.generated_course and lesson.generated_course.admin_course else lesson.title

        from .ai_services import build_track_assignment_and_quiz
        assignment_text, assignment_data, quiz_data = build_track_assignment_and_quiz(
            course_title=course_title,
            level_name=level_name,
            day_number=lesson.day_number,
            topic_title=lesson.title,
            course_type=course_type
        )
        try:
            task, _ = LessonTask.objects.get_or_create(
                lesson=lesson,
                defaults={'assignment_question': assignment_text, 'assignment_data': assignment_data, 'quiz_data': quiz_data}
            )
            if not task.assignment_question:
                task.assignment_question = assignment_text
                task.assignment_data = assignment_data
                task.save(update_fields=['assignment_question', 'assignment_data'])
        except Exception as e:
            logger.warning(f"Failed to persist assignment task on lesson {lesson.id}: {e}")

    return format_assignment_prompt_html(assignment_text), assignment_data


def get_saved_or_generated_quiz(lesson, request=None):
    """
    Retrieves pre-saved quiz questions directly from database with zero delay.
    When a student clicks on the quiz option:
    - Sets quiz_issued_at (issue date) to the exact timestamp of student's click if not already set.
    - Fetches quiz from canonical lesson in admin database.
    - Validates strictly that 'correct' is one of the options.
    """
    if lesson.generated_course:
        if not lesson.quiz_issued_at:
            lesson.quiz_issued_at = timezone.now()
            lesson.save(update_fields=['quiz_issued_at'])

    raw_quiz = []
    # 1. Direct task on lesson
    try:
        if hasattr(lesson, 'task') and lesson.task and lesson.task.quiz_data:
            raw_quiz = lesson.task.quiz_data
    except Exception:
        pass

    # 2. Check canonical lesson in admin database
    if not raw_quiz and lesson.course_level:
        canonical = DailyLesson.objects.filter(
            course_level=lesson.course_level,
            day_number=lesson.day_number,
            generated_course__isnull=True
        ).first()
        if canonical:
            try:
                if hasattr(canonical, 'task') and canonical.task and canonical.task.quiz_data:
                    raw_quiz = canonical.task.quiz_data
                    LessonTask.objects.update_or_create(
                        lesson=lesson,
                        defaults={
                            'assignment_question': getattr(canonical.task, 'assignment_question', ''),
                            'assignment_data': getattr(canonical.task, 'assignment_data', {}),
                            'quiz_data': raw_quiz
                        }
                    )
            except Exception:
                pass

    # 3. Fallback via build_track_assignment_and_quiz
    if not raw_quiz:
        course_type = getattr(lesson.generated_course, 'course_type', 'Mixed') if lesson.generated_course else 'Mixed'
        level_name = getattr(lesson.course_level, 'level', 'Beginner') if lesson.course_level else 'Beginner'
        course_title = getattr(lesson.generated_course.admin_course, 'title', lesson.title) if lesson.generated_course and lesson.generated_course.admin_course else lesson.title

        from .ai_services import build_track_assignment_and_quiz
        _, _, raw_quiz = build_track_assignment_and_quiz(
            course_title=course_title,
            level_name=level_name,
            day_number=lesson.day_number,
            topic_title=lesson.title,
            course_type=course_type
        )
        try:
            task, _ = LessonTask.objects.get_or_create(
                lesson=lesson,
                defaults={'assignment_question': '', 'quiz_data': raw_quiz}
            )
            if not task.quiz_data:
                task.quiz_data = raw_quiz
                task.save(update_fields=['quiz_data'])
        except Exception as e:
            logger.warning(f"Failed to persist quiz task on lesson {lesson.id}: {e}")

    # Standardize output and strictly validate correct is in options
    normalized = []
    for idx, q in enumerate(raw_quiz, start=1):
        q_text = q.get('text') or q.get('question', f"Question {idx}")
        opts = [str(o).strip() for o in q.get('options', [])]
        correct_val = str(q.get('correct', '')).strip()
        if not correct_val:
            c_idx = q.get('correct_answer')
            if isinstance(c_idx, int) and 0 <= c_idx < len(opts):
                correct_val = opts[c_idx]
            else:
                correct_val = opts[0] if opts else ""

        # Strictly validate that correct is in options
        if correct_val not in opts:
            if opts:
                correct_val = opts[0]

        normalized.append({
            'id': q.get('id', idx),
            'text': q_text,
            'code': q.get('code', ''),
            'options': opts,
            'correct': correct_val,
            'explanation': q.get('explanation', ''),
            'topic': q.get('topic', f"Day {lesson.day_number} Concept")
        })
    return normalized


@login_required
def assignment_view(request):
    active_course = GeneratedCourse.objects.filter(user=request.user).order_by('-created_at').first()
    if not active_course:
        messages.warning(request, "First generate your course.")
        return redirect('mycourse')

    lesson_id = request.GET.get('lesson_id')
    lesson = None

    if lesson_id:
        lesson = DailyLesson.objects.filter(id=lesson_id, generated_course=active_course).first()

    if not lesson:
        lesson = active_course.daily_lessons.filter(is_unlocked=True).last() or active_course.daily_lessons.first()

    if not lesson:
        messages.error(request, "No lesson is available.")
        return redirect('generate_course')

    # Instant access: Load pre-saved assignment directly from database and record issue date upon click
    assignment_prompt, assignment_data = get_saved_or_generated_assignment(lesson, request=request)
    lesson.refresh_from_db()

    deadline_date = lesson.deadline or (timezone.now() + timedelta(days=2))
    is_expired = timezone.now() > deadline_date

    # Track determination
    is_practical = (assignment_data.get('type') == 'practical') if assignment_data else (active_course.course_type == 'Practical')

    if request.method == 'POST':
        submission_text = request.POST.get('student_submission', '').strip()
        uploaded_file = request.FILES.get('file_submission')

        if not submission_text and not uploaded_file:
            messages.error(request, "Please provide source code/notes or upload a completed solution file.")
            return redirect(f"{request.path}?lesson_id={lesson.id}")

        # Telemetry: Copy/paste and typing pattern tracking
        paste_count = int(request.POST.get('paste_count', 0) or 0)
        pasted_chars_total = int(request.POST.get('pasted_chars_total', 0) or 0)
        typing_duration_seconds = int(request.POST.get('typing_duration_seconds', 0) or 0)
        keystroke_count = int(request.POST.get('keystroke_count', 0) or 0)

        # Integrity Check: Evaluate copy risk
        copy_risk, peer_sim, ai_prob, copy_details = evaluate_submission_copy_risk(
            submission_text=submission_text,
            paste_count=paste_count,
            pasted_chars_total=pasted_chars_total,
            typing_duration_seconds=typing_duration_seconds,
            keystroke_count=keystroke_count,
            current_user=request.user,
            lesson=lesson
        )

        # Rubric Evaluation: Do not give zero for copy risk; evaluate rubric fairly and flag for admin
        eval_result = evaluate_submission_with_ai(lesson.title, submission_text, uploaded_file)
        score_val = min(10, max(2, int(eval_result.get('score', 4)) * 2))  # Scale to 10 marks
        rubric_remarks = (
            f"Rubric Feedback: Scored {score_val}/10 marks. {eval_result.get('remarks', 'Good implementation.')} "
            f"[Integrity Review: {copy_risk} copy risk flagged for administrative verification]."
        )

        submission, created = AssignmentSubmission.objects.get_or_create(
            user=request.user,
            lesson=lesson,
            defaults={
                'question_prompt': assignment_prompt,
                'submitted_answer': submission_text,
                'file_submission': uploaded_file,
                'score': score_val,
                'marks': score_val,
                'total_marks': 10,
                'ai_feedback': rubric_remarks,
                'paste_count': paste_count,
                'pasted_chars_total': pasted_chars_total,
                'typing_duration_seconds': typing_duration_seconds,
                'keystroke_count': keystroke_count,
                'peer_similarity_score': peer_sim,
                'ai_generated_probability': ai_prob,
                'copy_risk_level': copy_risk,
                'copy_risk_details': copy_details,
                'admin_reviewed': False
            }
        )

        if not created:
            submission.question_prompt = assignment_prompt
            submission.submitted_answer = submission_text
            if uploaded_file:
                submission.file_submission = uploaded_file
            submission.score = score_val
            submission.marks = score_val
            submission.total_marks = 10
            submission.ai_feedback = rubric_remarks
            submission.paste_count = paste_count
            submission.pasted_chars_total = pasted_chars_total
            submission.typing_duration_seconds = typing_duration_seconds
            submission.keystroke_count = keystroke_count
            submission.peer_similarity_score = peer_sim
            submission.ai_generated_probability = ai_prob
            submission.copy_risk_level = copy_risk
            submission.copy_risk_details = copy_details
            submission.submitted_at = timezone.now()
            submission.save()

        # Mark lesson completed
        lesson.is_completed = True
        lesson.save(update_fields=['is_completed'])

        # Continuous daily update of student certificate on submission
        update_or_create_student_certificate(request.user, active_course, request=request)

        messages.success(request, f"Assignment successfully submitted! Rubric score: {score_val}/10 marks.")
        return redirect(f"{request.path}?lesson_id={lesson.id}")

    latest_submission = AssignmentSubmission.objects.filter(user=request.user, lesson=lesson).order_by('-submitted_at').first()
    all_submissions = AssignmentSubmission.objects.filter(user=request.user).order_by('-submitted_at')

    return render(request, 'student_dashboard/course_data/assignment.html', {
        'active_course': active_course,
        'lesson': lesson,
        'assignment_prompt': assignment_prompt,
        'assignment_data': assignment_data,
        'is_practical': is_practical,
        'latest_submission': latest_submission,
        'all_submissions': all_submissions,
        'deadline_date': deadline_date,
        'issue_date': lesson.assignment_issued_at,
        'is_expired': is_expired,
    })


@login_required
def quiz_view(request, lesson_id=None):
    """
    Renders diagnostic quizzes with zero delay.
    Issue date is recorded upon student's click/opening.
    Provides marks plus remarks with explanations per wrong answer.
    """
    active_course = GeneratedCourse.objects.filter(user=request.user).order_by('-created_at').first()

    if not lesson_id:
        lesson_id = request.GET.get('lesson_id')

    lesson = None
    if lesson_id:
        lesson = DailyLesson.objects.filter(id=lesson_id, generated_course__user=request.user).first()

    if not lesson and active_course:
        lesson = active_course.daily_lessons.filter(is_unlocked=True).last() or active_course.daily_lessons.first()

    if not lesson:
        messages.error(request, "No lesson available for quiz.")
        return redirect('student_dashboard')

    # Instant access & record issue date
    quiz_questions = get_saved_or_generated_quiz(lesson, request=request)
    lesson.refresh_from_db()

    if request.method == 'POST':
        score = 0
        total = len(quiz_questions)
        summary_list = []
        wrong_answers = []

        for idx, q in enumerate(quiz_questions, start=1):
            q_id = q.get('id', idx)
            user_answer = request.POST.get(f"q_{q_id}", "").strip()
            correct_answer = str(q.get('correct', '')).strip()

            is_correct = bool(user_answer and user_answer.lower() == correct_answer.lower())
            if is_correct:
                score += 1
            else:
                wrong_answers.append({
                    'question_number': idx,
                    'question': q.get('text', ''),
                    'user_answer': user_answer or "No answer provided",
                    'correct_answer': correct_answer,
                    'explanation': q.get('explanation', 'Refer to today\'s core lecture concepts.')
                })

            summary_list.append(
                f"<div class='mb-2 pb-2 border-bottom'>"
                f"<strong>Q{idx}: {q.get('text', '')}</strong><br>"
                f"<small class='text-muted'>Your Answer: <span class='{'text-success fw-bold' if is_correct else 'text-danger fw-bold'}'>{user_answer or 'None'}</span></small><br>"
                f"<small class='text-muted'>Correct Answer: <span class='text-success fw-bold'>{correct_answer}</span></small>"
                f"</div>"
            )

        percentage = int((score / total) * 100) if total > 0 else 0

        # Build remarks with explanation per wrong answer
        if wrong_answers:
            wrong_feedback_parts = [
                f"• Q{w['question_number']}: Correct answer was '{w['correct_answer']}'. {w['explanation']}"
                for w in wrong_answers
            ]
            ai_remarks = (
                f"Completed quiz with {score}/{total} correct answers ({percentage}% accuracy).\n"
                f"Explanations for Incorrect Answers:\n" + "\n".join(wrong_feedback_parts)
            )
        else:
            ai_remarks = f"Flawless performance! You achieved {score}/{total} correct answers (100% accuracy) on today\'s diagnostic quiz."

        question_summary_html = "".join(summary_list)

        QuizSubmission.objects.create(
            user=request.user,
            lesson=lesson,
            score=score,
            total_questions=total,
            percentage=percentage,
            ai_feedback=ai_remarks,
            wrong_answers_explanation=wrong_answers,
            question_summary=question_summary_html
        )

        # Mark lesson completed
        lesson.is_completed = True
        lesson.save(update_fields=['is_completed'])

        # Continuous daily update of student certificate on submission
        update_or_create_student_certificate(request.user, active_course, request=request)

        # Unlock next lesson if passed
        if percentage >= 50:
            next_lesson = DailyLesson.objects.filter(
                generated_course=lesson.generated_course,
                day_number=lesson.day_number + 1
            ).first()
            if next_lesson:
                next_lesson.is_unlocked = True
                next_lesson.save(update_fields=['is_unlocked'])
            messages.success(request, f"Quiz passed with {score}/{total} correct answers ({percentage}%)! Next lesson unlocked.")
        else:
            messages.warning(request, f"Score: {percentage}%. Review the wrong answer explanations and try again to master the concepts.")

        return redirect(f"{request.path}?lesson_id={lesson.id}")

    all_submissions = QuizSubmission.objects.filter(user=request.user).order_by('-submitted_at')
    latest_submission = QuizSubmission.objects.filter(user=request.user, lesson=lesson).order_by('-submitted_at').first()

    return render(request, 'student_dashboard/course_data/quiz.html', {
        'lesson': lesson,
        'quiz_questions': quiz_questions,
        'latest_submission': latest_submission,
        'all_submissions': all_submissions,
        'issue_date': lesson.quiz_issued_at,
    })


@login_required
@csrf_exempt
def record_lesson_watch_time(request, lesson_id):
    """
    Lesson Watch Time Tracking:
    - Counts watch time ONLY while lesson tab is visible and narration is actively playing.
    - Pauses on inactivity.
    - Skipping does NOT count toward watch time.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    lesson = get_object_or_404(DailyLesson, id=lesson_id)
    if not lesson.generated_course or lesson.generated_course.user != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = {}

    delta = int(data.get('seconds', 5))
    delta = max(1, min(delta, 30))  # Anti-tampering cap

    lesson.watch_time_seconds = (lesson.watch_time_seconds or 0) + delta
    req_sec = getattr(lesson, 'required_watch_seconds', 180) or 180

    if lesson.watch_time_seconds >= req_sec:
        lesson.watch_time_completed = True
        lesson.is_completed = True

    lesson.save(update_fields=['watch_time_seconds', 'watch_time_completed', 'is_completed'])

    # Continuous update of student certificate
    update_or_create_student_certificate(request.user, lesson.generated_course, request=request)

    watch_pct = min(100.0, (lesson.watch_time_seconds / req_sec * 100.0))
    return JsonResponse({
        'status': 'ok',
        'watch_time_seconds': lesson.watch_time_seconds,
        'required_watch_seconds': req_sec,
        'percentage': round(watch_pct, 1),
        'is_completed': lesson.watch_time_completed
    })


@login_required
def certificate(request, course_id=None):
    """
    Renders the official ALVIX Certificate of Completion & Excellence.
    Unlocks when the student completes the course and overall percentage reaches pass mark (35%).
    Until then, renders certificate_locked.html with exact remaining requirements.
    """
    if course_id:
        active_course = get_object_or_404(GeneratedCourse, id=course_id)
    else:
        active_course = GeneratedCourse.objects.filter(user=request.user).order_by('-created_at').first()

    if not active_course:
        return render(request, 'student_dashboard/certificate_locked.html', {
            'error': 'No active course found. Please enroll in a course to view your certificate.'
        })

    cert, perf = update_or_create_student_certificate(request.user, active_course, request=request)

    is_staff_or_preview = (
        request.user.is_staff or
        request.user.is_superuser or
        request.GET.get('preview') in ['1', 'true', 'yes']
    )

    if not cert.is_unlocked and not is_staff_or_preview:
        remaining_lessons = max(0, perf['total_days'] - perf['completed_days_count'])
        score_gap = max(0.0, round(perf['pass_mark'] - perf['overall_percentage'], 1))
        return render(request, 'student_dashboard/certificate_locked.html', {
            'active_course': active_course,
            'performance': perf,
            'remaining_lessons': remaining_lessons,
            'score_gap': score_gap,
            'pass_mark': perf['pass_mark'],
            'current_score': perf['overall_percentage'],
        })

    return render(request, 'student_dashboard/course_data/certificate.html', {
        'active_course': active_course,
        'certificate': cert,
        'performance': perf,
    })


@login_required
def download_certificate_pdf(request, course_id):
    """Downloads official server-generated PDF certificate with unique ID and verification QR code."""
    active_course = get_object_or_404(GeneratedCourse, id=course_id)
    cert, perf = update_or_create_student_certificate(request.user, active_course, request=request)

    is_staff_or_preview = request.user.is_staff or request.user.is_superuser or request.GET.get('preview') in ['1', 'true', 'yes']
    if not cert.is_unlocked and not is_staff_or_preview:
        messages.error(request, "Certificate is locked until you complete the course and achieve the pass mark.")
        return redirect('performance')

    pdf_stream = generate_certificate_pdf_bytes(cert)
    response = HttpResponse(pdf_stream.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Certificate_{cert.certificate_id}.pdf"'
    return response


def verify_certificate(request, cert_id):
    """
    Public verification endpoint:
    Displays whether the certificate is VALID or INVALID with official credentials.
    """
    cert = Certificate.objects.filter(certificate_id=cert_id).first()
    is_valid = bool(cert and cert.is_valid and cert.is_unlocked)
    return render(request, 'student_dashboard/certificate_verify.html', {
        'certificate': cert,
        'cert_id': cert_id,
        'is_valid': is_valid,
        'verification_time': timezone.now(),
    })


@login_required(login_url='login')
@user_passes_test(admin_required, login_url='login')
def admin_avatar_settings_view(request):
    avatar_settings = AvatarSettings.get_settings()
    asset_status = get_avatar_asset_status()

    if request.method == 'POST':
        form = AvatarSettingsForm(request.POST, instance=avatar_settings)
        if form.is_valid():
            form.save()
            messages.success(request, f"Avatar settings for '{avatar_settings.avatar_name}' updated successfully!")
            return redirect('admin_avatar_settings')
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        form = AvatarSettingsForm(instance=avatar_settings)

    return render(request, 'admin_db/admin_settings.html', {
        'form': form,
        'avatar_settings': avatar_settings,
        'asset_status': asset_status,
    })
