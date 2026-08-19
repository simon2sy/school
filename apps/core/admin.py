from django.contrib import admin
from django.utils.html import format_html
from .models import SchoolSettings


@admin.register(SchoolSettings)
class SchoolSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'school_name', 'organization_name',
                'logo', 'favicon', 'established_year'
            )
        }),
        ('Contact Information', {
            'fields': ('address', 'phone', 'email', 'website')
        }),
        ('Principal', {
            'fields': (
                'principal_name', 'principal_message', 'principal_photo'
            )
        }),
        ('About', {
            'fields': ('about', 'mission', 'vision')
        }),
        ('Homepage Hero', {
            'fields': ('hero_title', 'hero_subtitle', 'hero_image')
        }),
        ('Admissions', {
            'fields': ('admission_open', 'admission_info')
        }),
        ('Social Media', {
            'fields': (
                'facebook_url', 'instagram_url',
                'youtube_url', 'twitter_url'
            )
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def has_add_permission(self, request):
        # Only allow one instance
        return not SchoolSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="height:50px;" />',
                obj.logo.url
            )
        return "No logo"
    logo_preview.short_description = 'Logo Preview'