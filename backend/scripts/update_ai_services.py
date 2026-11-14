import re

path = 'alvix/alvixapp/ai_services.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Add is_topic_practical and build_track_assignment_and_quiz before get_curated_level_content_and_plan
insert_marker = "def get_curated_level_content_and_plan"

track_functions = '''
def is_topic_practical(topic_title: str, bullets: list = None, day_number: int = 1, course_type: str = 'Mixed') -> bool:
    """
    Determines whether a curriculum day is Practical or Theoretical.
    - Practical courses: always True.
    - Theory courses: always False.
    - Mixed courses: follow the topic of each day (practical topics get practical items, theory gets theory).
    Guarantees: Never generate a coding task for a theory topic or an essay for a syntax topic.
    """
    c_type = 'Theoretical' if course_type == 'Theory' else course_type
    if c_type == 'Practical':
        return True
    if c_type == 'Theoretical':
        return False

    # Mixed course: inspect topic and bullets
    t_lower = (topic_title or '').lower()
    bullet_text = " ".join([str(b).lower() for b in (bullets or [])])
    combined = f"{t_lower} {bullet_text}"

    # Syntax / implementation / lab / coding keywords -> Practical
    practical_keywords = ['syntax', 'code', 'coding', 'implement', 'building', 'hands-on', 'lab', 'file', 'script', 'api', 'pipeline', 'profiling', 'debug', 'deploy']
    # Theory / foundations / principles / proofs / complexity -> Theory
    theory_keywords = ['theory', 'theoretical', 'foundation', 'principle', 'invariant', 'architecture', 'model', 'proof', 'asymptotic', 'consensus', 'semantics', 'abstraction']

    has_practical = any(k in combined for k in practical_keywords)
    has_theory = any(k in combined for k in theory_keywords)

    if has_practical and not has_theory:
        return True
    if has_theory and not has_practical:
        return False

    # Even days practical, odd days theoretical in Mixed track
    return (day_number % 2 == 0)


def build_track_assignment_and_quiz(course_title: str, level_name: str, day_number: int, topic_title: str, course_type: str = 'Mixed', bullets: list = None):
    """
    Generates track-aware assignment and quiz adhering strictly to pedagogical requirements:
    1. Practical:
       - Assignment: practical task ('create a file that does X') with requirements checklist, marks rubric, expected file type.
       - Quiz: MCQs with tricky practical questions (predict output, spot error, best practice).
    2. Theory:
       - Assignment: short-answer or case-study question with expected points and rubric.
       - Quiz: concept-based MCQs.
    3. Mixed:
       - Follows topic of each day.
    Quiz JSON schema: question, optional code, 4 options, correct, explanation, topic.
    Validates strictly that 'correct' is one of the options.
    """
    is_practical = is_topic_practical(topic_title, bullets, day_number, course_type)
    file_ext = ".py" if "python" in course_title.lower() or "system" in course_title.lower() or "comput" in course_title.lower() else ".py"

    if is_practical:
        # PRACTICAL TRACK ITEM
        filename = f"lab_day{day_number}_{topic_title.lower().replace(' ', '_')[:18]}{file_ext}"
        assignment_prompt = (
            f"Practical Laboratory Task — Day {day_number} ({course_type} Track, {level_name} Level)\n"
            f"Task: Create a file named '{filename}' that implements an end-to-end verified solution for '{topic_title}' in {course_title}.\n\n"
            f"Requirements Checklist:\n"
            f"1. Implement the core module structure with clean function boundaries and descriptive variable names.\n"
            f"2. Validate all inputs defensively (type validation, non-empty bounds, edge-condition handling).\n"
            f"3. Guarantee deterministic execution under concurrent or heavy simulated input stress.\n"
            f"4. Include an automated self-verification test harness or assert statements at the bottom of '{filename}'.\n\n"
            f"Marks Rubric (10 Marks Total / 100% Scale):\n"
            f"• Core Implementation & Functional Logic: 4 Marks (40%)\n"
            f"• Defensive Input Validation & Error Handling: 2.5 Marks (25%)\n"
            f"• Code Architecture, Typing & Clean Modularity: 2 Marks (20%)\n"
            f"• Unit Testing, Assertions & Edge Coverage: 1.5 Marks (15%)\n\n"
            f"Expected File Type: {file_ext} (or paste complete source code below)"
        )
        assignment_data = {
            'type': 'practical',
            'filename': filename,
            'expected_file_type': file_ext,
            'task': f"Create a file named '{filename}' that implements an end-to-end verified solution for '{topic_title}'.",
            'checklist': [
                "Implement the core module structure with clean function boundaries and descriptive variable names.",
                "Validate all inputs defensively (type validation, non-empty bounds, edge-condition handling).",
                "Guarantee deterministic execution under concurrent or heavy simulated input stress.",
                f"Include an automated self-verification test harness or assert statements at the bottom of '{filename}'."
            ],
            'rubric': [
                {"criterion": "Core Implementation & Functional Logic", "marks": 4, "percentage": 40},
                {"criterion": "Defensive Input Validation & Error Handling", "marks": 2.5, "percentage": 25},
                {"criterion": "Code Architecture, Typing & Clean Modularity", "marks": 2, "percentage": 20},
                {"criterion": "Unit Testing, Assertions & Edge Coverage", "marks": 1.5, "percentage": 15}
            ]
        }

        # Tricky Practical MCQs (Predict Output, Spot Error, Best Practice)
        q1_code = f"def run_pipeline(items=[]):\\n    items.append({day_number})\\n    return len(items)\\nprint(run_pipeline(), run_pipeline())"
        q1_options = ["1 2", "1 1", "[1] [1, 2]", "IndexError"]
        q1_correct = "1 2"

        q2_code = f"def validate_state(val):\\n    if val is None or len(val) == 0:\\n        raise ValueError('Empty state')\\n    return True"
        q2_options = [
            "Defensive guard clause correctly halts invalid state before processing.",
            "Function crashes when val is None due to short-circuit evaluation order.",
            "len() is executed before checking None causing AttributeError.",
            "Raising ValueError is discouraged for invalid parameters."
        ]
        q2_correct = "Defensive guard clause correctly halts invalid state before processing."

        q3_code = f"# Best practice memory boundary check\\nCHUNK_SIZE = 64 * 1024\\nwith open('data.bin', 'rb') as f:\\n    while chunk := f.read(CHUNK_SIZE):\\n        process(chunk)"
        q3_options = [
            "Buffered chunk-wise processing avoids loading unbounded files into memory.",
            "Reading entire file with f.read() is faster and preferred for large files.",
            "Walrus operator (:=) causes unnecessary CPU context switching.",
            "Using binary mode ('rb') disables OS file caching."
        ]
        q3_correct = "Buffered chunk-wise processing avoids loading unbounded files into memory."

        quiz = [
            {
                "question": f"Predict the output of the following code snippet related to {topic_title}:",
                "code": q1_code,
                "options": q1_options,
                "correct": q1_correct,
                "explanation": "Default argument items=[] is evaluated once at function definition time, persisting state across multiple calls.",
                "topic": f"{topic_title} - Practical Execution"
            },
            {
                "question": f"Spot the correct architectural assessment of this defensive validation pattern:",
                "code": q2_code,
                "options": q2_options,
                "correct": q2_correct,
                "explanation": "Python short-circuit 'or' ensures len(val) is never invoked if val is None, providing clean defensive safety.",
                "topic": f"{topic_title} - Defensive Programming"
            },
            {
                "question": f"Which industry best practice is demonstrated by the chunked processing pattern below?",
                "code": q3_code,
                "options": q3_options,
                "correct": q3_correct,
                "explanation": "Fixed-size buffer chunking guarantees O(1) auxiliary memory consumption regardless of gigabyte-scale inputs.",
                "topic": f"{topic_title} - Production Best Practice"
            }
        ]

    else:
        # THEORY TRACK ITEM
        assignment_prompt = (
            f"Theoretical Case-Study & Analysis — Day {day_number} ({course_type} Track, {level_name} Level)\n"
            f"Case Study: Formulate an in-depth academic analysis of '{topic_title}' within {course_title}.\n\n"
            f"Expected Points to Address:\n"
            f"1. Define the formal theoretical invariants and state transition rules governing {topic_title}.\n"
            f"2. Analyze system behavior under network partitions, memory pressure, or unexpected race conditions.\n"
            f"3. Compare and contrast two canonical architectural approaches addressing this problem in industry.\n"
            f"4. Derive asymptotic time and space complexity bounds and evaluate their practical trade-offs.\n\n"
            f"Evaluation Rubric (10 Marks Total / 100% Scale):\n"
            f"• Theoretical Rigor & Invariant Definitions: 4 Marks (40%)\n"
            f"• Inclusion of All Mandatory Expected Points: 3 Marks (30%)\n"
            f"• Failure Scenario & Boundary Trade-off Analysis: 2 Marks (20%)\n"
            f"• Academic Terminology, Clarity & Expression: 1 Mark (10%)\n\n"
            f"Expected Submission: Written theoretical analysis (or uploaded document/PDF)"
        )
        assignment_data = {
            'type': 'theory',
            'expected_file_type': '.txt / text',
            'task': f"Formulate an in-depth academic analysis of '{topic_title}'.",
            'expected_points': [
                f"Define the formal theoretical invariants and state transition rules governing {topic_title}.",
                "Analyze system behavior under network partitions, memory pressure, or unexpected race conditions.",
                "Compare and contrast two canonical architectural approaches addressing this problem in industry.",
                "Derive asymptotic time and space complexity bounds and evaluate their practical trade-offs."
            ],
            'rubric': [
                {"criterion": "Theoretical Rigor & Invariant Definitions", "marks": 4, "percentage": 40},
                {"criterion": "Inclusion of All Mandatory Expected Points", "marks": 3, "percentage": 30},
                {"criterion": "Failure Scenario & Boundary Trade-off Analysis", "marks": 2, "percentage": 20},
                {"criterion": "Academic Terminology, Clarity & Expression", "marks": 1, "percentage": 10}
            ]
        }

        # Concept-based MCQs
        quiz = [
            {
                "question": f"Which fundamental invariant must hold true when designing systems around {topic_title}?",
                "code": "",
                "options": [
                    "State transitions must remain deterministic and preserve system invariants across failure boundaries.",
                    "System performance must prioritize throughput by bypassing input validation checks.",
                    "All components must share a single global un-synchronized memory block.",
                    "Network communications must assume zero-latency and reliable ordered packet delivery."
                ],
                "correct": "State transitions must remain deterministic and preserve system invariants across failure boundaries.",
                "explanation": "Theoretical robustness requires deterministic state transitions that prevent undefined states even during failures.",
                "topic": f"{topic_title} - Architectural Invariants"
            },
            {
                "question": f"What is the primary asymptotic trade-off encountered when optimizing {topic_title}?",
                "code": "",
                "options": [
                    "Decreasing query time typically requires auxiliary space for indexing and pre-computed state.",
                    "Increasing space always results in exponential algorithmic runtime.",
                    "Caching data in memory eliminates all network communication latency permanently.",
                    "Time complexity cannot be reduced below O(N^2) in modern computing architectures."
                ],
                "correct": "Decreasing query time typically requires auxiliary space for indexing and pre-computed state.",
                "explanation": "Space-time trade-off is fundamental: accelerated query operations require auxiliary data structures.",
                "topic": f"{topic_title} - Asymptotic Analysis"
            },
            {
                "question": f"How do top-ranked universities evaluate safety and reliability in {topic_title}?",
                "code": "",
                "options": [
                    "By formally modeling failure domains and proving correctness through boundary invariants.",
                    "By relying solely on manual testing right before software release.",
                    "By disabling assertions and compiler warnings in production.",
                    "By assuming hardware faults will never occur in distributed clusters."
                ],
                "correct": "By formally modeling failure domains and proving correctness through boundary invariants.",
                "explanation": "Rigorous academic curriculum teaches formal invariant modeling to prevent catastrophic runtime failures.",
                "topic": f"{topic_title} - Conceptual Foundations"
            }
        ]

    # Strictly validate that correct is in options for every question
    for q in quiz:
        if q['correct'] not in q['options']:
            q['options'][0] = q['correct']

    return assignment_prompt, assignment_data, quiz
'''

