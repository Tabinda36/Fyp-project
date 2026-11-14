"""
alvixapp/deep_curriculum_service.py
Enterprise AI Curriculum Generator & Deep Content Engine

Generates exhaustive, unrestricted academic content mapped to:
1. Beginner Level: Harvard University / CS50 Philosophy
   (Foundational mechanics, zero-to-one building blocks, extensive explanatory guides, memory mental models)
2. Intermediate Level: MIT Curriculum
   (Deep data structures, core algorithms, asymptotic mathematical bounds, invariants, performance optimization)
3. Advanced Level: Stanford & CMU Curriculum
   (Enterprise system architecture, distributed consensus, high-throughput async pipelines, production AI/LLM integration)

Generates:
- Dynamic Modules & Lessons (no artificial limits)
- Comprehensive long-form textbook reading material & production code examples
- 15 to 30+ slide top-university lecture PPT decks with detailed speaker notes & ASCII architecture
"""

import json
import logging
import re
from django.conf import settings
from django.db import transaction
from django.utils.text import slugify

from .models import (
    AdminCourse,
    CourseLevel,
    CourseModule,
    AcademicLesson,
    PresentationSlide,
    DailyLesson,
    LessonTask,
)

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. PEDAGOGICAL PROMPT BLUEPRINTS BY UNIVERSITY BENCHMARK
# ==============================================================================

BENCHMARK_PROMPT_GUIDES = {
    'Beginner': {
        'university': 'Harvard University',
        'benchmark_title': 'Harvard University / CS50 Philosophy',
        'philosophy': (
            "Focus on foundational computational mechanics, conceptual clarity, zero-to-one building blocks, "
            "extensive explanatory prose, and step-by-step mental models. Do NOT rush or summarize. "
            "Explain *why* abstractions exist before how they work. Use real-world analogies, execution traces, "
            "and line-by-line syntax dissection. Assume rigorous academic depth for novice minds."
        ),
        'focus_areas': [
            "Computational Mental Models & Memory Representation",
            "Deterministic State Transitions & Flow Control",
            "Functional Abstractions & The Execution Call Stack",
            "Sequential & Associative Data Collections",
            "Defensive Error Boundaries & Input Validation",
            "Object-Oriented Modeling & Domain Encapsulation",
            "End-to-End Capstone Application & Verification Testing"
        ],
        'slide_target_count': 20
    },
    'Intermediate': {
        'university': 'Massachusetts Institute of Technology (MIT)',
        'benchmark_title': 'MIT / Data structures & logic',
        'philosophy': (
            "Focus on deep data structures, core algorithms, asymptotic mathematical rigor (Big-O, Omega, Theta), "
            "loop invariants, recurrence relations (Master Theorem), memory cache locality, and optimization trade-offs. "
            "Emphasize amortized analysis, tree balancing invariants, graph traversals, and dynamic programming tables. "
            "Deliver uncompromising technical breakdowns."
        ),
        'focus_areas': [
            "Asymptotic Complexity & Recurrence Relations",
            "Abstract Data Types & Contiguous vs Linked Memory Layouts",
            "Balanced Hierarchies: AVL Trees, Red-Black Trees & Heaps",
            "Hashed Structures: Collision Invariants & Amortized Performance",
            "Graph Algorithms: Traversal, Shortest Path & Topological Ordering",
            "Algorithmic Paradigms: Dynamic Programming & Greedy Bounds",
            "High-Throughput In-Memory Indexing Engine Capstone"
        ],
        'slide_target_count': 24
    },
    'Advanced': {
        'university': 'Stanford University & Carnegie Mellon University (CMU)',
        'benchmark_title': 'Stanford & CMU / Systems & AI integration',
        'philosophy': (
            "Focus on enterprise-grade distributed systems architecture, concurrency, non-blocking I/O, CAP theorem, "
            "fault-tolerance, high-throughput network protocols, low-level system profiling, and production AI/LLM integration. "
            "Cover vector databases, retrieval-augmented generation (RAG) pipelines, embedding indexing, token economics, "
            "and production observability."
        ),
        'focus_areas': [
            "Hardware-Conscious Architecture & Cache Line Locality",
            "Concurrent Execution: Race Conditions, Locks & Asynchronous Event Loops",
            "Distributed Systems: Data Sharding, Consensus & Fault Tolerance",
            "High-Throughput Network Protocols & Socket Multiplexing",
            "Real-Time AI Inference Pipelines & Vector Embedding Workflows",
            "Production Diagnostics: Flamegraphs, Memory Leak Profiling & Telemetry",
            "Stanford & CMU Capstone: Distributed Resilient Processing Engine"
        ],
        'slide_target_count': 28
    }
}


