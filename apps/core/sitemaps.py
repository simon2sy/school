from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from apps.content.models import NewsArticle, Event, Notice
from apps.academics.models import AcademicProgram


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return [
            'core:home',
            'core:about',
            'core:contact',
            'core:admissions',
            'academics:programs',
            'academics:exam_routine',
            'academics:results',
            'content:news_list',
            'content:event_list',
            'content:gallery',
        ]

    def location(self, item):
        return reverse(item)


class NewsSitemap(Sitemap):
    priority = 0.7
    changefreq = 'daily'

    def items(self):
        return NewsArticle.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


class EventSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        return Event.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


class ProgramSitemap(Sitemap):
    priority = 0.8
    changefreq = 'monthly'

    def items(self):
        return AcademicProgram.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


class NoticeSitemap(Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        from django.utils import timezone
        return Notice.objects.filter(
            is_published=True,
            published_at__lte=timezone.now()
        )

    def lastmod(self, obj):
        return obj.updated_at