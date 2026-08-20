from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from apps.core.image_utils import optimize_image


class NewsCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name = "News Category"
        verbose_name_plural = "News Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('content:news_by_category', kwargs={'slug': self.slug})


class NewsArticle(models.Model):
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    category = models.ForeignKey(
        NewsCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='articles'
    )
    excerpt = models.TextField(
        max_length=500,
        help_text="Short summary shown in article lists"
    )
    content = models.TextField(help_text="Full article content (HTML supported)")
    featured_image = models.ImageField(
        upload_to='news/images/',
        null=True, blank=True
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='news_articles'
    )
    published_at = models.DateTimeField(
        default=timezone.now,
        help_text="When to publish this article"
    )
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(
        default=False,
        help_text="Feature this article on the homepage"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at']
        verbose_name = "News Article"
        verbose_name_plural = "News Articles"
        indexes = [
            models.Index(fields=['-published_at']),
            models.Index(fields=['is_published']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        optimize_image(self.featured_image)
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base_slug = slugify(self.title)
        slug = base_slug
        counter = 1
        while NewsArticle.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('content:news_detail', kwargs={'slug': self.slug})

    @property
    def is_live(self):
        return self.is_published and self.published_at <= timezone.now()


class Notice(models.Model):
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    content = models.TextField(help_text="Notice content")
    image = models.ImageField(
        upload_to='notices/images/',
        null=True, blank=True,
        help_text="Upload an image to display with the notice"
    )
    attachment = models.FileField(
        upload_to='notices/attachments/',
        null=True, blank=True,
        help_text="Upload PDF or document attachment"
    )
    published_at = models.DateTimeField(
        default=timezone.now,
        help_text="When to publish this notice"
    )
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Leave blank for no expiry"
    )
    is_published = models.BooleanField(default=True)
    is_important = models.BooleanField(
        default=False,
        help_text="Mark as important/urgent notice"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at']
        verbose_name = "Notice"
        verbose_name_plural = "Notices"
        indexes = [
            models.Index(fields=['-published_at']),
            models.Index(fields=['is_published']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        optimize_image(self.image)
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base_slug = slugify(self.title)
        slug = base_slug
        counter = 1
        while Notice.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('content:notice_detail', kwargs={'slug': self.slug})

    @property
    def is_active(self):
        now = timezone.now()
        if not self.is_published:
            return False
        if self.published_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True

    @property
    def is_expired(self):
        if self.expires_at and self.expires_at < timezone.now():
            return True
        return False


class Event(models.Model):
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    description = models.TextField()
    featured_image = models.ImageField(
        upload_to='events/images/',
        null=True, blank=True
    )
    location = models.CharField(
        max_length=300,
        blank=True,
        help_text="Event location/venue"
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_datetime']
        verbose_name = "Event"
        verbose_name_plural = "Events"
        indexes = [
            models.Index(fields=['-start_datetime']),
            models.Index(fields=['is_published']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        optimize_image(self.featured_image)
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base_slug = slugify(self.title)
        slug = base_slug
        counter = 1
        while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('content:event_detail', kwargs={'slug': self.slug})

    @property
    def is_upcoming(self):
        return self.start_datetime >= timezone.now()

    @property
    def is_past(self):
        return self.start_datetime < timezone.now()


class GalleryAlbum(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(
        upload_to='gallery/covers/',
        null=True, blank=True
    )
    is_published = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = "Gallery Album"
        verbose_name_plural = "Gallery Albums"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        optimize_image(self.cover_image)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('content:gallery_album', kwargs={'slug': self.slug})

    @property
    def image_count(self):
        return self.images.filter(is_published=True).count()


class GalleryImage(models.Model):
    album = models.ForeignKey(
        GalleryAlbum,
        on_delete=models.CASCADE,
        related_name='images'
    )
    title = models.CharField(max_length=200, blank=True)
    caption = models.TextField(blank=True)
    image = models.ImageField(upload_to='gallery/images/')
    is_featured = models.BooleanField(
        default=False,
        help_text="Feature on homepage gallery preview"
    )
    is_published = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = "Gallery Image"
        verbose_name_plural = "Gallery Images"

    def __str__(self):
        return self.title or f"Image in {self.album.title}"

    def save(self, *args, **kwargs):
        optimize_image(self.image)
        super().save(*args, **kwargs)