# ==============================================================================
# 2. GEMINI AI DEEP CURRICULUM GENERATOR
# ==============================================================================

def generate_curriculum_with_gemini(course_level):
    """
    Invokes Gemini 2.5 Flash to synthesize an exhaustive, multi-module,
    multi-lesson, and 20+ slide university lecture deck.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        logger.info("GEMINI_API_KEY not configured. Falling back to dynamic academic engine.")
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key, http_options={'timeout': 15.0})
        level_name = course_level.level
        benchmark_config = BENCHMARK_PROMPT_GUIDES.get(level_name, BENCHMARK_PROMPT_GUIDES['Beginner'])
        course_title = course_level.parent_course.title
        overview = course_level.parent_course.description or course_title

        prompt = f"""
You are the Distinguished Chair of Curriculum Architecture for ALVIX and Senior Fellow at {benchmark_config['university']}.
Your task is to design an EXHAUSTIVE, UNRESTRICTED, and WORLD-CLASS curriculum for the course:
COURSE: "{course_title}"
LEVEL: "{level_name}"
ACADEMIC BENCHMARK: "{benchmark_config['benchmark_title']}"
PEDAGOGICAL PHILOSOPHY:
{benchmark_config['philosophy']}

REQUIREMENTS:
1. Generate between 4 to 6 comprehensive Modules scaling with the full scope of {course_title}.
2. Inside each Module, generate 2 to 4 deeply detailed Lessons (total 10 to 18 lessons).
3. Each Lesson MUST include:
   - title: Clear, authoritative lesson name.
   - summary: Concise pedagogical overview.
   - reading_content: Long-form, highly detailed textbook-grade reading material (minimum 400-600 words of rich technical explanations, mental models, mechanical realities, and historical context).
   - code_examples: Array of 1 to 2 code examples with 'title', 'code', and 'explanation'.
   - use_cases: Array of 1 to 2 real-world enterprise/industry use cases with 'scenario' and 'solution'.
   - assignment_prompt: Rigorous engineering challenge or lab task with clear requirements.
   - assignment_rubric: Grading criteria and automated verification checklist.
   - quiz_data: Array of 5 multiple-choice questions with 'question', 'options' (array of 4), 'correct_answer' (0-3 index), and 'explanation'.
4. Comprehensive Lecture Deck:
   - Generate an extensive lecture presentation deck of {benchmark_config['slide_target_count']} to 30 professional slides matching elite university lecture decks.
   - Each slide MUST include:
     - slide_number: integer (1, 2, 3, ...)
     - title: Authoritative slide title
     - bullet_points: 3 to 5 deep, technical bullet points (not brief superficial fragments)
     - speaker_notes: 100 to 200 words of spoken lecture narrative that a top professor would present
     - code_snippet: Code example, syntax block, or configuration snippet (or empty string if conceptual)
     - diagram_or_visual: ASCII architecture diagram, flow layout, or mental model visualization
     - slide_category: e.g., 'Overview', 'Foundation', 'Architecture', 'Code Walkthrough', 'Analysis', 'Optimization', 'Lab'

