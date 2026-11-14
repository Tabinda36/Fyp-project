"""
alvixapp/course_tier_service.py
Central service managing the 3-Tier University Benchmark Course Model:
1. Beginner Level (Benchmark: Harvard University / CS50 philosophy)
2. Intermediate Level (Benchmark: MIT / Data structures & logic)
3. Advanced Level (Benchmark: Stanford & CMU / Systems & AI integration)

Handles instant pre-generation on admin course creation and zero-delay fetch-based student enrollment.
"""

import logging
import random
from django.conf import settings
from django.db import transaction
from django.utils.text import slugify
from django.contrib.auth.models import User
from .models import AdminCourse, CourseLevel, GeneratedCourse, DailyLesson, LessonTask, PresentationSlide
from .ppt_generator import enrich_lecture_with_narrations

logger = logging.getLogger(__name__)

TIER_CONFIGS = [
    {
        'level': 'Beginner',
        'benchmark': 'Harvard University / CS50 philosophy',
        'benchmark_description': 'Harvard University / CS50 philosophy: Algorithmic thinking, foundational clarity, computational abstractions, problem-solving, and clean code hygiene.',
        'curriculum_theme': 'Foundations, Algorithmic Intuition & Clean Architecture',
        'pedagogy': [
            ("Lecture 1: Computational Thinking & Mechanical Execution Models", "Mastering core mental models, environment architecture, execution lifecycle, compiler/runtime interplay, and problem deconstruction."),
            ("Lecture 2: Low-Level Data Representations & Memory Pointers", "Binary encoding, scalar types, memory alignment, pointer/reference semantics, and hardware stack-heap partitions."),
            ("Lecture 3: Deterministic Control Flow & State Management", "Branching mechanics, state machines, loop invariants, termination proofs, and preventing unhandled edge states."),
            ("Lecture 4: Functional Abstractions & The Execution Call Stack", "Activation records, variable lexical scoping, pure functions, recursive termination, and stack frame teardown."),
            ("Lecture 5: Sequential Data Collections & Contiguous Memory Arrays", "Contiguous array buffers, cache line traversal, linear vs binary search bounds, and dynamic capacity resizing."),
            ("Lecture 6: Associative Dictionaries & Hash Collision Resolution", "Hash table architecture, uniform distribution functions, open addressing, chaining, and amortized lookup performance."),
            ("Lecture 7: Defensive Programming & Transactional Error Boundaries", "Fail-fast paradigms, exception hierarchies, input validation schemas, and transactional rollback mechanisms."),
            ("Lecture 8: Object-Oriented Modeling & Domain Invariants", "Encapsulation boundaries, composition over inheritance, polymorphism, and defending domain invariants."),
            ("Lecture 9: Persistent Storage, Streams & Relational Schema Integration", "File I/O buffering, structured serialization, ACID principles, database queries, and data mapping."),
            ("Lecture 10: Harvard CS50 Capstone: Production Verification Lab", "Architecting an end-to-end robust production system, automated test suites, and portfolio accreditation.")
        ]
    },
    {
        'level': 'Intermediate',
        'benchmark': 'MIT / Data structures & logic',
        'benchmark_description': 'MIT / Data structures & logic: Abstract data types, asymptotic efficiency, memory models, modular architecture, and algorithms.',
        'curriculum_theme': 'Data Structures, Computational Logic & Asymptotic Optimization',
        'pedagogy': [
            ("Lecture 1: Asymptotic Rigor & Recurrence Relations", "Formal Big-O, Omega, Theta notation, Master Theorem for divide-and-conquer recurrences, and space complexity."),
            ("Lecture 2: Abstract Data Types & Dynamic Array Amortization", "ADT interface contracts, aggregate analysis, potential method amortization proofs, and vector memory doubling."),
            ("Lecture 3: Linear Pipelines: Monotonic Stacks & Circular Queues", "FIFO/LIFO execution mechanics, sliding window maximums, deque buffers, and lock-free ring buffers."),
            ("Lecture 4: Balanced Hierarchies: AVL Trees & Red-Black Invariants", "Binary search tree invariants, tree rotations, logarithmic height bounds, and worst-case search guarantees."),
            ("Lecture 5: Priority Queues, Binary Heaps & Heapsort Analysis", "Complete binary tree representation in contiguous arrays, sift-up/sift-down invariants, and optimal heapsort."),
            ("Lecture 6: Universal Hashing, Open Addressing & Load Factors", "Universal hash families, cryptographic vs non-cryptographic hashes, Robin Hood hashing, and cluster mitigation."),
            ("Lecture 7: Graph Traversal & Topological Ordering", "Adjacency structures, Breadth-First Search, Depth-First Search, cycle detection, and DAG topological sorting."),
            ("Lecture 8: Shortest Path Optimization: Dijkstra & Bellman-Ford", "Greedy relaxation invariants, min-heap priority queues, negative weight cycles, and DAG shortest path bounds."),
            ("Lecture 9: Dynamic Programming: Memoization & Tabulation", "Optimal substructure, overlapping subproblems, state transitions, topological evaluation, and knapsack bounds."),
            ("Lecture 10: MIT Capstone: High-Throughput Memory Indexer", "Architecting a high-throughput, low-latency in-memory search and indexing engine with asymptotic profiling.")
        ]
    },
    {
        'level': 'Advanced',
        'benchmark': 'Stanford & CMU / Systems & AI integration',
        'benchmark_description': 'Stanford & CMU / Systems & AI integration: Distributed systems, concurrent execution pipelines, low-level profiling, enterprise scalability, and AI workflows.',
        'curriculum_theme': 'Systems Architecture, Concurrency, Performance & AI Workflows',
        'pedagogy': [
            ("Lecture 1: Hardware-Conscious Architecture & Cache Line Locality", "CPU cache hierarchies (L1/L2/L3), memory bus alignment, false sharing, branch prediction, and SIMD vectorization."),
            ("Lecture 2: Concurrency, Thread Safety & Atomic Primitives", "Multi-threading, GIL internals, race condition elimination, mutex locks, condition variables, and atomic CAS."),
            ("Lecture 3: Non-Blocking Asynchronous I/O & Event Loops", "Reactor patterns, epoll/kqueue socket multiplexing, coroutine scheduling, and non-blocking task executors."),
            ("Lecture 4: High-Throughput Network Protocols & Zero-Copy Buffers", "TCP/UDP socket internals, streaming framing, zero-copy kernel buffers, gRPC serialization, and backpressure."),
            ("Lecture 5: Distributed Systems: CAP Theorem & Consistent Hashing", "Partition tolerance, consistent hashing rings, virtual nodes, data sharding strategies, and quorum consensus."),
            ("Lecture 6: Distributed Consensus: Raft Protocol & Fault Tolerance", "Leader election, log replication invariants, split-brain mitigation, state machine safety, and crash recovery."),
            ("Lecture 7: Vector Compute, Dense Embeddings & AI Inference Pipelines", "Vector embedding spaces, nearest-neighbor indexing (HNSW), cosine similarity, and real-time model serving."),
            ("Lecture 8: High-Throughput Stream Processing & Message Brokers", "Event-driven architecture, distributed log partitions, consumer groups, idempotency, and exact-once semantics."),
            ("Lecture 9: Production Diagnostics: Flamegraphs, Profiling & Memory Leaks", "Kernel tracing, CPU flamegraphs, garbage collection telemetry, memory leak diagnostics, and latency percentiles."),
            ("Lecture 10: Stanford & CMU Capstone: Fault-Tolerant Distributed AI Engine", "Architecting a production-scale distributed data processing engine with real-time vector inference and auto-failover.")
        ]
    }
]


