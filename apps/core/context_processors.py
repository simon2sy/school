from .models import SchoolSettings


def school_settings(request):
    """
    Make school settings available in all templates.
    Cached per request.
    """
    try:
        settings_obj = SchoolSettings.get_settings()
    except Exception:
        settings_obj = None

    return {
        'school_settings': settings_obj,
    }