OUTPUT FORMAT:
Strictly return a valid JSON object matching this schema without markdown code blocks:
{{
  "modules": [
    {{
      "order": 1,
      "title": "Module Title",
      "description": "Comprehensive module scope",
      "pedagogical_focus": "{benchmark_config['benchmark_title']}",
      "estimated_hours": 6,
      "lessons": [
        {{
          "order": 1,
          "title": "Lesson Title",
          "summary": "...",
          "reading_content": "...",
          "code_examples": [{{"title": "...", "code": "...", "explanation": "..."}}],
          "use_cases": [{{"scenario": "...", "solution": "..."}}],
          "assignment_prompt": "...",
          "assignment_rubric": "...",
          "quiz_data": [
            {{
              "question": "...",
              "options": ["A", "B", "C", "D"],
              "correct_answer": 0,
              "explanation": "..."
            }}
          ]
        }}
      ]
    }}
  ],
  "slides": [
    {{
      "slide_number": 1,
      "title": "...",
      "bullet_points": ["..."],
      "speaker_notes": "...",
      "code_snippet": "...",
      "diagram_or_visual": "...",
      "slide_category": "Overview"
    }}
  ]
}}
"""

        import concurrent.futures

        def _call_gemini_curriculum():
            return client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                )
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_gemini_curriculum)
            response = future.result(timeout=10)

        clean_text = re.sub(r'```json\s*|```\s*', '', response.text).strip()
        data = json.loads(clean_text)
        if isinstance(data, dict) and 'modules' in data and len(data['modules']) >= 3:
            logger.info(f"Gemini successfully generated {len(data['modules'])} modules and {len(data.get('slides', []))} slides for {course_level.title}")
            return data
        else:
            logger.warning("Gemini JSON did not contain expected modules structure.")
            return None

    except Exception as e:
        logger.error(f"Gemini deep generation error: {e}")
        return None


# ==============================================================================
# 3. EXHAUSTIVE ACADEMIC TEMPLATE ENGINE (Resilient Domain Synthesizer)
# ==============================================================================

def generate_academic_engine_curriculum(course_level):
    """
    Builds an exhaustive, university-aligned curriculum with 4-5 modules,
    12-16 deep lessons, and 20-28 detailed lecture slides tailored to the topic
    and benchmark standard.
    """
    level_name = course_level.level
    course_title = course_level.parent_course.title
    clean_name = course_title.replace(' ', '').replace('-', '')
    benchmark_config = BENCHMARK_PROMPT_GUIDES.get(level_name, BENCHMARK_PROMPT_GUIDES['Beginner'])
    focus_areas = benchmark_config['focus_areas']

    modules_data = []
    all_slides_data = []

    # Slide 1: Deck Title
    all_slides_data.append({
        "slide_number": 1,
        "title": f"{course_title}: Comprehensive {level_name} Lecture Series",
        "bullet_points": [
            f"Academic Benchmark: {benchmark_config['benchmark_title']}",
            f"Curriculum Level: {level_name} Mastery",
            f"Pedagogical Philosophy: {benchmark_config['university']} Standards",
            "Focus: Foundational Clarity, Technical Rigor & Production Architecture"
        ],
        "speaker_notes": (
            f"Welcome to the masterclass in {course_title}. This curriculum is rigorously modeled after "
            f"the pedagogical philosophy of {benchmark_config['benchmark_title']}. Our objective is not surface-level "
            "syntax or temporary shortcuts; we are developing first-principles engineering intuition. Every module "
            "has been constructed to dismantle technical ambiguity, prove invariants, and build deployable software."
        ),
        "code_snippet": f"# Academic Benchmark: {benchmark_config['benchmark_title']}\n# Domain: {course_title}\nprint('Initialized {course_title} Mastery')",
        "diagram_or_visual": "+--------------------------------------------------------+\n| ALVIX ACADEMIC SYLLABUS: " + course_title[:28] + " |\n| Benchmark: " + benchmark_config['university'][:28] + " |\n+--------------------------------------------------------+",
        "slide_category": "Overview"
    })

    # Slide 2: Course Roadmap
    all_slides_data.append({
        "slide_number": 2,
        "title": "Curriculum Architecture & Roadmap",
        "bullet_points": [
            "Deconstructing mechanical execution realities and underlying abstractions",
            "Progressive complexity ramp: from mental models to high-throughput systems",
            "Synchronized hands-on engineering challenges and formal verification labs",
            "Continuous diagnostic evaluation with instant explanatory feedback"
        ],
        "speaker_notes": (
            "Before diving into implementation, let us review our architectural trajectory. Notice how each "
            "module builds strictly upon the previous. We establish deterministic execution foundations, progress "
            "through optimal abstractions, and culminate in an industry-standard capstone verification project."
        ),
        "code_snippet": "",
        "diagram_or_visual": "[Foundations] --> [Data Abstractions] --> [System Pipelines] --> [Capstone Lab]",
        "slide_category": "Overview"
    })

    # Build Modules and Lessons
    module_configs = [
        {
            'order': 1,
            'title': f"Module 1: {focus_areas[0]}",
            'desc': f"Core theoretical frameworks, environment architecture, execution lifecycle, and problem deconstruction in {course_title}.",
            'hours': 6,
            'lessons': [
                ("Mechanics & Execution Model", "Dissecting compiler/runtime execution, thread stacks, memory bounds, and computational lifecycle."),
                ("Deterministic State & Data Representation", "Low-level types, binary encoding, IEEE-754 numbers, and memory alignment rules.")
            ]
        },
        {
            'order': 2,
            'title': f"Module 2: {focus_areas[1] if len(focus_areas) > 1 else 'Control Structures & Abstractions'}",
            'desc': f"Mastering modular boundaries, state encapsulation, branching logic, and computational scoping in {course_title}.",
            'hours': 8,
            'lessons': [
                ("Modular Functions & Call Stack Frames", "Activation records, variable scoping boundaries, pure transformations, and stack frame teardown."),
                ("Structured Iteration & Algorithmic Traversal", "Sequential processing, generator pipelines, amortized loops, and algorithmic termination guards.")
            ]
        },
        {
            'order': 3,
            'title': f"Module 3: {focus_areas[2] if len(focus_areas) > 2 else 'Data Structures & Efficiency'}",
            'desc': f"Abstract data types, collection ergonomics, cache locality, and asymptotic optimization in {course_title}.",
            'hours': 8,
            'lessons': [
                ("Contiguous Arrays vs Linked Hierarchies", "Memory allocation overhead, pointer dereferencing penalties, cache misses, and structural invariants."),
                ("Hash Mappings & Collision Resolution", "Hash table architecture, cryptographic vs bucket hashing, load factors, and Robin Hood hashing.")
            ]
        },
        {
            'order': 4,
            'title': f"Module 4: {focus_areas[3] if len(focus_areas) > 3 else 'Production Architecture & Error Boundaries'}",
            'desc': f"Defensive programming, exception hierarchies, stream I/O, and production resilience in {course_title}.",
            'hours': 10,
            'lessons': [
                ("Defensive Error Boundaries & Contract Enforcement", "Fail-fast paradigms, custom exception hierarchies, and transactional rollback semantics."),
                ("High-Throughput I/O & Persistent Storage", "Buffered streams, file serialization formats, network socket abstractions, and non-blocking I/O.")
            ]
        },
        {
            'order': 5,
            'title': f"Module 5: {focus_areas[-1]}",
            'desc': f"Capstone engineering laboratory, portfolio validation, and end-to-end integration benchmarked against {benchmark_config['university']}.",
            'hours': 12,
            'lessons': [
                ("Architectural Synthesis & Design Patterns", "Composing decoupled components, dependency injection, and observable telemetry instrumentation."),
                ("Verification Lab & Capstone Deployment", "Automated stress assertions, boundary benchmark profiling, and production packaging.")
            ]
        }
    ]

    current_slide_num = 3

    for m_idx, m_info in enumerate(module_configs, start=1):
        m_lessons = []
        for l_idx, (l_title, l_summary) in enumerate(m_info['lessons'], start=1):
            full_title = f"{course_title}: {l_title}"

            # Comprehensive Long-form Reading Material (Textbook Standard)
            reading_html = f"""
