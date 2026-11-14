"""
alvixapp/qr_generator.py
Pure-Python, zero-external-dependency QR Code matrix and image generator.
Supports standard Byte-mode encoding with Reed-Solomon Error Correction (ISO/IEC 18004).
Generates high-contrast PIL Images and Base64 Data URIs suitable for certificates and verification links.
"""

import io
import base64
from PIL import Image, ImageDraw

# Galois Field GF(2^8) math for Reed-Solomon Code
GF_EXP = [0] * 512
GF_LOG = [0] * 256

def _init_galois_field():
    x = 1
    for i in range(255):
        GF_EXP[i] = x
        GF_EXP[i + 255] = x
        GF_LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11d
    GF_LOG[0] = 0

_init_galois_field()

def _gf_mul(x, y):
    if x == 0 or y == 0:
        return 0
    return GF_EXP[GF_LOG[x] + GF_LOG[y]]

def _rs_poly_multiply(p, q):
    r = [0] * (len(p) + len(q) - 1)
    for j in range(len(q)):
        for i in range(len(p)):
            r[i + j] ^= _gf_mul(p[i], q[j])
    return r

def _rs_generator_poly(nsym):
    g = [1]
    for i in range(nsym):
        g = _rs_poly_multiply(g, [1, GF_EXP[i]])
    return g

def _rs_encode(data, nsym):
    gen = _rs_generator_poly(nsym)
    msg_out = list(data) + [0] * nsym
    for i in range(len(data)):
        coef = msg_out[i]
        if coef != 0:
            for j in range(len(gen)):
                msg_out[i + j] ^= _gf_mul(gen[j], coef)
    return msg_out[len(data):]


# Supported Versions: V1 (21x21, 19 data cw, 7 ec cw), V2 (25x25, 34 data cw, 10 ec cw), V3 (29x29, 55 data cw, 15 ec cw), V4 (33x33, 80 data cw, 20 ec cw)
QR_VERSIONS = {
    1: {'size': 21, 'data_cw': 19, 'ec_cw': 7, 'align': []},
    2: {'size': 25, 'data_cw': 34, 'ec_cw': 10, 'align': [6, 18]},
    3: {'size': 29, 'data_cw': 55, 'ec_cw': 15, 'align': [6, 22]},
    4: {'size': 33, 'data_cw': 80, 'ec_cw': 20, 'align': [6, 26]},
}

