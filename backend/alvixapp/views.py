
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
from django.http import Http404, JsonResponse
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
from django.contrib.auth.hashers import make_password
from .permissions import is_alvix_admin, can_access_lesson
from .assignment_grading import evaluate_submission_with_ai
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
        email_input = (request.POST.get("email") or "").strip()
        password = request.POST.get("password")

        user_obj = User.objects.filter(email__iexact=email_input).first() if email_input else None
        username = user_obj.username if user_obj else email_input

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if is_alvix_admin(user):
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
    (Logic lives in page_context/public.py, shared with /api/v1/public/.)
    """
    from .page_context.public import finalize_student_registration as _finalize
    return _finalize(request, pending_data)


@csrf_protect
def signup_view(request):
    from .page_context import public as public_ctx

    admin_courses = AdminCourse.objects.filter(is_active=True)
    context = {
        'admin_courses': admin_courses,
    }

    if request.method == 'POST':
        # Step A: Verification Code submission
        if 'verify_code_submit' in request.POST or 'otp_code' in request.POST:
            entered_code = request.POST.get('verification_code') or request.POST.get('otp_code', '')
            result = public_ctx.signup_verify(request, entered_code)
            if result['ok']:
                # Redirect to 1 recommended course page
                return redirect('student_assessment')
            context['error'] = result['error']
            if result['step']:
                context['step'] = result['step']
                context['email'] = result['email']
            return render(request, 'main_front/signup.html', context)

        # Step B: Combined Assessment + Registration Form Submission
        result = public_ctx.signup_start(request, request.POST)
        if not result['ok']:
            context['error'] = result['error']
            context['saved_data'] = result['saved_data']
            return render(request, 'main_front/signup.html', context)

        context['step'] = result['step']
        context['email'] = result['email']
        context['verification_code_debug'] = result['verification_code_debug']
        return render(request, 'main_front/signup.html', context)

    return render(request, 'main_front/signup.html', context)


def verify_otp_view(request):
    from .page_context import public as public_ctx

    pending_data = public_ctx.pending_signup(request)
    if not pending_data:
        return redirect('signup')

    context = {'email': pending_data.get('email')}
    if request.method == 'POST':
        entered_otp = request.POST.get('otp_code') or request.POST.get('verification_code', '')
        result = public_ctx.verify_otp(request, entered_otp)
        if result['ok']:
            return redirect('student_assessment')
        context['error'] = result['error']

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
    (Logic lives in page_context/public.py, shared with /api/v1/public/suggested-courses/.)
    """
    from .page_context import public as public_ctx

    ctx = public_ctx.resolve_course_suggestion(request)

    # Handle POST Actions for Choices (b) and (c)
    if request.method == 'POST':
        target = public_ctx.handle_suggested_courses_action(request, request.POST, ctx)
        if target:
            return redirect(target)

    context = public_ctx.build_suggested_courses_context(request, ctx)
    return render(request, 'main_front/suggested_courses.html', context)


