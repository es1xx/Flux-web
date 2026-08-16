"""
URL configuration for blog_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.shortcuts import redirect
from django.utils import translation


def root_redirect(request):
    """Send bare `/` to the active language prefix (`/en/` or `/uk/`)."""
    lang = translation.get_language() or settings.LANGUAGE_CODE
    if lang not in {code for code, _ in settings.LANGUAGES}:
        lang = settings.LANGUAGE_CODE
    return redirect(f'/{lang}/')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', root_redirect),
]

urlpatterns += i18n_patterns(
    path('', include('blog.urls')),
    prefix_default_language=True,
)

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
