from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin Panel
    path('admin/', admin.site.urls),
    
    # Include App URLs
    path('', include('alvixapp.urls')),
]

# Serving static/media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
from django.urls import re_path
from django.views.static import serve
urlpatterns += [
    re_path(r'^public/(?P<path>.*)$', serve, {'document_root': settings.BASE_DIR / 'public'}),
]