# ....................................... STUDENT DASHBOARD VIEWS...................................................#
@login_required
def dashboard(request):
    # Context logic lives in page_context/student.py (shared with /api/v1/student/dashboard/).
    from .page_context import student as student_ctx
    try:
        if student_ctx.dashboard_requires_assessment(request.user):
            return redirect("student_assessment")
        return render(request, 'student_dashboard/dashboard.html', student_ctx.build_dashboard_context(request))
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
    (Logic lives in page_context/student.py, shared with /api/v1/student/assessment/.)
    """
    from .page_context import student as student_ctx
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    is_retake = student_ctx.assessment_is_retake(request, profile_obj)

    if request.method == 'POST':
        form = StudentProfileAssessmentForm(request.POST)
        if form.is_valid():
            messages.success(request, student_ctx.save_student_assessment(request, form, profile_obj, is_retake))
            return redirect('suggested_courses')
        else:
            messages.error(request, student_ctx.ASSESSMENT_ERROR_MESSAGE)
    else:
        form = StudentProfileAssessmentForm(initial=student_ctx.assessment_initial(profile_obj))

    context = {
        'form': form,
        'profile': profile_obj,
        'is_retake': is_retake,
    }
    return render(request, 'student_dashboard/assessment.html', context)


@login_required
def profile(request):
    from .page_context import student as student_ctx
    if request.method == "POST":
        from .upload_safety import UploadRejected
        try:
            student_ctx.save_profile(request, request.POST, request.FILES)
        except UploadRejected as exc:
            messages.error(request, str(exc))
        return redirect('profile')

    profile_obj, created = Profile.objects.get_or_create(user=request.user)
    return render(request, "student_dashboard/profile.html", {"profile": profile_obj})

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import AdminCourse, GeneratedCourse, DailyLesson, StudentAssessment

logger = logging.getLogger(__name__)


def get_course_lessons(course):
    """Safe helper to fetch lessons across model schemas (shared copy in page_context.learning)."""
    from .page_context.learning import get_course_lessons as _get_course_lessons
    return _get_course_lessons(course)

@login_required
def course_content_view(request):
    """
    Renders active course syllabus and lessons.
    Self-healing: If an active course exists with 0 lessons, it automatically generates
    the 7-day curriculum via Gemini AI so the user never gets an empty screen.
    """
    from .page_context.learning import build_course_content_context
    return render(request, 'student_dashboard/course_data/course_content.html', build_course_content_context(request))


@login_required
def mycourse(request):
    from .page_context.learning import build_mycourse_context
    return render(request, 'student_dashboard/mycourse.html', build_mycourse_context(request))


@login_required
def course_detail(request, course_id):
    from .page_context.learning import build_course_detail_context
    context = build_course_detail_context(request, course_id)
    if context is None:
        return redirect('mycourse')
    return render(request, 'student_dashboard/mycourse.html', context)


@login_required
def single_lesson_view(request, lesson_id):
    from .page_context.lessons import build_lesson_player_context
    return render(request, 'student_dashboard/course_data/daily_lesson.html',
                  build_lesson_player_context(request, lesson_id))


@login_required
def submit_lesson_step(request, lesson_id):
    if request.method == "POST":
        lesson = get_object_or_404(DailyLesson, id=lesson_id)
        if not can_access_lesson(request.user, lesson):
            raise Http404("Lesson not found")
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
            from .page_context import student as student_ctx
            student_ctx.save_report(request, form)
            messages.success(request, student_ctx.REPORT_SUCCESS_MESSAGE)
            return redirect('reports')
    else:
        form = ReportForm()

    from .page_context.student import student_reports as _student_reports
    student_reports = _student_reports(request.user)
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
    # Logic lives in page_context/student.py (shared with /api/v1/student/notifications/).
    from .page_context import student as student_ctx
    return render(request, 'student_dashboard/notifications.html', student_ctx.build_notifications_context(request))


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Notification, StudentNotificationStatus

@login_required
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
    # Logic lives in page_context/student.py (shared with /api/v1/student/performance/).
    from .page_context import student as student_ctx
    return render(request, 'student_dashboard/performance.html', student_ctx.build_performance_context(request))





from .models import UserSettings
from .forms import UserSettingsForm

@login_required
def settings_view(request):
    from .page_context.student import get_user_settings
    user_settings = get_user_settings(request.user)

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
    return is_alvix_admin(user)


@login_required
def generate_course(request):
    from .page_context.learning import build_generate_course_context, perform_generate_course
    if request.method == 'POST':
        ok_, level, message, target = perform_generate_course(request.user, request.POST)
        messages.add_message(request, messages.SUCCESS if ok_ else messages.ERROR, message)
        return redirect(target)

    return render(request, 'student_dashboard/course_data/generate_course.html', build_generate_course_context(request))


@login_required
def daily_lesson_view(request):
    from .page_context.learning import resolve_current_lesson
    lesson_id, error = resolve_current_lesson(request)
    if lesson_id:
        return redirect('daily_lesson_view', lesson_id=lesson_id)
    messages.error(request, error)
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
    if not can_access_lesson(request.user, lesson):
        raise Http404("Lesson not found")
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
    from .page_context.admin_courses import upload_lesson_ppt, ppt_upload_redirect_url

    lesson = get_object_or_404(DailyLesson, id=lesson_id)
    if request.method == 'POST':
        level, msg = upload_lesson_ppt(lesson, request.FILES.get('ppt_file'))
        if level == 'success':
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    return redirect(ppt_upload_redirect_url(lesson))


@login_required
def download_assignment_pdf(request, submission_id):
    from .models import AssignmentSubmission
    from django.template.loader import render_to_string
    from django.http import HttpResponse

    submission = get_object_or_404(AssignmentSubmission, id=submission_id, user=request.user)
    assignment_prompt = submission.question_prompt or (
        get_saved_or_generated_assignment(submission.lesson)[0] if submission and submission.lesson else ""
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
    from .page_context.admin import build_admin_dashboard_context
    return render(request, 'admin_db/admindashboard.html', build_admin_dashboard_context())


@login_required
@user_passes_test(admin_required)
def user_management(request):
    from .page_context.admin import UserActionError, build_user_management_context, user_management_action
    if request.method == 'POST':
        try:
            message = user_management_action(request.POST)
        except UserActionError as exc:
            messages.error(request, str(exc))
            return redirect('user_management')
        if message:
            messages.success(request, message)
            return redirect('user_management')

    return render(request, 'admin_db/user_management.html', build_user_management_context())


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
    from .page_context.admin import delete_user_by_id
    messages.success(request, delete_user_by_id(user_id))
    return redirect('user_management')


@login_required
@user_passes_test(admin_required)
def courses_info(request):
    from .page_context.admin_courses import build_courses_info_context
    return render(request, 'admin_db/courses_info.html', build_courses_info_context(request))


@login_required
@user_passes_test(admin_required)
def admin_course_detail(request, slug):
    from .page_context.admin_courses import build_course_detail_context
    return render(request, 'admin_db/course_details.html', build_course_detail_context(slug))


@login_required
@user_passes_test(admin_required)
def toggle_system_mode(request):
    messages.success(request, "System mode updated successfully.")
    return redirect('admin_dashboard')


@login_required
@user_passes_test(admin_required)
def analytics(request):
    from .page_context.admin import build_analytics_context
    return render(request, 'admin_db/analytics.html', build_analytics_context())


@login_required
@user_passes_test(admin_required)
def admin_notifications(request):
    from .page_context.admin import build_admin_notifications_context, dispatch_admin_notification
    if request.method == 'POST':
        message = dispatch_admin_notification(request.POST)
        if message:
            messages.success(request, message)
            return redirect('admin_notifications')

    return render(request, 'admin_db/admin_notifications.html', build_admin_notifications_context())


@login_required
@user_passes_test(admin_required)
def add_course(request):
    if request.method == 'POST':
        from .page_context.admin_courses import create_admin_course
        admin_course, msg = create_admin_course(request.POST, request.FILES)
        if admin_course:
            messages.success(request, msg)
            return redirect('courses_info')
    return render(request, 'admin_db/add_course.html')


@login_required
@user_passes_test(admin_required)
def admin_course_level_detail(request, slug):
    from .page_context import admin_courses as ac_ctx
    course_level = ac_ctx.get_course_level(slug)
    force_regen = (request.GET.get('regenerate') == '1' or request.POST.get('action') == 'regenerate')
    regen_msg = ac_ctx.prepare_level_detail(course_level, force_regen)
    if regen_msg:
        messages.success(request, regen_msg)
        return redirect('admin_course_level_detail', slug=slug)
    return render(request, 'admin_db/level_course_view.html', ac_ctx.build_level_detail_context(course_level))


@login_required
@user_passes_test(admin_required)
def admin_regenerate_deep_curriculum(request, slug):
    from .page_context import admin_courses as ac_ctx
    course_level = ac_ctx.get_course_level(slug)
    messages.success(request, ac_ctx.regenerate_level_curriculum(course_level))
    return redirect('admin_course_level_detail', slug=slug)


@login_required
@user_passes_test(admin_required)
def admin_course_level_users(request, slug):
    from .page_context.admin_courses import build_level_users_context
    return render(request, 'admin_db/level_users_telemetry.html', build_level_users_context(slug))


@login_required
def enroll_level_view(request, slug):
    from .page_context.learning import perform_enroll_level
    message, target = perform_enroll_level(request.user, slug)
    messages.success(request, message)
    return redirect(target)


@login_required
@user_passes_test(admin_required)
def admin_reports(request):
    from .page_context.admin import build_admin_reports_context
    return render(request, 'admin_db/admin_reports.html', build_admin_reports_context())


@login_required
@user_passes_test(admin_required)
def send_report_response(request, report_id):
    from .page_context.admin import respond_to_report
    if request.method == 'POST':
        message = respond_to_report(report_id, request.POST)
        if message:
            messages.success(request, message)
    else:
        get_object_or_404(Report, id=report_id)
    return redirect('admin_reports')


@login_required
@user_passes_test(admin_required)
def delete_report(request, report_id):
    from .page_context.admin import delete_report_by_id
    messages.success(request, delete_report_by_id(report_id))
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
    from .page_context.lessons import (
        build_assignment_context, prepare_assignment, resolve_assignment_lesson, submit_assignment,
    )
    active_course, lesson, redirect_to = resolve_assignment_lesson(request, request.GET.get('lesson_id'))
    if redirect_to:
        return redirect(redirect_to)

    state = prepare_assignment(request, active_course, lesson)

    if request.method == 'POST':
        submit_assignment(request, state, request.POST, request.FILES)
        return redirect(f"{request.path}?lesson_id={lesson.id}")

    return render(request, 'student_dashboard/course_data/assignment.html', build_assignment_context(request, state))


@login_required
def quiz_view(request, lesson_id=None):
    """
    Renders diagnostic quizzes with zero delay.
    Issue date is recorded upon student's click/opening.
    Provides marks plus remarks with explanations per wrong answer.
    """
    from .page_context.lessons import build_quiz_context, prepare_quiz, resolve_quiz_lesson, submit_quiz
    if not lesson_id:
        lesson_id = request.GET.get('lesson_id')

    active_course, lesson, redirect_to = resolve_quiz_lesson(request, lesson_id)
    if redirect_to:
        return redirect(redirect_to)

    # Instant access & record issue date
    quiz_questions = prepare_quiz(request, lesson)

    if request.method == 'POST':
        submit_quiz(request, active_course, lesson, quiz_questions, request.POST)
        return redirect(f"{request.path}?lesson_id={lesson.id}")

    return render(request, 'student_dashboard/course_data/quiz.html', build_quiz_context(request, lesson, quiz_questions))


@login_required
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
    from .page_context.learning import build_certificate_context
    locked, context = build_certificate_context(request, course_id)
    if locked:
        return render(request, 'student_dashboard/certificate_locked.html', context)
    return render(request, 'student_dashboard/course_data/certificate.html', context)


@login_required
def download_certificate_pdf(request, course_id):
    """Downloads official server-generated PDF certificate with unique ID and verification QR code."""
    active_course = get_object_or_404(GeneratedCourse, id=course_id) if is_alvix_admin(request.user) else get_object_or_404(GeneratedCourse, id=course_id, user=request.user)
    cert, perf = update_or_create_student_certificate(active_course.user, active_course, request=request)

    is_staff_or_preview = is_alvix_admin(request.user)  # previewing a locked certificate is admin-only
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
    from .page_context.public import build_certificate_verify_context
    return render(request, 'student_dashboard/certificate_verify.html', build_certificate_verify_context(cert_id))


@login_required(login_url='login')
@user_passes_test(admin_required, login_url='login')
def admin_avatar_settings_view(request):
    from .page_context.admin import build_avatar_settings_context
    avatar_settings = AvatarSettings.get_settings()

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

    return render(request, 'admin_db/admin_settings.html', build_avatar_settings_context(form, avatar_settings))
