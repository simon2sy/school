from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    NewsCategory, NewsArticle, Notice,
    Event, GalleryAlbum, GalleryImage
)


@admin.register(NewsCategory)
class NewsCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'article_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

    def article_count(self, obj):
        return obj.articles.filter(is_published=True).count()
    article_count.short_description = 'Published Articles'


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'author',
        'published_at', 'is_published', 'is_featured', 'image_preview'
    ]
    list_filter = ['category', 'is_published', 'is_featured', 'published_at']
    search_fields = ['title', 'content', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['-published_at']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_published', 'is_featured']
    date_hierarchy = 'published_at'
    autocomplete_fields = ['category']

    fieldsets = (
        ('Article Content', {
            'fields': ('title', 'slug', 'category', 'excerpt', 'content')
        }),
        ('Media', {
            'fields': ('featured_image',)
        }),
        ('Publication', {
            'fields': ('author', 'published_at', 'is_published', 'is_featured')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def image_preview(self, obj):
        if obj.featured_image:
            return format_html(
                '<img src="{}" style="height:40px;width:60px;object-fit:cover;border-radius:4px;" />',
                obj.featured_image.url
            )
        return "—"
    image_preview.short_description = 'Image'


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'published_at', 'expires_at',
        'is_published', 'is_important', 'status_badge'
    ]
    list_filter = ['is_published', 'is_important', 'published_at']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['-published_at']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_published', 'is_important']

    def status_badge(self, obj):
        now = timezone.now()
        if not obj.is_published:
            color = '#6b7280'
            label = 'Draft'
        elif obj.expires_at and obj.expires_at < now:
            color = '#dc2626'
            label = 'Expired'
        elif obj.published_at > now:
            color = '#d97706'
            label = 'Scheduled'
        else:
            color = '#16a34a'
            label = 'Active'
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600;">{}</span>',
            color, label
        )
    status_badge.short_description = 'Status'


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'start_datetime', 'end_datetime',
        'location', 'is_published', 'upcoming_badge'
    ]
    list_filter = ['is_published', 'start_datetime']
    search_fields = ['title', 'description', 'location']
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['-start_datetime']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_published']

    def upcoming_badge(self, obj):
        if obj.start_datetime >= timezone.now():
            return format_html(
                '<span style="background:#2563eb;color:white;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">Upcoming</span>'
            )
        return format_html(
            '<span style="background:#6b7280;color:white;padding:2px 8px;'
            'border-radius:4px;font-size:11px;">Past</span>'
        )
    upcoming_badge.short_description = 'Type'


class GalleryImageInline(admin.TabularInline):
    model = GalleryImage
    extra = 3
    fields = [
        'image', 'title', 'caption',
        'is_featured', 'is_published', 'display_order'
    ]


@admin.register(GalleryAlbum)
class GalleryAlbumAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'image_count_display', 'display_order',
        'is_published', 'created_at'
    ]
    list_filter = ['is_published']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['display_order', '-created_at']
    list_editable = ['display_order', 'is_published']
    inlines = [GalleryImageInline]

    def image_count_display(self, obj):
        return obj.images.filter(is_published=True).count()
    image_count_display.short_description = 'Images'


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = [
        'title_or_id', 'album', 'is_featured',
        'is_published', 'image_preview'
    ]
    list_filter = ['album', 'is_featured', 'is_published']
    search_fields = ['title', 'caption', 'album__title']
    list_editable = ['is_featured', 'is_published']
    autocomplete_fields = ['album']

    def title_or_id(self, obj):
        return obj.title or f"Image #{obj.pk}"
    title_or_id.short_description = 'Title'

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:40px;width:60px;object-fit:cover;border-radius:4px;" />',
                obj.image.url
            )
        return "—"
    image_preview.short_description = 'Preview'