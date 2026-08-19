from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from apps.core.sitemaps import (
    StaticViewSitemap, NewsSitemap, EventSitemap,
    ProgramSitemap, NoticeSitemap
)

# Customize admin
admin.site.site_header = settings.ADMIN_SITE_HEADER
admin.site.site_title = settings.ADMIN_SITE_TITLE
admin.site.index_title = settings.ADMIN_INDEX_TITLE

sitemaps = {
    'static': StaticViewSitemap,
    'news': NewsSitemap,
    'events': EventSitemap,
    'programs': ProgramSitemap,
    'notices': NoticeSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls', namespace='core')),
    path('', include('apps.academics.urls', namespace='academics')),
    path('', include('apps.content.urls', namespace='content')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]

# Serve media and static in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = 'apps.core.views.handler_404'
handler500 = 'apps.core.views.handler_500'