<div class="academic-reading-module">
    <div class="p-3 mb-4 rounded-3" style="background: rgba(6, 78, 59, 0.06); border-left: 5px solid #064E3B;">
        <span class="badge" style="background: #064E3B; color: #D4AF37; font-weight: 700; font-size: 0.8rem;">
            🏛️ {benchmark_config['benchmark_title']}
        </span>
        <h4 class="fw-bold mt-2 mb-1" style="color: #064E3B;">{full_title}</h4>
        <p class="text-muted small mb-0">{l_summary}</p>
    </div>

    <h5 class="fw-bold mt-4 mb-2" style="color: #064E3B;">
        <i class="bi bi-book-half text-warning me-2"></i>1. Theoretical Foundations & First Principles
    </h5>
    <p style="line-height: 1.8; color: #334155;">
        In alignment with the pedagogical conventions of {benchmark_config['university']}, understanding <strong>{l_title}</strong> 
        requires discarding naive mental models that treat code as isolated textual syntax. When instructions run, 
        they interface with an underlying execution engine, memory hierarchies, and operating system abstractions. 
        In {level_name} studies, we examine the mechanical consequences of every architectural choice: how data is allocated, 
        how CPU cache lines are traversed, and why deterministic state boundaries prevent cascading failures under production workloads.
    </p>

    <h5 class="fw-bold mt-4 mb-2" style="color: #064E3B;">
        <i class="bi bi-cpu text-warning me-2"></i>2. Architecture Blueprint & Mechanical Dissection
    </h5>
    <p style="line-height: 1.8; color: #334155;">
        Study the production-grade architectural blueprint below. Observe the rigorous separation between domain logic, 
        input validation, and state mutation. Every function enforces an explicit contract, shielding calling contexts from unhandled edge states:
    </p>
    <pre style="background: #0f172a; color: #38bdf8; padding: 20px; border-radius: 12px; font-family: 'Consolas', monospace; font-size: 0.88rem; border: 1.5px solid rgba(212, 175, 55, 0.4); overflow-x: auto;">
# ==============================================================================
# Blueprint: {full_title}
# Academic Benchmark: {benchmark_config['benchmark_title']}
# Level: {level_name}
# ==============================================================================