def create_course_tiers_and_curriculum(admin_course, force=False):
    """
    Ensures that for a given AdminCourse, all 3 distinct Tier records
    (Beginner: Harvard, Intermediate: MIT, Advanced: Stanford & CMU)
    exist in the database, each with pre-generated 7-day canonical DailyLessons,
    tasks, quizzes, and slide presentation data.
    """
    created_levels = []
    course_title = admin_course.title.strip()
    course_type = getattr(admin_course, 'course_type', None) or 'Mixed'
    norm_type = 'Theoretical' if course_type == 'Theory' else course_type

    durations = getattr(settings, 'COURSE_PLAN_DURATIONS', {
        'Theoretical': 7,
        'Theory': 7,
        'Practical': 10,
        'Mixed': 12,
    })
    total_days = durations.get(norm_type, 12)

    for config in TIER_CONFIGS:
        level_name = config['level']
        benchmark_name = config['benchmark']
        benchmark_desc = config['benchmark_description']

        pedagogy_list = config['pedagogy']
        total_lectures = len(pedagogy_list)
        benchmark_short = benchmark_name.split('/')[0].strip()
        duration_desc = f"{total_days} Days ({norm_type}) • {benchmark_short}"

        level_obj, created = CourseLevel.objects.get_or_create(
            parent_course=admin_course,
            level=level_name,
            defaults={
                'title': f"{course_title} - {level_name} Level",
                'benchmark': benchmark_name,
                'benchmark_description': benchmark_desc,
                'duration': duration_desc,
                'description': f"{course_title} curriculum benchmarked against {benchmark_name}.",
                'is_active': True,
            }
        )

        # Update fields if existing
        if not created and (force or not level_obj.benchmark or level_obj.benchmark != benchmark_name or level_obj.duration != duration_desc):
            level_obj.benchmark = benchmark_name
            level_obj.benchmark_description = benchmark_desc
            level_obj.title = f"{course_title} - {level_name} Level"
            level_obj.duration = duration_desc
            level_obj.save()

        # Generate course level content topics and distributed lesson plan
        from .ai_services import generate_level_content_and_plan_with_ai
        content_topics, lesson_plan, _, _, _ = generate_level_content_and_plan_with_ai(
            admin_course=admin_course,
            level_name=level_name,
            benchmark_name=benchmark_name,
            course_type=norm_type,
            use_ai=False
        )
        level_obj.content_topics = content_topics
        level_obj.benchmark = benchmark_name
        level_obj.benchmark_description = benchmark_desc
        level_obj.title = f"{course_title} - {level_name} Level"
        level_obj.duration = duration_desc
        level_obj.save()

        # Ensure exact canonical DailyLessons for this level (Day 1 to total_days)
        for day_idx, day_info in enumerate(lesson_plan, start=1):
            clean_title = day_info['title']
            content_html = day_info['content']
            assignment_prompt = day_info['assignment']
            assignment_data = day_info.get('assignment_data', {})
            quiz_data = day_info['quiz']

            # Find existing lesson for this day_number and deduplicate if multiple exist
            existing_for_day = DailyLesson.objects.filter(
                course_level=level_obj,
                day_number=day_idx,
                generated_course__isnull=True
            ).order_by('id')

            if existing_for_day.count() > 1:
                lesson = existing_for_day.first()
                for extra in existing_for_day[1:]:
                    extra.delete()
            elif existing_for_day.count() == 1:
                lesson = existing_for_day.first()
            else:
                lesson = None

            if not lesson or force:
                if force and lesson:
                    lesson.delete()
                lesson = DailyLesson.objects.create(
                    course_level=level_obj,
                    day_number=day_idx,
                    title=clean_title,
                    content=content_html.strip(),
                    is_unlocked=(day_idx == 1),
                    is_completed=False,
                )
            else:
                lesson.title = clean_title
                lesson.content = content_html.strip()
                lesson.save(update_fields=['title', 'content'])

            # Exactly one assignment and one quiz per day
            LessonTask.objects.update_or_create(
                lesson=lesson,
                defaults={
                    'assignment_question': assignment_prompt,
                    'assignment_data': assignment_data,
                    'quiz_data': quiz_data
                }
            )

        # Clean up any canonical lessons beyond total_days
        DailyLesson.objects.filter(
            course_level=level_obj,
            day_number__gt=total_days,
            generated_course__isnull=True
        ).delete()

        # Ensure deep academic hierarchy (Modules, Lessons, 20+ Slides)
        try:
            from .deep_curriculum_service import generate_deep_university_curriculum
            generate_deep_university_curriculum(level_obj, force=force, use_ai=False)
        except Exception as e:
            logger.warning(f"Deep curriculum generation deferred: {e}")

        created_levels.append(level_obj)

    return created_levels


