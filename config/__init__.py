"""
This package will contain the Django project's Celery app.
It ensures the Celery app is always imported when
Django starts so that @shared_task will use this app.

If celery is not installed, the app still works —
async tasks just won't run until a worker is available.
"""

try:
    from .celery import app as celery_app
    __all__ = ("celery_app",)
except ImportError:
    # celery is not installed — graceful degradation.
    # The project runs fine; @shared_task calls will be
    # executed synchronously as a fallback.
    pass
