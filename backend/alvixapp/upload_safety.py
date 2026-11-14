"""
Validation for user-uploaded files.

Uploads are served from /media/ on the same origin as the app, so an uploaded
HTML/SVG/JS file would run as same-origin script (stored XSS). Images must be real
images; assignment files may be anything except browser-executable types.
"""

import os

from PIL import Image

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
BLOCKED_SUBMISSION_EXTENSIONS = {
    '.html', '.htm', '.xhtml', '.shtml', '.svg', '.svgz', '.xml', '.xsl', '.js', '.mjs',
    '.php', '.phtml', '.asp', '.aspx', '.jsp', '.cgi', '.exe', '.bat', '.cmd', '.ps1', '.vbs', '.hta',
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_SUBMISSION_BYTES = 20 * 1024 * 1024


class UploadRejected(ValueError):
    """Raised with a user-facing message when an upload is not acceptable."""


def _ext(uploaded):
    return os.path.splitext(getattr(uploaded, 'name', '') or '')[1].lower()


def validate_image(uploaded):
    if _ext(uploaded) not in IMAGE_EXTENSIONS:
        raise UploadRejected("Please upload an image file (JPG, PNG, GIF or WEBP).")
    if getattr(uploaded, 'size', 0) > MAX_IMAGE_BYTES:
        raise UploadRejected("Image is too large (maximum 5 MB).")
    try:
        uploaded.seek(0)
        Image.open(uploaded).verify()
    except Exception:
        raise UploadRejected("The uploaded file is not a valid image.")
    finally:
        uploaded.seek(0)
    return uploaded


def validate_submission_file(uploaded):
    if _ext(uploaded) in BLOCKED_SUBMISSION_EXTENSIONS:
        raise UploadRejected("This file type is not allowed. Upload source code, a document, PDF or ZIP archive.")
    if getattr(uploaded, 'size', 0) > MAX_SUBMISSION_BYTES:
        raise UploadRejected("File is too large (maximum 20 MB).")
    return uploaded