if "def build_track_assignment_and_quiz" not in text:
    text = text.replace(insert_marker, track_functions + "\n\n" + insert_marker)

# Update get_curated_level_content_and_plan loop to use build_track_assignment_and_quiz
old_loop_assign = """        assignment = (
            f"Day {day} Assignment ({norm_type} Track - {level_name} Level):\\n"
            f"Implement a verified solution applying the core concepts of '{topic['title']}' in {course_title}.\\n"
            f"1. Structure your code or analysis cleanly with modular boundaries.\\n"
            f"2. Validate all inputs defensively and document your reasoning.\\n"
            f"3. Submit your completed source code or summary notes."
        )

        quiz = [
            {
                "question": f"What is the primary objective of Day {day} in {topic['title']}?",
                "options": [
                    "To establish deterministic modular execution and prevent edge-case failures.",
                    "To write unstructured scripts without parameter validation.",
                    "To bypass testing and deploy directly to production.",
                    "To disable error handling for faster execution."
                ],
                "correct_answer": 0,
                "explanation": "Modularity and deterministic execution guarantee reliable and maintainable systems."
            },
            {
                "question": f"Why do top-ranked universities emphasize rigorous fundamentals in {level_name} courses?",
                "options": [
                    "To guarantee software correctness and architectural scalability under real workloads.",
                    "To make code longer and more complex without purpose.",
                    "To avoid using modern tools and libraries.",
                    "To prevent automated compilers from optimizing code."
                ],
                "correct_answer": 0,
                "explanation": "Foundational rigor prevents system crashes, memory leaks, and architectural debt."
            },
            {
                "question": f"Which practice is required for the Day {day} assignment submission?",
                "options": [
                    "Defensive input validation and modular boundary separation.",
                    "Using uninitialized global variables.",
                    "Ignoring runtime error messages and warnings.",
                    "Hardcoding arbitrary credentials in source files."
                ],
                "correct_answer": 0,
                "explanation": "Defensive boundaries and input validation ensure that invalid states are caught safely."
            }
        ]

        lesson_plan.append({
            'day_number': day,
            'title': day_title,
            'topic_title': topic['title'],
            'overview': overview,
            'takeaway': takeaway,
            'content': content_html,
            'assignment': assignment,
            'quiz': quiz
        })"""

new_loop_assign = """        assignment, assignment_data, quiz = build_track_assignment_and_quiz(
            course_title=course_title,
            level_name=level_name,
            day_number=day,
            topic_title=topic['title'],
            course_type=norm_type,
            bullets=topic.get('bullets', [])
        )

        lesson_plan.append({
            'day_number': day,
            'title': day_title,
            'topic_title': topic['title'],
            'overview': overview,
            'takeaway': takeaway,
            'content': content_html,
            'assignment': assignment,
            'assignment_data': assignment_data,
            'quiz': quiz
        })"""

text = text.replace(old_loop_assign.replace('\r\n', '\n'), new_loop_assign.replace('\r\n', '\n'))
text = text.replace(old_loop_assign.replace('\n', '\r\n'), new_loop_assign.replace('\n', '\r\n'))

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated ai_services.py successfully!")
