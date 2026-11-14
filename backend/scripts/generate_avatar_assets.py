"""
Generates the 4 PNG frames of Inara, the ALVIX AI lecturer, with transparent backgrounds.

Look (owner request, 2026-11-14): a modern professional lecturer — navy blazer with gold
ALVIX lapel pin over a cream blouse, a soft taupe hijab, a tablet in one hand and a slim
pointer in the other. The canvas (512x512), face position and the four frame names are
unchanged, so the lesson player's layout and animations work as before.

Frames: inara_idle.png, inara_blink.png, inara_mouth_open.png, inara_wave.png
Output: backend/public/assets/avatar/   (run from anywhere:  python scripts/generate_avatar_assets.py)
"""
import os

from PIL import Image, ImageDraw, ImageFilter

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BACKEND_DIR, 'public', 'assets', 'avatar')

SIZE = 512
SS = 3  # supersampling factor: draw at 3x, downscale with LANCZOS for smooth edges

# Palette
NAVY = (27, 38, 64, 255)            # blazer
NAVY_DARK = (17, 25, 45, 255)       # blazer shadows / lapel edges
NAVY_LIGHT = (44, 58, 92, 255)      # lapel highlight
BLOUSE = (247, 242, 232, 255)
BLOUSE_SHADOW = (226, 217, 200, 255)
HIJAB = (176, 150, 132, 255)        # soft taupe
HIJAB_DARK = (146, 120, 104, 255)
HIJAB_LIGHT = (199, 176, 158, 255)
UNDERCAP = (238, 228, 214, 255)
GOLD = (212, 175, 55, 255)
GOLD_DARK = (168, 134, 30, 255)
SKIN = (246, 214, 188, 255)
SKIN_SHADOW = (229, 188, 160, 255)
BLUSH = (235, 120, 120, 60)
BROW = (62, 42, 32, 255)
EYE = (44, 30, 22, 255)
IRIS = (92, 60, 40, 255)
WHITE = (255, 255, 255, 255)
LIP = (196, 96, 98, 255)
MOUTH_IN = (122, 40, 48, 255)
TABLET = (36, 40, 48, 255)
TABLET_SCREEN = (16, 110, 83, 255)  # ALVIX emerald
EMERALD_LIGHT = (52, 168, 120, 255)


def S(*coords):
    """Scale 512-space coordinates to the supersampled canvas."""
    if len(coords) == 1 and isinstance(coords[0], (list, tuple)):
        coords = coords[0]
    out = []
    for c in coords:
        if isinstance(c, (list, tuple)):
            out.append(tuple(v * SS for v in c))
        else:
            out.append(c * SS)
    return out


def w(px):
    return max(1, int(px * SS))


# ---------------------------------------------------------------------------
# Body
# ---------------------------------------------------------------------------
def draw_body(d):
    # Hijab drape behind the shoulders
    d.polygon(S([(150, 512), (168, 352), (214, 318), (298, 318), (344, 352), (362, 512)]), fill=HIJAB_DARK)

    # Blazer torso
    d.polygon(S([(108, 512), (128, 410), (170, 368), (226, 352), (286, 352), (342, 368), (384, 410), (404, 512)]), fill=NAVY)
    # Shoulder shading
    d.polygon(S([(108, 512), (128, 410), (170, 368), (150, 512)]), fill=NAVY_DARK)
    d.polygon(S([(404, 512), (384, 410), (342, 368), (362, 512)]), fill=NAVY_DARK)

    # Blouse V
    d.polygon(S([(222, 356), (290, 356), (256, 470)]), fill=BLOUSE)
    d.line(S([(256, 380), (256, 470)]), fill=BLOUSE_SHADOW, width=w(2))
    for y in (400, 428, 456):
        d.ellipse(S([253, y, 259, y + 6]), fill=BLOUSE_SHADOW)

    # Lapels (notched)
    d.polygon(S([(222, 356), (200, 372), (214, 404), (204, 416), (256, 482), (240, 420)]), fill=NAVY_LIGHT)
    d.polygon(S([(290, 356), (312, 372), (298, 404), (308, 416), (256, 482), (272, 420)]), fill=NAVY_LIGHT)
    d.line(S([(222, 356), (240, 420), (256, 482)]), fill=NAVY_DARK, width=w(2))
    d.line(S([(290, 356), (272, 420), (256, 482)]), fill=NAVY_DARK, width=w(2))

    # Gold ALVIX lapel pin
    d.ellipse(S([290, 392, 306, 408]), fill=GOLD, outline=GOLD_DARK, width=w(1.5))
    d.polygon(S([(298, 395), (302, 404), (294, 404)]), fill=GOLD_DARK)

    # Blazer button
    d.ellipse(S([251, 488, 261, 498]), fill=GOLD_DARK)


def draw_hijab_and_face(d):
    # Hijab hood around the head
    d.ellipse(S([152, 96, 360, 352]), fill=HIJAB_DARK)
    d.ellipse(S([158, 100, 354, 344]), fill=HIJAB)
    # Soft highlight on the crown
    d.chord(S([176, 104, 336, 230]), start=200, end=340, fill=HIJAB_LIGHT)

    # Under-cap band on the forehead
    d.chord(S([194, 134, 318, 226]), start=190, end=350, fill=UNDERCAP)

    # Face
    d.ellipse(S([194, 158, 318, 312]), fill=SKIN)
    d.arc(S([194, 158, 318, 312]), start=35, end=145, fill=SKIN_SHADOW, width=w(3))

    # Hijab wrap under the chin and across the neck
    d.polygon(S([(184, 300), (214, 330), (256, 344), (298, 330), (328, 300), (338, 352), (256, 380), (174, 352)]), fill=HIJAB)
    d.arc(S([196, 290, 316, 372]), start=20, end=160, fill=HIJAB_DARK, width=w(3))

    # Eyebrows (thin, gently arched)
    d.arc(S([212, 194, 246, 214]), start=205, end=335, fill=BROW, width=w(3))
    d.arc(S([266, 194, 300, 214]), start=205, end=335, fill=BROW, width=w(3))

    # Nose
    d.line(S([(257, 236), (259, 254), (252, 257)]), fill=SKIN_SHADOW, width=w(2.5))


