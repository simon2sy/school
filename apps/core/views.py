from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from .models import SchoolSettings
from apps.content.models import NewsArticle, Event, Notice, GalleryImage
from apps.academics.models import AcademicProgram


@cache_page(60 * 5)
def home(request):
    """Homepage view with all sections."""
    school = SchoolSettings.get_settings()
    now = timezone.now()

    # Latest published news
    latest_news = NewsArticle.objects.filter(
        is_published=True
    ).select_related('category', 'author').order_by('-published_at')[:6]

    # Upcoming events
    upcoming_events = Event.objects.filter(
        is_published=True,
        start_datetime__gte=now
    ).order_by('start_datetime')[:4]

    # Active notices
    active_notices = Notice.objects.filter(
        is_published=True,
        published_at__lte=now
    ).filter(
        models_expires_filter(now)
    ).order_by('-published_at')[:5]

    # Academic programs
    programs = AcademicProgram.objects.filter(
        is_published=True
    ).order_by('display_order')[:6]

    # One gallery query feeds both homepage sections. Featured images power the
    # "Life at Galaxy" preview; otherwise the most recent published photos are
    # used so the section is never empty. The "Inspiring Moments" strip shows
    # the latest published shots. (Featured images are a subset of published.)
    recent_images = list(
        GalleryImage.objects.filter(is_published=True)
        .select_related('album')
        .order_by('-created_at')[:8]
    )
    featured = [img for img in recent_images if img.is_featured][:8]
    gallery_images = featured or recent_images
    gallery_pictures = recent_images[:6]

    # Inspirational quotes shown in the "Inspiring Moments" section.
    inspiring_quotes = [
        {
            'initial': 'E',
            'name': 'Emma R.',
            'role': 'Class 8 Student',
            'color': 'from-blue-500 to-blue-700',
            'quote': 'Galaxy has given me the confidence to speak up and the curiosity to keep asking questions.',
        },
        {
            'initial': 'R',
            'name': 'Rajesh K.',
            'role': 'Parent',
            'color': 'from-emerald-500 to-cyan-600',
            'quote': 'Seeing my child thrive here has been the greatest joy. Galaxy truly cares for every student.',
        },
        {
            'initial': 'S',
            'name': 'Sita M.',
            'role': 'Class 10 Student',
            'color': 'from-amber-500 to-orange-600',
            'quote': "The teachers don't just teach - they inspire. I've discovered a love for learning here.",
        },
    ]

    context = {
        'school': school,
        'latest_news': latest_news,
        'upcoming_events': upcoming_events,
        'active_notices': active_notices,
        'programs': programs,
        'gallery_images': gallery_images,
        'gallery_pictures': gallery_pictures,
        'inspiring_quotes': inspiring_quotes,
        'page_title': f"{school.school_name} - Quality Education in Bhadrapur-9, Jhapa, Nepal",
        'meta_description': f"Welcome to {school.school_name}, Bhadrapur-9, Jhapa, Nepal. Providing quality education under {school.organization_name}.",
    }
    return render(request, 'pages/home.html', context)


def models_expires_filter(now):
    """Filter for notices that haven't expired."""
    from django.db.models import Q
    return Q(expires_at__isnull=True) | Q(expires_at__gte=now)


def about(request):
    """About page."""
    school = SchoolSettings.get_settings()
    context = {
        'school': school,
        'page_title': f"About Us - {school.school_name}",
        'meta_description': f"Learn about {school.school_name}, its mission, vision, and commitment to quality education in Bhadrapur-9, Jhapa, Nepal.",
    }
    return render(request, 'pages/about.html', context)


def admissions(request):
    """Admissions page."""
    school = SchoolSettings.get_settings()
    programs = AcademicProgram.objects.filter(
        is_published=True
    ).order_by('display_order')

    context = {
        'school': school,
        'programs': programs,
        'page_title': f"Admissions - {school.school_name}",
        'meta_description': f"Apply for admission at {school.school_name}, Bhadrapur-9, Jhapa. Quality education for your bright future.",
    }
    return render(request, 'pages/admissions.html', context)


def contact(request):
    """Contact page with contact form."""
    from .forms import ContactForm
    school = SchoolSettings.get_settings()
    form = ContactForm()

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            from django.conf import settings as dj_settings
            from django.core.mail import send_mail
            from django.contrib import messages
            import logging

            logger = logging.getLogger(__name__)
            cleaned = form.cleaned_data
            subject = f"[Contact Form] {cleaned['subject']} - {cleaned['name']}"
            body = (
                f"Name: {cleaned['name']}\n"
                f"Email: {cleaned['email']}\n"
                f"Phone: {cleaned.get('phone', 'Not provided')}\n\n"
                f"Message:\n{cleaned['message']}"
            )
            try:
                send_mail(
                    subject,
                    body,
                    dj_settings.DEFAULT_FROM_EMAIL,
                    [dj_settings.CONTACT_TO_EMAIL],
                    fail_silently=False,
                )
                messages.success(
                    request,
                    "Thank you for your message! We will get back to you shortly.",
                )
            except Exception as exc:
                # The console backend just prints in dev; on any failure we log
                # but still thank the visitor instead of showing an error page.
                logger.warning("Contact form email failed: %s", exc)
                messages.info(
                    request,
                    "Thanks for your message! Our team will contact you shortly.",
                )
            form = ContactForm()

    context = {
        'school': school,
        'form': form,
        'page_title': f"Contact Us - {school.school_name}",
        'meta_description': f"Contact {school.school_name}, Bhadrapur-9, Jhapa, Nepal.",
    }
    return render(request, 'pages/contact.html', context)


def handler_404(request, exception):
    school = SchoolSettings.get_settings()
    return render(request, 'errors/404.html', {'school': school}, status=404)


def handler_500(request):
    try:
        school = SchoolSettings.get_settings()
    except Exception:
        school = None
    return render(request, 'errors/500.html', {'school': school}, status=500)