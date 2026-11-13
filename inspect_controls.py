import re

with open('d:/ALIF/alvix/alvixapp/templates/student_dashboard/course_data/daily_lesson.html', 'r', encoding='utf-8') as f:
    text = f.read()

buttons = re.findall(r'<button[^>]*>|<div[^>]*id="[^"]*"[^>]*>', text)
print("Found elements:")
for b in buttons:
    if any(k in b for k in ['btn', 'Btn', 'Slide', 'slide', 'play', 'Play', 'bar', 'Progress', 'progress', 'dot', 'Dot', 'time', 'Time', 'video', 'Video']):
        print(b.strip())