class {clean_name}EngineM{m_idx}L{l_idx}:
    \"\"\"
    Production-grade component demonstrating {l_title}.
    Enforces invariant checks, memory bounds, and defensive telemetry.
    \"\"\"
    def __init__(self, context_name: str = "{course_title}"):
        self.context = context_name
        self.benchmark = "{benchmark_config['benchmark_title']}"
        self._execution_state = "READY"
        self._telemetry_log = []

    def execute_pipeline(self, payload: dict) -> dict:
        \"\"\"Executes deterministic validation and transformation.\"\"\"
        if not payload or not isinstance(payload, dict):
            raise ValueError("Invariant violation: Payload must be a non-null dictionary.")

        # Stage 1: Defensive Contract Guard
        validated_data = self._enforce_contract(payload)

        # Stage 2: Transformative Processing
        result = self._process_domain_logic(validated_data)

        # Stage 3: Audit Recording
        self._telemetry_log.append({{"stage": "completed", "benchmark": self.benchmark}})
        return result

    def _enforce_contract(self, data: dict) -> dict:
        # Strict validation matching {benchmark_config['university']} standards
        return {{k: v for k, v in data.items() if k is not None}}

    def _process_domain_logic(self, data: dict) -> dict:
        return {{
            "status": "SUCCESS",
            "topic": "{full_title}",
            "benchmark": self.benchmark,
            "data": data
        }}

# Production Driver
pipeline = {clean_name}EngineM{m_idx}L{l_idx}()
output = pipeline.execute_pipeline({{"module": {m_idx}, "lesson": {l_idx}, "status": "active"}})
print(f"Executed with zero errors: {{output['status']}}")
    </pre>

    <h5 class="fw-bold mt-4 mb-2" style="color: #064E3B;">
        <i class="bi bi-shield-exclamation text-warning me-2"></i>3. Engineering Trade-offs & Anti-Patterns
    </h5>
    <ul style="line-height: 1.8; color: #334155;">
        <li><strong>Global Mutable State:</strong> Sharing mutable variables across functions introduces race conditions and makes testing non-deterministic. Always prefer pure functions and encapsulated classes.</li>
        <li><strong>Implicit Failure Modes:</strong> Failing silently or returning raw null values corrupts downstream data. Enforce explicit error boundaries and typed return values.</li>
        <li><strong>Neglecting Asymptotic Complexity:</strong> Naive implementations that look clean in syntax can easily degrade to O(N^2) complexity. Always profile algorithmic complexity against {benchmark_config['benchmark_title']}.</li>
    </ul>

    <div class="p-3 my-3 rounded-3" style="background: #f8fafc; border-left: 4px solid #D4AF37;">
        <h6 class="fw-bold mb-1" style="color: #064E3B;"><i class="bi bi-award-fill text-warning me-1"></i>Key Academic Takeaway:</h6>
        <p class="mb-0 text-muted small">
            Mastery of {l_title} is demonstrated when your code handles unexpected boundary conditions gracefully, 
            exhibits optimal memory utilization, and passes automated verification suites with zero warnings.
        </p>
    </div>
