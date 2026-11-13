with open('d:/ALIF/alvix/alvixapp/templates/student_dashboard/course_data/daily_lesson.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
overlays = re.findall(r'<div[^>]*id="(?:inaraIntroStage|playOverlay|completionOverlay)[^"]*"[^>]*>', text)
for o in overlays:
    print(o)

styles = re.findall(r'#(?:inaraIntroStage|playOverlay|completionOverlay)\s*\{[^}]*\}', text)
for s in styles:
    print(s)
