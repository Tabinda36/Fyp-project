import re

for tpath in [r'd:\ALIF\alvix\alvixapp\templates\student_dashboard\course_data\generate_course.html', r'd:\ALIF\alvix\alvixapp\templates\student_dashboard\course_data\daily_lesson.html']:
    with open(tpath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    vars_found = set(re.findall(r'\{\{\s*([a-zA-Z0-9_]+)', content))
    loops_found = set(re.findall(r'\{%\s*for\s+\w+\s+in\s+([a-zA-Z0-9_]+)', content))
    ifs_found = set(re.findall(r'\{%\s*if\s+([a-zA-Z0-9_]+)', content))
    print(f"=== {tpath} ===")
    print(f"  Loops: {loops_found}")
    print(f"  Vars: {vars_found}")
    print(f"  Ifs: {ifs_found}")
