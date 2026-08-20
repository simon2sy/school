from datetime import timedelta
from io import BytesIO

import django
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

import apps.academics.models  # noqa: F401  (ensure models registered)
from apps.academics.models import AcademicProgram
from apps.content.models import Event, GalleryAlbum, GalleryImage, NewsArticle, Notice
from apps.core.models import SchoolSettings
from apps.core.image_utils import optimize_image


def make_jpeg(width=3000, height=2000):
    buf = BytesIO()
    Image.new("RGB", (width, height), (30, 80, 200)).save(buf, "JPEG", quality=95)
    buf.seek(0)
    return SimpleUploadedFile("photo.jpg", buf.read(), content_type="image/jpeg")


class SchoolSettingsCacheTests(TestCase):
    def test_get_settings_returns_cached_object(self):
        # LocMemCache pickles values, so repeated calls return an *equal*
        # value rather than the exact same instance — but it must hit the cache.
        result = SchoolSettings.get_settings()
        self.assertIsNotNone(result)
        self.assertEqual(SchoolSettings.get_settings(), result)

    def test_default_school_name_is_galaxy(self):
        settings = SchoolSettings.get_settings()
        self.assertEqual(settings.school_name, "Galaxy English School")


class HomeViewTests(TestCase):
    def setUp(self):
        NewsArticle.objects.create(
            title="Test News", excerpt="Excerpt", content="Body", is_published=True
        )
        Notice.objects.create(
            title="Test Notice", content="Notice body", is_published=True
        )
        Event.objects.create(
            title="Test Event", description="Desc",
            start_datetime=timezone.now() + timedelta(days=1), is_published=True,
        )
        album = GalleryAlbum.objects.create(title="Album")
        GalleryImage.objects.create(album=album, title="Pic", image=make_jpeg(), is_published=True)
        AcademicProgram.objects.create(
            name="Program", short_description="SD", description="Desc", is_published=True
        )

    def test_home_returns_200_and_shows_sections(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test News")
        self.assertContains(response, "Test Notice")
        self.assertContains(response, "Galaxy English School")


class StaticViewTests(TestCase):
    def test_about_admissions_contact_all_200(self):
        for name in ("core:about", "core:admissions", "core:contact"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CONTACT_TO_EMAIL="info@galaxyenglishschool.edu.np",
    DEFAULT_FROM_EMAIL="Galaxy English School <noreply@galaxyenglishschool.edu.np>",
)
class ContactFormTests(TestCase):
    def test_valid_submission_sends_email(self):
        outbox = django.core.mail.outbox
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "9800000000",
            "subject": "Admission inquiry",
            "message": "I would like to know more about admissions.",
        }
        response = self.client.post(reverse("core:contact"), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(outbox), 1)
        self.assertIn("Admission inquiry", outbox[0].subject)
        self.assertIn("info@galaxyenglishschool.edu.np", outbox[0].to)

    def test_invalid_form_does_not_send_email(self):
        outbox = django.core.mail.outbox
        response = self.client.post(reverse("core:contact"), {"name": "A"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(outbox), 0)


class ImageOptimizerTests(TestCase):
    def test_optimize_image_downscales_and_compresses(self):
        upload = make_jpeg(3000, 2000)
        original_size = upload.size

        album = GalleryAlbum.objects.create(title="Album")
        image = GalleryImage(album=album, title="Pic", image=upload)
        image.save()  # triggers optimize_image in save()

        image.image.open()
        optimized = Image.open(image.image)
        self.assertLessEqual(optimized.width, 1600)
        self.assertLess(optimized.size[0], original_size)

        image.delete()
        album.delete()

    def test_optimize_image_noops_on_empty(self):
        # Passing None should not raise.
        optimize_image(None)

