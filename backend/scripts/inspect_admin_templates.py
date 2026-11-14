import os
import re

tpl_dir = r'd:\ALIF\alvix\alvixapp\templates\admin_db'
for fname in os.listdir(tpl_dir):
    fpath = os.path.join(tpl_dir, fname)
    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    # Find all {{ var }} and {% for x in var %} and {% if var %}
    vars_found = set(re.findall(r'\{\{\s*([a-zA-Z0-9_]+)', content))
    loops_found = set(re.findall(r'\{%\s*for\s+\w+\s+in\s+([a-zA-Z0-9_]+)', content))
    ifs_found = set(re.findall(r'\{%\s*if\s+([a-zA-Z0-9_]+)', content))
    print(f"=== {fname} ===")
    print(f"  Loops: {loops_found}")
    print(f"  Vars: {vars_found}")
    print(f"  Ifs: {ifs_found}")
