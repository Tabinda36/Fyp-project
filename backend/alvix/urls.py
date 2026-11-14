from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from alvixapp.spa import spa_index

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('alvixapp.api.urls')),
    path('', include('alvixapp.urls')),
    # Inara avatar frames and other public assets
    re_path(r'^public/(?P<path>.*)$', serve, {'document_root': settings.PUBLIC_ROOT}),
]

# Uploaded media (profile pictures, course images, lesson audio/PPT, assignment files).
# static() only works with DEBUG=True, so serve it explicitly; set ALVIX_SERVE_MEDIA=False
# when a web server (nginx etc.) serves MEDIA_ROOT instead.
if getattr(settings, 'ALVIX_SERVE_MEDIA', True):
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

# Built React assets (/assets/*.js|css) and SPA fallback for unknown paths (React shows its 404).
if getattr(settings, 'ALVIX_FRONTEND', 'templates') == 'react':
    urlpatterns += [
        re_path(r'^assets/(?P<path>.*)$', serve, {'document_root': settings.FRONTEND_DIST_DIR / 'assets'}),
        re_path(r'^(?!api/|admin/|media/|static/|public/).*$', spa_index),
    ]
