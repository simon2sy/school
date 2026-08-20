from datetime import timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.content.models import (
    Event, GalleryAlbum, GalleryImage, NewsArticle, NewsCategory, Notice,
)


def make_jpeg(width=800, height=600):
    buf = BytesIO()
    Image.new("RGB", (width, height), (10, 120, 80)).save(buf, "JPEG", quality=90)
    buf.seek(0)
    return SimpleUploadedFile("img.jpg", buf.read(), content_type="image/jpeg")


class NewsViewTests(TestCase):
    def setUp(self):
        self.published = NewsArticle.objects.create(
            title="Published Story", excerpt="Exc", content="Body",
            is_published=True, published_at=timezone.now() - timedelta(hours=1),
        )
        NewsArticle.objects.create(
            title="Future Story", excerpt="Exc", content="Body",
            is_published=True, published_at=timezone.now() + timedelta(days=1),
        )
        NewsArticle.objects.create(
            title="Draft Story", excerpt="Exc", content="Body", is_published=False,
        )

    def test_list_only_shows_published_and_live(self):
        response = self.client.get(reverse("content:news_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Story")
        self.assertNotContains(response, "Draft Story")
        self.assertNotContains(response, "Future Story")

    def test_detail_shows_published_only(self):
        self.assertEqual(
            self.client.get(
                reverse("content:news_detail", args=[self.published.slug])
            ).status_code,
            200,
        )

    def test_unpublished_detail_404(self):
        draft = NewsArticle.objects.get(title="Draft Story")
        self.assertEqual(
            self.client.get(reverse("content:news_detail", args=[draft.slug])).status_code,
            404,
        )


class NoticeViewTests(TestCase):
    def setUp(self):
        Notice.objects.create(title="Active", content="Body", is_published=True)
        expired = Notice.objects.create(
            title="Expired", content="Body", is_published=True,
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.expired = expired

    def test_expired_notice_hidden_from_list(self):
        response = self.client.get(reverse("content:notice_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active")
        self.assertNotContains(response, "Expired")


class EventViewTests(TestCase):
    def setUp(self):
        self.upcoming = Event.objects.create(
            title="Upcoming", description="Desc", is_published=True,
            start_datetime=timezone.now() + timedelta(days=5),
        )
        self.past = Event.objects.create(
            title="Past Event", description="Desc", is_published=True,
            start_datetime=timezone.now() - timedelta(days=5),
        )

    def test_list_shows_upcoming_and_past(self):
        response = self.client.get(reverse("content:event_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upcoming")
        self.assertContains(response, "Past Event")

    def test_past_events_are_paginated(self):
        for i in range(8):
            Event.objects.create(
                title=f"Past {i}", description="D", is_published=True,
                start_datetime=timezone.now() - timedelta(days=10 + i),
            )
        response = self.client.get(reverse("content:event_list"))
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.context["past_page_obj"]), 6)


class GalleryViewTests(TestCase):
    def setUp(self):
        self.album = GalleryAlbum.objects.create(title="Album")
        self.image = GalleryImage.objects.create(
            album=self.album, title="Pic", image=make_jpeg(), is_published=True
        )

    def test_gallery_list_200(self):
        self.assertEqual(self.client.get(reverse("content:gallery")).status_code, 200)

    def test_album_detail_shows_published_images(self):
        response = self.client.get(
            reverse("content:gallery_album", args=[self.album.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pic")

    def test_cleanup(self):
        self.image.delete()
        self.album.delete()

