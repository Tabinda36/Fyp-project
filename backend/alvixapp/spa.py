"""Serves the built React app (frontend/dist/index.html) for SPA routes."""

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.csrf import ensure_csrf_cookie

_FALLBACK = (
    "<!doctype html><title>ALVIX</title>"
    "<p style='font-family:sans-serif;padding:2rem'>The React frontend has not been built yet. "
    "Run <code>npm run build</code> in <code>frontend/</code>, or use the Vite dev server "
    "(<code>npm run dev</code>, http://localhost:5173), or set <code>ALVIX_FRONTEND=templates</code>.</p>"
)


@xframe_options_sameorigin  # the admin course view embeds the lesson player (same origin only)
@ensure_csrf_cookie
def spa_index(request, *args, **kwargs):
    index = settings.FRONTEND_DIST_DIR / 'index.html'
    try:
        html = index.read_text(encoding='utf-8')
    except OSError:
        return HttpResponse(_FALLBACK, status=503)
    return HttpResponse(html)
