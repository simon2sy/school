"""
Celery application for Galaxy English School.

Start the worker:
    celery -A config worker -l info

Start the beat scheduler:
    celery -A config beat -l info

Start both (dev shortcut):
    celery -A config worker -B -l info
"""

import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

# Read config from Django settings; the CELERY_ namespace means all
# celery-related configuration keys must be prefixed with `CELERY_`.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps (every tasks.py file).
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Quick sanity-check task."""
    print(f"Request: {self.request!r}")
