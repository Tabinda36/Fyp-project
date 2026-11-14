"""
Generates the 4 developer cartoon avatar PNG frames for Inara with transparent backgrounds.
Saved to public/assets/avatar/
"""
import os
import math
from PIL import Image, ImageDraw

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'public', 'assets', 'avatar')
os.makedirs(OUTPUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 512, 512

# Color Palette (Emerald & Gold ALVIX theme)
EMERALD_DARK = (6, 78, 59, 255)       # #064E3B
EMERALD_MID  = (16, 110, 83, 255)     # #106E53
EMERALD_LIGHT= (22, 140, 106, 255)    # #168C6A
GOLD_ACCENT  = (212, 175, 55, 255)     # #D4AF37
GOLD_LIGHT   = (254, 249, 231, 255)    # #FEF9E7
SKIN_BASE    = (253, 222, 192, 255)    # #FDDEC0
SKIN_SHADOW  = (240, 198, 164, 255)    # #F0C6A4
CHEEK_BLUSH  = (248, 113, 113, 70)     # Soft rose
EYE_COLOR    = (35, 22, 16, 255)       # Dark warm brown
EYE_WHITE    = (255, 255, 255, 255)
LIP_COLOR    = (205, 85, 85, 255)
BOOK_COVER   = (6, 78, 59, 255)
BOOK_PAGE    = (250, 248, 240, 255)
GOLD_BORDER  = (212, 175, 55, 255)

def draw_base_body_and_hijab(draw, frame_type):
    # 1. Torso / Abaya (Lower half)
    draw.polygon([
        (130, 512), (180, 360), (332, 360), (382, 512)
    ], fill=EMERALD_DARK)
    
    # Abaya Gold Center Placket
    draw.line([(256, 360), (256, 512)], fill=GOLD_ACCENT, width=4)
    # Small Gold Buttons
    for y in [395, 430, 465, 500]:
        draw.ellipse([252, y, 260, y + 8], fill=GOLD_ACCENT)

    # 2. Hijab Shoulder Drape (flowing over shoulders)
    draw.polygon([
        (120, 512), (160, 340), (210, 310), (302, 310), (352, 340), (392, 512)
    ], fill=EMERALD_MID)
    # Shoulder drape fold lines
    draw.arc([140, 330, 260, 480], start=30, end=110, fill=EMERALD_DARK, width=3)
    draw.arc([252, 330, 372, 480], start=70, end=150, fill=EMERALD_DARK, width=3)

    # 3. Hijab Hood Base (Behind head & around neck)
    draw.ellipse([140, 90, 372, 360], fill=EMERALD_DARK)
    draw.ellipse([148, 96, 364, 350], fill=EMERALD_MID)

    # 4. Under-cap Band (Forehead inner hijab layer)
    draw.chord([192, 132, 320, 230], start=190, end=350, fill=GOLD_LIGHT)
    draw.arc([192, 132, 320, 230], start=190, end=350, fill=GOLD_ACCENT, width=2)

    # 5. Face Oval & Contours
    draw.ellipse([190, 160, 322, 315], fill=SKIN_BASE)
    # Soft jawline shadow
    draw.arc([190, 160, 322, 315], start=40, end=140, fill=SKIN_SHADOW, width=3)

    # 6. Hijab Outer Frame wrapping face snugly and elegantly
    draw.polygon([
        (160, 180), (192, 148), (256, 140), (320, 148), (352, 180),
        (356, 260), (330, 325), (256, 355), (182, 325), (156, 260)
    ], outline=GOLD_ACCENT, fill=None)
    
    # Hijab chest wrap tuck
    draw.polygon([
        (185, 320), (256, 365), (327, 320), (290, 380), (222, 380)
    ], fill=EMERALD_DARK)
    draw.polygon([
        (205, 330), (256, 368), (307, 330), (280, 378), (232, 378)
    ], fill=EMERALD_MID)

    # 7. Eyebrows (Curved, expressive, graceful)
    # Left eyebrow
    draw.arc([212, 192, 244, 212], start=200, end=340, fill=(45, 30, 22, 255), width=3)
    # Right eyebrow
    draw.arc([268, 192, 300, 212], start=200, end=340, fill=(45, 30, 22, 255), width=3)

    # 8. Nose (Subtle elegant cartoon nose)
    draw.line([(256, 236), (258, 252), (253, 254)], fill=SKIN_SHADOW, width=2)

    # 9. Cheeks Blush (Warm gentle glow)
    # We create a temporary layer for transparent blush circles
    blush_layer = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(blush_layer)
    bdraw.ellipse([200, 245, 230, 265], fill=CHEEK_BLUSH)
    bdraw.ellipse([282, 245, 312, 265], fill=CHEEK_BLUSH)
    return blush_layer

def draw_eyes(draw, is_blinking):
    if is_blinking:
        # Gentle curved closed eyes with lashes
        # Left closed eye
        draw.arc([214, 218, 244, 236], start=20, end=160, fill=EYE_COLOR, width=3)
        draw.line([(214, 227), (210, 223)], fill=EYE_COLOR, width=2)
        draw.line([(244, 227), (248, 223)], fill=EYE_COLOR, width=2)
        # Right closed eye
        draw.arc([268, 218, 298, 236], start=20, end=160, fill=EYE_COLOR, width=3)
        draw.line([(268, 227), (264, 223)], fill=EYE_COLOR, width=2)
        draw.line([(298, 227), (302, 223)], fill=EYE_COLOR, width=2)
    else:
        # Left Eye (White + Iris + Pupil + Glint)
        draw.ellipse([214, 214, 244, 236], fill=EYE_WHITE)
        draw.ellipse([222, 214, 240, 236], fill=EYE_COLOR)
        draw.ellipse([224, 216, 238, 234], fill=(15, 10, 8, 255))
        # Catchlight sparkles
        draw.ellipse([230, 218, 235, 223], fill=(255, 255, 255, 255))
        draw.ellipse([225, 228, 228, 231], fill=(255, 255, 255, 200))
        # Eyelash line
        draw.arc([212, 210, 246, 234], start=190, end=350, fill=EYE_COLOR, width=3)
        draw.line([(244, 216), (249, 212)], fill=EYE_COLOR, width=2)

        # Right Eye
        draw.ellipse([268, 214, 298, 236], fill=EYE_WHITE)
        draw.ellipse([272, 214, 290, 236], fill=EYE_COLOR)
        draw.ellipse([274, 216, 288, 234], fill=(15, 10, 8, 255))
        # Catchlight sparkles
        draw.ellipse([280, 218, 285, 223], fill=(255, 255, 255, 255))
        draw.ellipse([275, 228, 278, 231], fill=(255, 255, 255, 200))
        # Eyelash line
        draw.arc([266, 210, 300, 234], start=190, end=350, fill=EYE_COLOR, width=3)
        draw.line([(298, 216), (303, 212)], fill=EYE_COLOR, width=2)

def draw_mouth(draw, mouth_state):
    # mouth_state: 'closed' | 'open' | 'smiling_parted'
    if mouth_state == 'closed':
        # Gentle closed smile
        draw.arc([238, 268, 274, 286], start=20, end=160, fill=LIP_COLOR, width=3)
        # Subtle dimple accents
        draw.line([(238, 275), (236, 273)], fill=LIP_COLOR, width=2)
        draw.line([(274, 275), (276, 273)], fill=LIP_COLOR, width=2)
    elif mouth_state == 'open':
        # Speaking mouth: softly open showing teeth and rosy tone
        draw.chord([236, 268, 276, 294], start=0, end=180, fill=(130, 35, 45, 255))
        # Upper teeth line
        draw.chord([240, 269, 272, 278], start=0, end=180, fill=(255, 255, 255, 255))
        # Soft lower lip arc
        draw.arc([236, 268, 276, 294], start=0, end=180, fill=LIP_COLOR, width=2)
    elif mouth_state == 'smiling_parted':
        # Cheerful parted smile for waving intro
        draw.chord([236, 266, 276, 290], start=10, end=170, fill=(150, 45, 55, 255))
        draw.chord([238, 267, 274, 276], start=0, end=180, fill=(255, 255, 255, 255))
        draw.arc([235, 265, 277, 292], start=10, end=170, fill=LIP_COLOR, width=2)

def draw_hands_and_book(draw, is_waving):
    # Open Book in front of chest
    book_left, book_top, book_right, book_bottom = 200, 385, 312, 470
    
    # Book Cover backing
    draw.polygon([
        (190, 400), (256, 420), (322, 400), (326, 480), (256, 498), (186, 480)
    ], fill=EMERALD_DARK, outline=GOLD_BORDER)

    # Book Pages (Left page & Right page)
    draw.polygon([
        (196, 406), (254, 422), (254, 490), (192, 475)
    ], fill=BOOK_PAGE)
    draw.polygon([
        (258, 422), (316, 406), (320, 475), (258, 490)
    ], fill=BOOK_PAGE)

    # Page text lines (aesthetic miniature gold lines)
    for y_off in [430, 442, 454, 466]:
        draw.line([(204, y_off), (246, y_off + 4)], fill=(180, 160, 120, 255), width=2)
        draw.line([(264, y_off + 4), (308, y_off)], fill=(180, 160, 120, 255), width=2)

    # Left Hand holding book
    draw.ellipse([180, 435, 206, 465], fill=SKIN_BASE)
    draw.arc([180, 435, 206, 465], start=0, end=360, fill=SKIN_SHADOW, width=2)

    if not is_waving:
        # Right hand also holding book on right side
        draw.ellipse([306, 435, 332, 465], fill=SKIN_BASE)
        draw.arc([306, 435, 332, 465], start=0, end=360, fill=SKIN_SHADOW, width=2)
    else:
        # Right hand is RAISED, waving high beside head!
        # Arm sleeve heading up towards the right
        draw.polygon([
            (325, 350), (390, 270), (420, 290), (345, 380)
        ], fill=EMERALD_DARK)
        # Gold sleeve cuff
        draw.line([(390, 270), (420, 290)], fill=GOLD_ACCENT, width=4)

        # Waving Hand Palm and Fingers
        # Palm
        draw.ellipse([405, 235, 450, 280], fill=SKIN_BASE)
        # Thumb
        draw.polygon([(408, 260), (388, 250), (398, 240), (415, 252)], fill=SKIN_BASE)
        # Four fingers extended upward
        draw.rounded_rectangle([420, 205, 432, 250], radius=5, fill=SKIN_BASE)
        draw.rounded_rectangle([430, 200, 442, 250], radius=5, fill=SKIN_BASE)
        draw.rounded_rectangle([440, 205, 452, 250], radius=5, fill=SKIN_BASE)
        draw.rounded_rectangle([448, 215, 460, 255], radius=5, fill=SKIN_BASE)
        
        # Motion sparkle / wave lines
        draw.arc([462, 195, 480, 220], start=270, end=60, fill=GOLD_ACCENT, width=3)
        draw.arc([470, 222, 488, 248], start=270, end=60, fill=GOLD_ACCENT, width=3)

def generate_frame(filename, is_waving=False, is_blinking=False, mouth_state='closed'):
    img = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Base body and Hijab
    blush_layer = draw_base_body_and_hijab(draw, 'base')
    
    # 2. Eyes
    draw_eyes(draw, is_blinking)

    # 3. Mouth
    draw_mouth(draw, mouth_state)

    # 4. Hands & Book / Waving
    draw_hands_and_book(draw, is_waving)

    # Composite blush layer
    img = Image.alpha_composite(img, blush_layer)

    out_path = os.path.join(OUTPUT_DIR, filename)
    img.save(out_path, 'PNG')
    print(f"Generated frame: {out_path} ({img.size})")

if __name__ == '__main__':
    # 1. inara_idle.png (both hands holding the book, mouth closed, eyes open)
    generate_frame('inara_idle.png', is_waving=False, is_blinking=False, mouth_state='closed')

    # 2. inara_wave.png (one hand raised, waving, cheerful smile)
    generate_frame('inara_wave.png', is_waving=True, is_blinking=False, mouth_state='smiling_parted')

    # 3. inara_blink.png (eyes closed, mouth closed)
    generate_frame('inara_blink.png', is_waving=False, is_blinking=True, mouth_state='closed')

    # 4. inara_mouth_open.png (eyes open, mouth open speaking)
    generate_frame('inara_mouth_open.png', is_waving=False, is_blinking=False, mouth_state='open')

    print("All 4 Inara avatar frames generated successfully!")