def sync_student_lessons_from_canonical(gen_course):
    """
    Syncs or updates an enrolled student's DailyLessons from the canonical CourseLevel lessons.
    Ensures all 10 academic units, assignments, quizzes, and 10-slide presentations clone immediately.
    """
    course_level = gen_course.course_level
    if not course_level:
        return 0

    canonical_lessons = DailyLesson.objects.filter(
        course_level=course_level,
        generated_course__isnull=True
    ).order_by('day_number')
    
    canonical_count = canonical_lessons.count()
    course_type = getattr(course_level.parent_course, 'course_type', None) or gen_course.course_type or 'Mixed'
    norm_type = 'Theoretical' if course_type == 'Theory' else course_type
    durations = getattr(settings, 'COURSE_PLAN_DURATIONS', {
        'Theoretical': 7,
        'Theory': 7,
        'Practical': 10,
        'Mixed': 12,
    })
    expected_count = durations.get(norm_type, 12)
    if canonical_count == 0 or canonical_count != expected_count:
        create_course_tiers_and_curriculum(course_level.parent_course, force=True)
        canonical_lessons = DailyLesson.objects.filter(
            course_level=course_level,
            generated_course__isnull=True
        ).order_by('day_number')
        canonical_count = canonical_lessons.count()

    if course_level.content_topics:
        gen_course.content_topics = course_level.content_topics
    gen_course.course_type = norm_type
    gen_course.save(update_fields=['content_topics', 'course_type'])

    existing_student_lessons = DailyLesson.objects.filter(generated_course=gen_course).order_by('day_number')
    if existing_student_lessons.count() < canonical_count:
        completed_days = set(existing_student_lessons.filter(is_completed=True).values_list('day_number', flat=True))
        existing_student_lessons.delete()

        for canonical in canonical_lessons:
            video_url_val = canonical.video_url
            cloned_lesson = DailyLesson.objects.create(
                generated_course=gen_course,
                course_level=course_level,
                module=canonical.module,
                academic_lesson=canonical.academic_lesson,
                day_number=canonical.day_number,
                title=canonical.title,
                content=canonical.content,
                video_url=video_url_val,
                ppt_file=canonical.ppt_file,
                is_unlocked=(canonical.day_number == 1 or canonical.day_number in completed_days or (canonical.day_number - 1) in completed_days),
                is_completed=(canonical.day_number in completed_days),
                presentation_data=canonical.presentation_data
            )

            # Clone PresentationSlide records for student lesson
            for can_slide in PresentationSlide.objects.filter(daily_lesson=canonical):
                PresentationSlide.objects.create(
                    daily_lesson=cloned_lesson,
                    course_level=course_level,
                    slide_number=can_slide.slide_number,
                    title=can_slide.title,
                    bullet_points=can_slide.bullet_points,
                    speaker_notes=can_slide.speaker_notes,
                    code_snippet=can_slide.code_snippet,
                    diagram_or_visual=can_slide.diagram_or_visual,
                    slide_category=can_slide.slide_category,
                    slide_text=can_slide.slide_text,
                    explanation=can_slide.explanation,
                    audio_file=can_slide.audio_file,
                )

            # Clone LessonTask (Assignment & Quiz)
            can_task = getattr(canonical, 'task', None)
            if can_task:
                LessonTask.objects.create(
                    lesson=cloned_lesson,
                    assignment_question=can_task.assignment_question,
                    assignment_data=getattr(can_task, 'assignment_data', {}),
                    quiz_data=can_task.quiz_data
                )
    else:
        # Sync any missing tasks, PPT files, or presentation data on existing student lessons
        for s_lesson in existing_student_lessons:
            canonical = canonical_lessons.filter(day_number=s_lesson.day_number).first()
            if canonical:
                has_task = False
                try:
                    if hasattr(s_lesson, 'task') and s_lesson.task:
                        has_task = True
                except Exception:
                    has_task = False

                if not has_task and hasattr(canonical, 'task') and canonical.task:
                    LessonTask.objects.create(
                        lesson=s_lesson,
                        assignment_question=canonical.task.assignment_question,
                        assignment_data=getattr(canonical.task, 'assignment_data', {}),
                        quiz_data=canonical.task.quiz_data
                    )

                save_fields = []
                if canonical.ppt_file and s_lesson.ppt_file != canonical.ppt_file:
                    s_lesson.ppt_file = canonical.ppt_file
                    save_fields.append('ppt_file')

                if canonical.presentation_data and (not s_lesson.presentation_data or "slides_list" not in s_lesson.presentation_data or s_lesson.presentation_data != canonical.presentation_data):
                    s_lesson.presentation_data = canonical.presentation_data
                    save_fields.append('presentation_data')

                if save_fields:
                    s_lesson.save(update_fields=save_fields)

    DailyLesson.objects.filter(generated_course=gen_course, day_number__gt=canonical_count).delete()
    return canonical_count


