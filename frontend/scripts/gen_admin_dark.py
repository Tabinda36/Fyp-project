"""Generate dark-theme overrides for pages from their hard-coded light colours.

Usage (from frontend/):
  python scripts/gen_admin_dark.py src                      # admin  -> src/layouts/AdminDarkOverrides.css
  python scripts/gen_admin_dark.py src student              # student/learning/lessons -> src/layouts/StudentDarkOverrides.css
Overrides apply only under body.adm-theme-dark (both shells set it in dark mode).
"""
import colorsys
import pathlib
import re
import sys

SRC = pathlib.Path(sys.argv[1])
TARGET = sys.argv[2] if len(sys.argv) > 2 else 'admin'
if TARGET == 'student':
    PAGE_DIRS = [SRC / 'pages' / d for d in ('student', 'learning', 'lessons')]
    OUT = SRC / 'layouts' / 'StudentDarkOverrides.css'
    SKIP_CSS = {'DashboardPage.css', 'ProfilePage.css', 'SettingsPage.css', 'NotificationsPage.css',
                'ReportsPage.css', 'PerformancePage.css', 'MyCoursePage.css'}  # redesigned: hand-written dark rules
    SKIP_JSX = {'DashboardPage.jsx', 'ProfilePage.jsx', 'SettingsPage.jsx', 'NotificationsPage.jsx',
                'ReportsPage.jsx', 'PerformancePage.jsx', 'MyCoursePage.jsx'}
else:
    PAGE_DIRS = [SRC / 'pages' / 'admin']
    OUT = SRC / 'layouts' / 'AdminDarkOverrides.css'
    SKIP_CSS = {'AdminDashboardPage.css', 'UserManagementPage.css'}  # hand-written dark rules
    SKIP_JSX = {'AdminDashboardPage.jsx', 'UserManagementPage.jsx', 'UserDetailPage.jsx'}

NAMED = {'white': (255, 255, 255), '#fff': (255, 255, 255)}
COLOR_RE = re.compile(r'#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|\bwhite\b')


def parse(c):
    c = c.strip().lower()
    if c in NAMED:
        return NAMED[c], 1.0
    if c.startswith('#'):
        h = c[1:]
        if len(h) in (3, 4):
            h = ''.join(ch * 2 for ch in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return (r, g, b), a
    nums = [float(x) for x in re.findall(r'[\d.]+', c)]
    a = nums[3] if len(nums) > 3 else 1.0
    return tuple(int(n) for n in nums[:3]), a


def lum(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def colors_in(value):
    out = []
    for m in COLOR_RE.findall(value):
        try:
            out.append(parse(m))
        except Exception:
            pass
    return out


def bg_override(value):
    cols = [c for c in colors_in(value) if c[1] > 0.5]
    if not cols or 'url(' in value:
        return None
    lums = [lum(rgb) for rgb, _ in cols]
    if min(lums) < 0.6:  # contains a mid/dark colour (brand gradient, badge) -> keep
        return None
    return '#10201c' if min(lums) > 0.93 else '#15302a'


def text_override(value):
    cols = colors_in(value)
    if len(cols) != 1:
        return None
    rgb, _ = cols[0]
    l = lum(rgb)
    if l >= 0.3:
        return None
    if l < 0.07:
        return '#e3f1ea'
    r, g, b = rgb
    h, s, _v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if s > 0.35 and 0.25 < h < 0.55:  # green / teal accents
        return '#8fdcb9'
    if s > 0.35 and (h < 0.05 or h > 0.92):  # reds
        return '#ff8a80'
    return '#b9cfc5'


def border_override(value):
    cols = colors_in(value)
    if cols and all(lum(rgb) > 0.6 for rgb, _ in cols):
        return '#24413a'
    return None


rules = []

# 1) Page stylesheets
for css_file in sorted(f for d in PAGE_DIRS for f in d.glob('*.css')):
    if css_file.name in SKIP_CSS:
        continue
    text = re.sub(r'/\*.*?\*/', '', css_file.read_text(encoding='utf-8'), flags=re.S)
    for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', text):
        sel = sel.strip()
        if not sel or sel.startswith('@') or re.fullmatch(r'(from|to|[\d.%,\s]+)', sel):
            continue
        if sel in ('body', 'html', '*') or sel.startswith('body') or sel.startswith(':root'):
            continue
        decls = {}
        for d in body.split(';'):
            if ':' not in d:
                continue
            prop, val = d.split(':', 1)
            prop, val = prop.strip().lower(), val.replace('!important', '').strip()
            if prop in ('background', 'background-color'):
                o = bg_override(val)
                if o:
                    decls['background'] = o
            elif prop == 'color':
                o = text_override(val)
                if o:
                    decls['color'] = o
            elif prop in ('border', 'border-color', 'border-top', 'border-bottom', 'border-left', 'border-right'):
                o = border_override(val)
                if o:
                    decls['border-color'] = o
        if decls:
            scoped = ',\n'.join(f'.adm-theme-dark .adm-main {s.strip()}' for s in sel.split(','))
            body_out = ''.join(f'  {k}: {v} !important;\n' for k, v in decls.items())
            rules.append(f'/* {css_file.name} */\n{scoped} {{\n{body_out}}}\n')

# 2) Inline styles in JSX (React serialises colours as rgb(r, g, b))
inline_bg, inline_text = {}, {}
for jsx in sorted(f for d in PAGE_DIRS for f in d.glob('*.jsx') if f.name not in SKIP_JSX):
    src = jsx.read_text(encoding='utf-8')
    for prop, val in re.findall(r"(backgroundColor|background|background-color)\s*:\s*['\"]?([^,;'\"}]+)", src):
        for rgb, a in colors_in(val):
            if a > 0.5 and lum(rgb) > 0.6:
                inline_bg[rgb] = '#10201c' if lum(rgb) > 0.93 else '#15302a'
    for val in re.findall(r"(?<![-\w])color\s*:\s*['\"]?(#[0-9a-fA-F]{3,6})", src):
        rgb, _ = parse(val)
        o = text_override(val)
        if o:
            inline_text[rgb] = o

for rgb, o in sorted(inline_bg.items()):
    r, g, b = rgb
    rules.append(
        f'.adm-theme-dark .adm-main [style*="background-color: rgb({r}, {g}, {b})"],\n'
        f'.adm-theme-dark .adm-main [style*="background: rgb({r}, {g}, {b})"] {{\n  background: {o} !important;\n}}\n'
    )
for rgb, o in sorted(inline_text.items()):
    r, g, b = rgb
    rules.append(f'.adm-theme-dark .adm-main [style*="color: rgb({r}, {g}, {b})"]:not([style*="background-color: rgb({r}, {g}, {b})"]) {{\n  color: {o} !important;\n}}\n')

header = ('/* GENERATED by gen_admin_dark.py: dark-theme overrides for hard-coded light colours\n'
          '   in admin page CSS and inline styles. Active only under body.adm-theme-dark. */\n\n')
OUT.write_text(header + '\n'.join(rules), encoding='utf-8')
print(f'{len(rules)} rules -> {OUT}')