def draw_blush(size):
    layer = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(layer)
    bd.ellipse(S([204, 248, 232, 266]), fill=BLUSH)
    bd.ellipse(S([280, 248, 308, 266]), fill=BLUSH)
    return layer.filter(ImageFilter.GaussianBlur(3 * SS))


def draw_eyes(d, blinking):
    if blinking:
        for x in (214, 268):
            d.arc(S([x, 218, x + 30, 236]), start=20, end=160, fill=EYE, width=w(3))
            d.line(S([(x + 28, 228), (x + 33, 224)]), fill=EYE, width=w(2))
        return
    for x in (214, 268):
        d.ellipse(S([x, 214, x + 30, 236]), fill=WHITE)
        d.ellipse(S([x + 7, 214, x + 25, 236]), fill=IRIS)
        d.ellipse(S([x + 10, 218, x + 22, 232]), fill=EYE)
        d.ellipse(S([x + 15, 218, x + 20, 223]), fill=WHITE)
        d.ellipse(S([x + 10, 228, x + 13, 231]), fill=(255, 255, 255, 190))
        # Upper lid line + outer lash flick
        d.arc(S([x - 2, 210, x + 32, 234]), start=190, end=350, fill=EYE, width=w(3))
        d.line(S([(x + 30, 216), (x + 35, 212)]), fill=EYE, width=w(2))


def draw_mouth(d, state):
    if state == 'closed':
        d.arc(S([240, 268, 272, 286]), start=20, end=160, fill=LIP, width=w(3))
    elif state == 'open':
        d.chord(S([238, 268, 274, 294]), start=0, end=180, fill=MOUTH_IN)
        d.chord(S([242, 269, 270, 278]), start=0, end=180, fill=WHITE)
        d.arc(S([238, 268, 274, 294]), start=0, end=180, fill=LIP, width=w(2.5))
    else:  # smiling, for the wave
        d.chord(S([236, 266, 276, 290]), start=10, end=170, fill=MOUTH_IN)
        d.chord(S([239, 267, 273, 276]), start=0, end=180, fill=WHITE)
        d.arc(S([235, 265, 277, 292]), start=10, end=170, fill=LIP, width=w(2.5))


def draw_hands(d, waving):
    # Left side of the picture: tablet held against the chest
    d.rounded_rectangle(S([150, 404, 226, 500]), radius=8 * SS, fill=TABLET)
    d.rounded_rectangle(S([156, 410, 220, 494]), radius=5 * SS, fill=TABLET_SCREEN)
    # Tiny "slide" on the screen: title bar + bars
    d.rectangle(S([162, 418, 214, 426]), fill=GOLD)
    for i, h in enumerate((22, 34, 16, 28)):
        x = 166 + i * 12
        d.rectangle(S([x, 480 - h, x + 7, 480]), fill=EMERALD_LIGHT)
    # Hand gripping the tablet's edge
    d.ellipse(S([206, 440, 236, 472]), fill=SKIN)
    d.arc(S([206, 440, 236, 472]), start=90, end=270, fill=SKIN_SHADOW, width=w(2))

    if not waving:
        # Right side: hand low, holding a slim pointer angled outward
        d.line(S([(318, 462), (420, 380)]), fill=GOLD_DARK, width=w(5))
        d.ellipse(S([414, 374, 426, 386]), fill=GOLD)
        d.ellipse(S([300, 446, 332, 478]), fill=SKIN)
        d.arc(S([300, 446, 332, 478]), start=-90, end=90, fill=SKIN_SHADOW, width=w(2))
    else:
        # Right arm raised beside the head, waving
        d.polygon(S([(334, 372), (392, 286), (424, 304), (364, 400)]), fill=NAVY)
        d.polygon(S([(392, 286), (424, 304), (418, 314), (386, 296)]), fill=BLOUSE)  # blouse cuff
        d.ellipse(S([400, 238, 446, 286]), fill=SKIN)
        d.polygon(S([(404, 266), (384, 254), (392, 244), (410, 256)]), fill=SKIN)  # thumb
        for x, top in ((414, 208), (425, 202), (436, 207), (446, 218)):
            d.rounded_rectangle(S([x, top, x + 11, 254]), radius=5 * SS, fill=SKIN)
        d.arc(S([458, 196, 476, 222]), start=270, end=60, fill=GOLD, width=w(3))
        d.arc(S([466, 224, 484, 250]), start=270, end=60, fill=GOLD, width=w(3))


def generate_frame(filename, waving=False, blinking=False, mouth='closed'):
    big = SIZE * SS
    img = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_body(d)
    draw_hijab_and_face(d)
    img = Image.alpha_composite(img, draw_blush(big))
    d = ImageDraw.Draw(img)
    draw_eyes(d, blinking)
    draw_mouth(d, mouth)
    draw_hands(d, waving)

    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    path = os.path.join(OUTPUT_DIR, filename)
    img.save(path, 'PNG', optimize=True)
    print(f"Generated {path}")


if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    generate_frame('inara_idle.png')
    generate_frame('inara_blink.png', blinking=True)
    generate_frame('inara_mouth_open.png', mouth='open')
    generate_frame('inara_wave.png', waving=True, mouth='smile')
    print("All 4 Inara frames generated.")