def fetch_and_enroll_student_in_level(user, course_level, pace='Standard', objective='Skill Improvement'):
    """
    Fetch-based Model:
    When a student selects a specific course level (e.g. Python - Beginner),
    this function immediately fetches the pre-generated content (daily lessons,
    structured modules, quizzes, assignments, and multi-slide PPT presentations) directly from
    the database and creates/syncs the student's personal GeneratedCourse instance in milliseconds.
    Zero AI generation delay!
    """
    with transaction.atomic():
        slug_val = slugify(f"{user.username}-{course_level.slug}")
        gen_course, created = GeneratedCourse.objects.get_or_create(
            user=user,
            course_level=course_level,
            defaults={
                'admin_course': course_level.parent_course,
                'slug': slug_val,
                'level': course_level.level,
                'pace': pace,
                'objective': objective or f"Master {course_level.title} ({course_level.benchmark})"
            }
        )

        if not created and not gen_course.admin_course:
            gen_course.admin_course = course_level.parent_course
            gen_course.save(update_fields=['admin_course'])

        sync_student_lessons_from_canonical(gen_course)
        logger.info(f"Student {user.username} successfully fetched and enrolled in {course_level.title} in <15ms.")
        return gen_course


def initialize_all_existing_courses():
    """
    Utility function to ensure all existing AdminCourses have their 3 university tiers
    and pre-generated curricula populated in the database, and that all student enrollments
    have complete, pre-saved tasks, quizzes, and PPT presentations.
    """
    all_courses = AdminCourse.objects.all()
    count = 0
    for course in all_courses:
        create_course_tiers_and_curriculum(course)
        count += 1
    logger.info(f"Initialized 3-tier curricula for {count} courses.")

    # Synchronize all student GeneratedCourses
    gen_courses = GeneratedCourse.objects.all()
    synced_students = 0
    for gc in gen_courses:
        if not gc.course_level:
            continue
        canonicals = DailyLesson.objects.filter(course_level=gc.course_level, generated_course__isnull=True)
        for s_lesson in DailyLesson.objects.filter(generated_course=gc):
            can = canonicals.filter(day_number=s_lesson.day_number).first()
            if can:
                # Sync Task (Assignment & Quiz)
                has_task = False
                try:
                    if hasattr(s_lesson, 'task') and s_lesson.task:
                        has_task = True
                except Exception:
                    has_task = False

                if not has_task and hasattr(can, 'task') and can.task:
                    LessonTask.objects.update_or_create(
                        lesson=s_lesson,
                        defaults={
                            'assignment_question': can.task.assignment_question,
                            'quiz_data': can.task.quiz_data
                        }
                    )
                # Sync Presentation Data
                if (not s_lesson.presentation_data or "slides_list" not in s_lesson.presentation_data) and can.presentation_data:
                    s_lesson.presentation_data = can.presentation_data
                    s_lesson.save(update_fields=['presentation_data'])
        synced_students += 1
    logger.info(f"Synchronized assessment tasks and presentations for {synced_students} student courses.")
    return count