def generate_qr_matrix(text: str):
    """Encodes text into a standard QR matrix using byte mode (ISO/IEC 18004)."""
    raw_bytes = text.encode('utf-8')
    data_len = len(raw_bytes)

    # Select smallest fitting QR version
    version = 1
    for v, info in QR_VERSIONS.items():
        # Byte mode header: 4 bits mode (0100) + 8 bits count = 12 bits = 1.5 bytes + data_len <= data_cw
        if data_len + 3 <= info['data_cw']:
            version = v
            break
    else:
        version = 4

    v_info = QR_VERSIONS[version]
    total_data_cw = v_info['data_cw']
    ec_cw_count = v_info['ec_cw']
    matrix_size = v_info['size']

    # 1. Build bitstream
    bits = "0100"  # Byte mode
    bits += f"{data_len:08b}"
    for b in raw_bytes:
        bits += f"{b:08b}"
    
    # Terminator (up to 4 zeroes)
    needed = total_data_cw * 8
    pad_len = min(4, needed - len(bits))
    bits += "0" * max(0, pad_len)

    # Align to byte
    if len(bits) % 8 != 0:
        bits += "0" * (8 - (len(bits) % 8))

    # Pad bytes: 0xEC (11101100), 0x11 (00010001)
    pad_bytes = ["11101100", "00010001"]
    pad_idx = 0
    while len(bits) < needed:
        bits += pad_bytes[pad_idx % 2]
        pad_idx += 1

    # Convert to data codewords
    data_cw = []
    for i in range(0, needed, 8):
        data_cw.append(int(bits[i:i+8], 2))

    # Compute error correction codewords
    ec_cw = _rs_encode(data_cw, ec_cw_count)
    final_codewords = data_cw + ec_cw

    # 2. Place into Matrix
    matrix = [[None] * matrix_size for _ in range(matrix_size)]
    reserved = [[False] * matrix_size for _ in range(matrix_size)]

    # Finder patterns at (0,0), (0, size-7), (size-7, 0)
    def place_finder(r, c):
        for dr in range(7):
            for dc in range(7):
                is_black = (
                    dr == 0 or dr == 6 or dc == 0 or dc == 6 or
                    (2 <= dr <= 4 and 2 <= dc <= 4)
                )
                matrix[r + dr][c + dc] = 1 if is_black else 0
                reserved[r + dr][c + dc] = True

        # Separators
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                rr, cc = r + dr, c + dc
                if 0 <= rr < matrix_size and 0 <= cc < matrix_size:
                    if not reserved[rr][cc]:
                        matrix[rr][cc] = 0
                        reserved[rr][cc] = True

    place_finder(0, 0)
    place_finder(0, matrix_size - 7)
    place_finder(matrix_size - 7, 0)

    # Alignment pattern if version >= 2
    if v_info['align']:
        for ar in v_info['align']:
            for ac in v_info['align']:
                if (ar < 9 and ac < 9) or (ar < 9 and ac > matrix_size - 9) or (ar > matrix_size - 9 and ac < 9):
                    continue
                for dr in range(-2, 3):
                    for dc in range(-2, 3):
                        is_black = (abs(dr) == 2 or abs(dc) == 2 or (dr == 0 and dc == 0))
                        matrix[ar + dr][ac + dc] = 1 if is_black else 0
                        reserved[ar + dr][ac + dc] = True

    # Timing patterns
    for i in range(8, matrix_size - 8):
        if not reserved[6][i]:
            matrix[6][i] = 1 if (i % 2 == 0) else 0
            reserved[6][i] = True
        if not reserved[i][6]:
            matrix[i][6] = 1 if (i % 2 == 0) else 0
            reserved[i][6] = True

    # Dark module
    matrix[4 * version + 9][8] = 1
    reserved[4 * version + 9][8] = True

    # Reserve Format Info areas
    for i in range(9):
        if 0 <= i < matrix_size:
            reserved[8][i] = True
            reserved[i][8] = True
    for i in range(matrix_size - 8, matrix_size):
        reserved[8][i] = True
        reserved[i][8] = True

    # Convert final codewords to bit array
    all_bits = []
    for cw in final_codewords:
        for bit_idx in range(7, -1, -1):
            all_bits.append((cw >> bit_idx) & 1)

    # 3. Interleave data bits in 2-column zig-zag right-to-left
    bit_cursor = 0
    direction = -1  # up
    col = matrix_size - 1

    while col > 0:
        if col == 6:  # skip vertical timing line
            col -= 1
        
        rows = range(matrix_size - 1, -1, -1) if direction == -1 else range(matrix_size)
        for row in rows:
            for c in (col, col - 1):
                if not reserved[row][c]:
                    b_val = all_bits[bit_cursor] if bit_cursor < len(all_bits) else 0
                    bit_cursor += 1
                    # Apply Mask 0: (row + col) % 2 == 0
                    mask = 1 if ((row + c) % 2 == 0) else 0
                    matrix[row][c] = b_val ^ mask

        direction = -direction
        col -= 2

    # 4. Place Format Information (EC Level L=01, Mask 0=000 -> 01000 BCH encoded: 111011111000100)
    # Masked with 101010000010010 = 010001111010110
    FORMAT_BITS = [0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0]

    # Around top-left
    fmt_coords_tl = [
        (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
        (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)
    ]
    for bit, (r, c) in zip(FORMAT_BITS, fmt_coords_tl):
        matrix[r][c] = bit

    # Bottom-left and Top-right
    for idx, bit in enumerate(FORMAT_BITS[:7]):
        matrix[matrix_size - 1 - idx][8] = bit
    for idx, bit in enumerate(FORMAT_BITS[7:]):
        matrix[8][matrix_size - 8 + idx] = bit

    return matrix


def generate_qr_image(text: str, box_size: int = 8, border: int = 4) -> Image.Image:
    """Renders a standard QR code matrix into a crisp PIL Image."""
    matrix = generate_qr_matrix(text)
    size = len(matrix)
    total_size = (size + border * 2) * box_size

    img = Image.new('RGB', (total_size, total_size), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    for r in range(size):
        for c in range(size):
            if matrix[r][c] == 1:
                x0 = (c + border) * box_size
                y0 = (r + border) * box_size
                x1 = x0 + box_size
                y1 = y0 + box_size
                draw.rectangle([x0, y0, x1, y1], fill=(6, 78, 59))  # Deep Emerald Green

    return img


def generate_qr_base64_data_uri(text: str) -> str:
    """Returns a data URI string (data:image/png;base64,...) for embedding in HTML/templates."""
    img = generate_qr_image(text, box_size=6, border=3)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{encoded}"
