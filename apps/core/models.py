from django.db import models
from django.core.cache import cache
from django.core.exceptions import ValidationError
from apps.core.image_utils import optimize_image


class SchoolSettings(models.Model):
    # Cache key for the singleton settings object.
    CACHE_KEY = "galaxy_school_settings"
    """
    Singleton model for school-wide configuration.
    Only one instance should exist.
    """
    school_name = models.CharField(
        max_length=200,
        default="Galaxy English School"
    )
    organization_name = models.CharField(
        max_length=200,
        default="Galaxy English School"
    )
    logo = models.ImageField(
        upload_to='school/logo/',
        null=True, blank=True,
        help_text="Upload school logo (recommended: PNG with transparent background)"
    )
    favicon = models.ImageField(
        upload_to='school/favicon/',
        null=True, blank=True,
        help_text="Upload favicon (recommended: 32x32 PNG)"
    )
    address = models.TextField(
        default="Galaxy English School, Bhadrapur-9, Jhapa 57204, Nepal"
    )
    phone = models.CharField(
        max_length=50,
        default="023-542762"
    )
    email = models.EmailField(
        default="info@galaxyenglishschool.edu.np"
    )
    website = models.URLField(
        default="https://www.galaxyenglishschool.edu.np",
        blank=True
    )
    principal_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Principal's full name"
    )
    principal_message = models.TextField(
        blank=True,
        default="",
        help_text="Message from the principal"
    )
    principal_photo = models.ImageField(
        upload_to='school/principal/',
        null=True, blank=True
    )
    about = models.TextField(
        blank=True,
        default="Galaxy English School is a leading educational institution in Bhadrapur-9, Jhapa, Nepal. We are committed to providing quality education and nurturing the holistic development of our students.",
        help_text="About the school"
    )
    mission = models.TextField(
        blank=True,
        default="To provide quality education that empowers students to achieve academic excellence, develop critical thinking skills, and become responsible citizens of Nepal and the world.",
        help_text="School mission statement"
    )
    vision = models.TextField(
        blank=True,
        default="To be the premier educational institution in Eastern Nepal, recognized for academic excellence, innovation, and character development.",
        help_text="School vision statement"
    )
    facebook_url = models.URLField(blank=True, default="")
    instagram_url = models.URLField(blank=True, default="")
    youtube_url = models.URLField(blank=True, default="")
    twitter_url = models.URLField(blank=True, default="")
    admission_open = models.BooleanField(
        default=True,
        help_text="Toggle admission open/closed status"
    )
    admission_info = models.TextField(
        blank=True,
        default="Admissions are now open for the academic year 2082/83. Apply now to secure your spot.",
        help_text="Admission information displayed on website"
    )
    hero_title = models.CharField(
        max_length=200,
        default="Empowering Students to Learn, Lead and Succeed",
        help_text="Main hero section headline"
    )
    hero_subtitle = models.TextField(
        default="Galaxy English School, Birtamod provides a world-class education rooted in Nepali values. Join our community of learners and build your future with us.",
        help_text="Hero section subheading"
    )
    hero_image = models.ImageField(
        upload_to='school/hero/',
        null=True, blank=True,
        help_text="Main hero background image (recommended: 1920x1080)"
    )
    established_year = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="Year the school was established"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "School Settings"
        verbose_name_plural = "School Settings"

    def __str__(self):
        return f"{self.school_name} - Settings"

    def clean(self):
        if not self.pk and SchoolSettings.objects.exists():
            raise ValidationError(
                "Only one School Settings instance is allowed. "
                "Please edit the existing one."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        # Optimize uploads (hero/logo/principal) before storing. The favicon is
        # intentionally left untouched — it is tiny by nature.
        optimize_image(self.hero_image, max_width=1920, max_height=1080)
        optimize_image(self.logo, max_width=600, max_height=600)
        optimize_image(self.principal_photo, max_width=800, max_height=800)
        super().save(*args, **kwargs)
        # Refresh the cached copy so edits show up immediately.
        cache.set(type(self).CACHE_KEY, self)

    @classmethod
    def get_settings(cls):
        """Get school settings (cached), create default if none exists."""
        cached = cache.get(cls.CACHE_KEY)
        if cached is not None:
            return cached
        obj, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'school_name': 'Galaxy English School',
                'organization_name': 'Galaxy English School',
            }
        )
        cache.set(cls.CACHE_KEY, obj)
        return obj