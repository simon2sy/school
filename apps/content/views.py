from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from .models import (
    NewsArticle, NewsCategory, Notice,
    Event, GalleryAlbum, GalleryImage
)
from apps.core.models import SchoolSettings


def news_list(request):
    """News listing page with category filter."""
    school = SchoolSettings.get_settings()
    now = timezone.now()

    articles = NewsArticle.objects.filter(
        is_published=True,
        published_at__lte=now
    ).select_related('category', 'author').order_by('-published_at')

    # Category filter
    category_slug = request.GET.get('category')
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(NewsCategory, slug=category_slug)
        articles = articles.filter(category=selected_category)

    # Search
    search_query = request.GET.get('q', '')
    if search_query:
        articles = articles.filter(
            Q(title__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(content__icontains=search_query)
        )

    paginator = Paginator(articles, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = NewsCategory.objects.filter(
        articles__is_published=True,
        articles__published_at__lte=now
    ).distinct()

    context = {
        'school': school,
        'page_obj': page_obj,
        'categories': categories,
        'selected_category': selected_category,
        'search_query': search_query,
        'page_title': f"News & Updates - {school.school_name}",
        'meta_description': f"Latest news, announcements and updates from {school.school_name}, Birtamod, Nepal.",
    }
    return render(request, 'news/list.html', context)


def news_detail(request, slug):
    """News article detail page."""
    school = SchoolSettings.get_settings()
    now = timezone.now()

    article = get_object_or_404(
        NewsArticle,
        slug=slug,
        is_published=True,
        published_at__lte=now
    )

    related_articles = NewsArticle.objects.filter(
        is_published=True,
        published_at__lte=now
    ).exclude(pk=article.pk)

    if article.category:
        related_articles = related_articles.filter(
            category=article.category
        )

    related_articles = related_articles.order_by('-published_at')[:3]

    context = {
        'school': school,
        'article': article,
        'related_articles': related_articles,
        'page_title': f"{article.title} - {school.school_name}",
        'meta_description': article.excerpt,
        'og_image': article.featured_image.url if article.featured_image else None,
    }
    return render(request, 'news/detail.html', context)


def news_by_category(request, slug):
    """News filtered by category - redirect to news_list with filter."""
    from django.shortcuts import redirect
    return redirect(f'/news/?category={slug}')


def notice_list(request):
    """Notices listing page."""
    school = SchoolSettings.get_settings()
    now = timezone.now()

    notices = Notice.objects.filter(
        is_published=True,
        published_at__lte=now
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gte=now)
    ).order_by('-published_at')

    paginator = Paginator(notices, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'school': school,
        'page_obj': page_obj,
        'page_title': f"Notices - {school.school_name}",
        'meta_description': f"Official notices and announcements from {school.school_name}, Birtamod, Nepal.",
    }
    return render(request, 'content/notices.html', context)


def notice_detail(request, slug):
    """Notice detail page."""
    school = SchoolSettings.get_settings()
    now = timezone.now()

    notice = get_object_or_404(
        Notice,
        slug=slug,
        is_published=True,
        published_at__lte=now
    )

    context = {
        'school': school,
        'notice': notice,
        'page_title': f"{notice.title} - {school.school_name}",
        'meta_description': notice.content[:160] if notice.content else '',
    }
    return render(request, 'content/notice_detail.html', context)


def event_list(request):
    """Events listing page."""
    school = SchoolSettings.get_settings()
    now = timezone.now()

    upcoming_events = Event.objects.filter(
        is_published=True,
        start_datetime__gte=now
    ).order_by('start_datetime')

    past_events = Event.objects.filter(
        is_published=True,
        start_datetime__lt=now
    ).order_by('-start_datetime')

    paginator = Paginator(past_events, 6)
    page_number = request.GET.get('page')
    past_page_obj = paginator.get_page(page_number)

    context = {
        'school': school,
        'upcoming_events': upcoming_events,
        'past_page_obj': past_page_obj,
        'page_title': f"Events - {school.school_name}",
        'meta_description': f"Upcoming and past events at {school.school_name}, Birtamod, Nepal.",
    }
    return render(request, 'events/list.html', context)


def event_detail(request, slug):
    """Event detail page."""
    school = SchoolSettings.get_settings()

    event = get_object_or_404(
        Event,
        slug=slug,
        is_published=True
    )

    upcoming_events = Event.objects.filter(
        is_published=True,
        start_datetime__gte=timezone.now()
    ).exclude(pk=event.pk).order_by('start_datetime')[:3]

    context = {
        'school': school,
        'event': event,
        'upcoming_events': upcoming_events,
        'page_title': f"{event.title} - {school.school_name}",
        'meta_description': event.description[:160],
        'og_image': event.featured_image.url if event.featured_image else None,
    }
    return render(request, 'events/detail.html', context)


def gallery(request):
    """Gallery main page."""
    school = SchoolSettings.get_settings()

    albums = GalleryAlbum.objects.filter(
        is_published=True
    ).prefetch_related('images').order_by('display_order', '-created_at')

    context = {
        'school': school,
        'albums': albums,
        'page_title': f"Photo Gallery - {school.school_name}",
        'meta_description': f"Photo gallery of {school.school_name}, Birtamod, Nepal.",
    }
    return render(request, 'content/gallery.html', context)


def gallery_album(request, slug):
    """Gallery album detail page."""
    school = SchoolSettings.get_settings()

    album = get_object_or_404(
        GalleryAlbum,
        slug=slug,
        is_published=True
    )

    images = album.images.filter(
        is_published=True
    ).order_by('display_order', '-created_at')

    context = {
        'school': school,
        'album': album,
        'images': images,
        'page_title': f"{album.title} - Gallery - {school.school_name}",
        'meta_description': album.description or f"Photos from {album.title}",
    }
    return render(request, 'content/gallery_album.html', context)