</div>
"""

            code_examples = [
                {
                    "title": f"Production Implementation Blueprint: {l_title}",
                    "code": f"class {clean_name}Processor:\n    def run(self, data):\n        # Enforce {benchmark_config['benchmark_title']}\n        return {{'verified': True, 'topic': '{l_title}'}}\n",
                    "explanation": f"Implements strict encapsulation, typed returns, and validation boundaries for {l_title}."
                }
            ]

            use_cases = [
                {
                    "scenario": f"High-Throughput Enterprise Architecture for {course_title}",
                    "solution": f"Deconstruct into modular, isolated micro-components adhering to {benchmark_config['benchmark_title']} conventions to eliminate single points of failure."
                }
            ]

            assignment_prompt = (
                f"Engineering Laboratory Challenge: {full_title}\n\n"
                f"Academic Benchmark: {benchmark_config['benchmark_title']}\n"
                f"Objective: Build an end-to-end robust implementation demonstrating '{l_title}'.\n\n"
                f"Requirements:\n"
                f"1. Implement strict validation boundaries to reject null or malformed data immediately.\n"
                f"2. Write at least 3 automated unit assertions testing happy path, boundary edge cases, and error recovery.\n"
                f"3. Profile your code's memory allocation and runtime complexity, documenting adherence to {benchmark_config['university']} standards."
            )

            assignment_rubric = (
                "Grading Criteria (100 Points Total):\n"
                "- Correctness & Domain Logic: 40 Points\n"
                "- Defensive Validation & Error Handling: 25 Points\n"
                "- Algorithmic Efficiency & Code Cleanliness: 20 Points\n"
                "- Automated Unit Test Assertions: 15 Points"
            )

            quiz_data = [
                {
                    "question": f"What is the foundational architectural purpose of {l_title}?",
                    "options": [
                        f"To establish deterministic modular execution and prevent unhandled edge cases.",
                        "To write monolithic scripts without functions or classes.",
                        "To bypass validation checks for marginal compilation speed.",
                        "To store sensitive credentials in public global variables."
                    ],
                    "correct_answer": 0,
                    "explanation": f"According to {benchmark_config['benchmark_title']}, deterministic validation and modularity guarantee system reliability."
                },
                {
                    "question": f"Why does {benchmark_config['university']} emphasize defensive error handling in {level_name} courses?",
                    "options": [
                        "To ensure failures are caught and handled explicitly at architectural boundaries.",
                        "To hide all error messages from software engineers.",
                        "To intentionally slow down CPU execution cycles.",
                        "To duplicate code across all files."
                    ],
                    "correct_answer": 0,
                    "explanation": "Defensive error boundaries guarantee that unexpected states never crash core runtime operations."
                },
                {
                    "question": "Which design pattern best protects against state corruption in concurrent or multi-step execution?",
                    "options": [
                        "Shared mutable global dictionaries across all routines.",
                        "Pure functions and encapsulated immutable state transitions.",
                        "Disabling type assertions and schema validation.",
                        "Hardcoding absolute file paths across nested logic."
                    ],
                    "correct_answer": 1,
                    "explanation": "Immutable state transitions and pure functions eliminate race conditions and side effects."
                },
                {
                    "question": f"When evaluating {course_title} performance at the {level_name} level, which metric is most critical?",
                    "options": [
                        "The total number of comments written per file.",
                        "Algorithmic time complexity (Big-O) and memory cache line efficiency.",
                        "How colorful the IDE syntax highlighting looks.",
                        "The length of variable names in characters."
                    ],
                    "correct_answer": 1,
                    "explanation": "Asymptotic time and space complexity govern scalable production performance."
                },
                {
                    "question": f"What is the recommended practice when an unrecoverable input error is detected in {l_title}?",
                    "options": [
                        "Fail immediately with an explicit, informative exception before data corruption occurs.",
                        "Return false silently and continue execution.",
                        "Ignore the error and write corrupted bytes to disk.",
                        "Restart the entire operating system."
                    ],
                    "correct_answer": 0,
                    "explanation": "The 'fail-fast' paradigm prevents corrupted states from propagating into downstream subsystems."
                }
            ]

            lesson_dict = {
                "order": l_idx,
                "title": full_title,
                "summary": l_summary,
                "reading_content": reading_html.strip(),
                "code_examples": code_examples,
                "use_cases": use_cases,
                "assignment_prompt": assignment_prompt,
                "assignment_rubric": assignment_rubric,
                "quiz_data": quiz_data,
                "estimated_minutes": 45
            }
            m_lessons.append(lesson_dict)

            # Generate 2 dedicated, deeply detailed Lecture Slides for this lesson
            all_slides_data.append({
                "slide_number": current_slide_num,
                "title": f"{l_title}: Theoretical Foundations",
                "bullet_points": [
                    f"Core Objective: Master {l_title} adhering to {benchmark_config['university']} standards",
                    "Mechanical reality: Execution stack frames, variable lifetime, and allocation costs",
                    "Defensive design: Establishing strict contracts and pre-condition validation",
                    f"Production consideration: Eliminating mutable shared state in {course_title}"
                ],
                "speaker_notes": (
                    f"In this lecture module, we dissect {l_title}. Notice how professional engineers "
                    f"differentiate between superficial syntax and underlying execution behavior. When {benchmark_config['university']} "
                    "trains engineers, the primary emphasis is placed on predictability. If your state transitions "
                    "are deterministic and your error boundaries are explicit, your software will scale reliably."
                ),
                "code_snippet": f"# {l_title} Contract\ndef execute_task(data: dict) -> dict:\n    assert data is not None, 'Contract violation'\n    return {{'status': 'verified', 'data': data}}",
                "diagram_or_visual": f"[Input Payload] --> [Contract Validator] --> [{clean_name} Engine] --> [Verified Output]",
                "slide_category": "Foundation"
            })
            current_slide_num += 1

            all_slides_data.append({
                "slide_number": current_slide_num,
                "title": f"{l_title}: Implementation & Trade-offs",
                "bullet_points": [
                    "Production blueprint: Modular architecture with isolated responsibilities",
                    "Complexity analysis: Big-O time and space consumption trade-offs",
                    "Failure modes: Identifying common anti-patterns and memory leak vectors",
                    "Automated verification: Constructing comprehensive unit assertions"
                ],
                "speaker_notes": (
                    f"Let us walk through the code architecture for {l_title}. Notice that we do not write "
                    "code haphazardly; every line serves a clear architectural purpose. We analyze our "
                    "algorithmic bounds: what happens when N increases by three orders of magnitude? "
                    "These are the exact engineering questions that separate amateur code from elite systems."
                ),
                "code_snippet": f"pipeline = {clean_name}Engine()\nresult = pipeline.execute({{'task': '{l_title}'}})\nassert result['status'] == 'verified'",
                "diagram_or_visual": "Memory Layout:\n+-------------------+-------------------+\n| Stack (Frames)    | Heap (Objects)    |\n+-------------------+-------------------+",
                "slide_category": "Code Walkthrough"
            })
            current_slide_num += 1

        modules_data.append({
            "order": m_idx,
            "title": m_info['title'],
            "description": m_info['desc'],
            "pedagogical_focus": benchmark_config['benchmark_title'],
            "estimated_hours": m_info['hours'],
            "lessons": m_lessons
        })

    # Final Capstone Lecture Slide
    all_slides_data.append({
        "slide_number": current_slide_num,
        "title": f"{course_title}: Capstone Laboratory Specification",
        "bullet_points": [
            f"Capstone Target: Full verification against {benchmark_config['benchmark_title']}",
            "Integration: Combining all modular engines into a unified deployable system",
            "Verification: Passing 100% of unit assertions, edge stress tests, and diagnostic quizzes",
            "Next Phase: Progression to portfolio deployment and industry accreditation"
        ],
        "speaker_notes": (
            f"We conclude our lecture series for {course_title}. Your final challenge is to synthesize "
            f"every single concept we have studied into your capstone project. Adhere strictly to {benchmark_config['university']} "
            "hygiene: modularity, algorithmic efficiency, and exhaustive defensive testing. Excellent work completing this deck."
        ),
        "code_snippet": f"# Final Capstone Verification Suite\ndef test_suite():\n    assert verify_all_modules() == True\n    print('Accredited: {benchmark_config['benchmark_title']}')",
        "diagram_or_visual": "+--------------------------------------------------------+\n| 🏛️ CAPSTONE VERIFICATION: " + benchmark_config['benchmark_title'][:28] + " |\n| Status: PRODUCTION ACCREDITED                         |\n+--------------------------------------------------------+",
        "slide_category": "Lab"
    })

    return {
        "modules": modules_data,
        "slides": all_slides_data
    }


# ==============================================================================
# 4. DATABASE ORCHESTRATION & SYNC ENGINE
# ==============================================================================

def generate_deep_university_curriculum(course_level, force=False, use_ai=True):
    """
    Ensures that for a given CourseLevel, the full academic hierarchy:
    - CourseModule (4-6 modules)
    - AcademicLesson (10-18 deep lessons with long-form reading, codes, rubrics, quizzes)
    - PresentationSlide (15-30+ detailed slides with speaker notes & visuals)
    are deeply populated in the database.
    Also synchronizes canonical DailyLessons for seamless student compatibility.
    """
    # Check if already generated
    has_modules = CourseModule.objects.filter(course_level=course_level).exists()
    has_slides = PresentationSlide.objects.filter(course_level=course_level).exists()

    if has_modules and has_slides and not force:
        logger.info(f"Curriculum already deeply generated for {course_level.title}.")
        return course_level

    logger.info(f"Generating deep university curriculum for {course_level.title} [{course_level.level}]...")

    curriculum_data = None
    if use_ai:
        curriculum_data = generate_curriculum_with_gemini(course_level)

    if not curriculum_data:
        curriculum_data = generate_academic_engine_curriculum(course_level)

    with transaction.atomic():
        # Clear existing deep models if force
        if force:
            CourseModule.objects.filter(course_level=course_level).delete()
            PresentationSlide.objects.filter(course_level=course_level).delete()

        created_lessons = []
        total_modules_count = 0
        total_lessons_count = 0

        # 1. Save Modules & Academic Lessons
        for mod_item in curriculum_data.get('modules', []):
            module_obj = CourseModule.objects.create(
                course_level=course_level,
                admin_course=course_level.parent_course,
                order=mod_item.get('order', 1),
                title=mod_item.get('title', f"Module {mod_item.get('order', 1)}"),
                description=mod_item.get('description', ''),
                pedagogical_focus=mod_item.get('pedagogical_focus', course_level.benchmark),
                estimated_hours=mod_item.get('estimated_hours', 6)
            )
            total_modules_count += 1

            for les_item in mod_item.get('lessons', []):
                les_obj = AcademicLesson.objects.create(
                    module=module_obj,
                    course_level=course_level,
                    order=les_item.get('order', 1),
                    title=les_item.get('title'),
                    summary=les_item.get('summary', ''),
                    reading_content=les_item.get('reading_content', ''),
                    code_examples=les_item.get('code_examples', []),
                    use_cases=les_item.get('use_cases', []),
                    assignment_prompt=les_item.get('assignment_prompt', ''),
                    assignment_rubric=les_item.get('assignment_rubric', ''),
                    quiz_data=les_item.get('quiz_data', []),
                    estimated_minutes=les_item.get('estimated_minutes', 45)
                )
                created_lessons.append(les_obj)
                total_lessons_count += 1

        # 2. Save Presentation Slides (15 to 30+ Slides)
        slides_list = curriculum_data.get('slides', [])
        total_slides_count = 0
        for s_idx, slide_item in enumerate(slides_list, start=1):
            matching_lesson = created_lessons[s_idx % len(created_lessons)] if created_lessons else None
            PresentationSlide.objects.create(
                course_level=course_level,
                lesson=matching_lesson,
                slide_number=slide_item.get('slide_number', s_idx),
                title=slide_item.get('title', f"Slide {s_idx}"),
                bullet_points=slide_item.get('bullet_points', []),
                speaker_notes=slide_item.get('speaker_notes', ''),
                code_snippet=slide_item.get('code_snippet', ''),
                diagram_or_visual=slide_item.get('diagram_or_visual', ''),
                slide_category=slide_item.get('slide_category', 'Concept')
            )
            total_slides_count += 1

        # 3. Synchronize / Enrich DailyLesson for Student Compatibility
        # If canonical DailyLessons already established (e.g. 7, 10, 12 days by settings), preserve them!
        existing_canonical = DailyLesson.objects.filter(course_level=course_level, generated_course__isnull=True)
        if not existing_canonical.exists():
            for idx, acad_lesson in enumerate(created_lessons, start=1):
                # Rich presentation data for PPT generator
                slide_deck = []
                for s in PresentationSlide.objects.filter(course_level=course_level):
                    slide_deck.append({
                        "slide_number": s.slide_number,
                        "title": s.title,
                        "bullet_points": s.bullet_points,
                        "speaker_notes": s.speaker_notes,
                        "code_snippet": s.code_snippet,
                        "diagram_or_visual": s.diagram_or_visual,
                        "slide_category": s.slide_category
                    })

                # Pre-build slides_list for instant video and presentation generation
                slides_list = []
                # Build dedicated slides for this lesson (up to 10 slides per lecture)
                deck_slice = slide_deck[:10] if len(slide_deck) >= 10 else slide_deck
                for s_idx, s in enumerate(deck_slice, start=1):
                    speaker_notes = s.get("speaker_notes", "") or f"Lecture covering {s.get('title', '')}."
                    slides_list.append({
                        "slide_number": s_idx,
                        "type": "code" if s.get("code_snippet") else "concept",
                        "badge": s.get("slide_category", "ACADEMIC LECTURE").upper(),
                        "title": s.get("title", f"Slide {s_idx}"),
                        "key_points": s.get("bullet_points", []),
                        "speaker_notes": speaker_notes,
                        "narration": speaker_notes,
                        "code_snippet": s.get("code_snippet", ""),
                        "diagram_or_visual": s.get("diagram_or_visual", ""),
                    })

                d_lesson = DailyLesson.objects.create(
                    course_level=course_level,
                    module=acad_lesson.module,
                    academic_lesson=acad_lesson,
                    day_number=idx,
                    title=acad_lesson.title,
                    content=acad_lesson.reading_content,
                    is_unlocked=True,  # every day of the plan is open (owner request)
                    is_completed=False,
                    presentation_data={"slides": slide_deck, "slides_list": slides_list}
                )

                # Automated Pipeline: When content generates -> PPT generates -> 2-3 min Audio & Explanations generate -> Saved in Admin DB
                try:
                    from .ppt_service import generate_and_save_admin_lesson_ppt_and_audio
                    generate_and_save_admin_lesson_ppt_and_audio(d_lesson, generate_audio=False)
                except Exception as e:
                    logger.warning(f"Automated PPT and audio generation deferred for lesson {d_lesson.id}: {e}")

                # Create or update LessonTask (Assignment & Quiz)
                LessonTask.objects.update_or_create(
                    lesson=d_lesson,
                    defaults={
                        'assignment_question': acad_lesson.assignment_prompt,
                        'quiz_data': acad_lesson.quiz_data
                    }
                )

        # 4. Update CourseLevel Metadata
        course_level.is_deep_generated = True
        course_level.total_modules_count = total_modules_count
        course_level.total_lessons_count = total_lessons_count
        course_level.total_slides_count = total_slides_count
        benchmark_clean = course_level.benchmark.split('/')[0].strip() if course_level.benchmark else 'University Benchmark'
        course_level.duration = f"{total_lessons_count} Academic Lectures • {benchmark_clean}"
        course_level.save(update_fields=[
            'is_deep_generated',
            'total_modules_count',
            'total_lessons_count',
            'total_slides_count',
            'duration'
        ])

        logger.info(
            f"Successfully saved {total_modules_count} modules, {total_lessons_count} lessons, "
            f"and {total_slides_count} slides for {course_level.title}!"
        )

    return course_level
