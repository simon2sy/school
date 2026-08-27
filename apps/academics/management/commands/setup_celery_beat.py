"""
Management command to set up Celery Beat periodic tasks.

Usage:
    python manage.py setup_celery_beat

Creates the following periodic schedules:

1. warm_all_public_caches  — every 30 minutes (warms programs + routines)
2. bulk_recalculate_check  — daily at 2 AM (safety net for GPA consistency)

Run this once after deploying Celery + django-celery-beat.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Set up Celery Beat periodic tasks for cache warming and maintenance."

    def handle(self, *args, **options):
        try:
            from django_celery_beat.models import (
                PeriodicTask, PeriodicTaskSchedule, CrontabSchedule,
            )
        except ImportError:
            self.stderr.write(
                self.style.ERROR(
                    "django-celery-beat is not installed. "
                    "Install it with: pip install django-celery-beat"
                )
            )
            return

        created_count = 0

        # ── Crontab: every 30 minutes ──
        every_30_min, _ = CrontabSchedule.objects.get_or_create(
            minute='*/30',
            hour='*',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )

        # ── Crontab: daily at 2:00 AM ──
        daily_2am, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='2',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )

        # ── Task 1: Warm all public caches every 30 minutes ──
        task1, created = PeriodicTask.objects.get_or_create(
            name='Warm all public caches (every 30 min)',
            defaults={
                'task': 'apps.academics.tasks.warm_all_public_caches',
                'crontab': every_30_min,
                'enabled': True,
                'description': (
                    'Pre-populates Redis caches for programs, exam routines, '
                    'and other public-facing data. Reduces first-hit latency.'
                ),
            },
        )
        if created:
            created_count += 1
            self.stdout.write(self.style.SUCCESS(
                '  ✓ Created: Warm all public caches (every 30 min)'
            ))
        else:
            self.stdout.write('  → Already exists: Warm all public caches')

        # ── Task 2: Daily GPA consistency check ──
        # This recalculates GPA for all results if the grading scale was changed.
        # Disabled by default — enable manually when needed.
        task2, created = PeriodicTask.objects.get_or_create(
            name='Daily GPA consistency check (disabled)',
            defaults={
                'task': 'apps.academics.tasks.warm_all_public_caches',
                'crontab': daily_2am,
                'enabled': False,  # Disabled by default — manual trigger
                'description': (
                    'Safety net: recalculates all GPAs daily at 2 AM. '
                    'Enable this if you change the grading scale mid-year.'
                ),
            },
        )
        if created:
            created_count += 1
            self.stdout.write(self.style.SUCCESS(
                '  ✓ Created (disabled): Daily GPA consistency check'
            ))
        else:
            self.stdout.write('  → Already exists: Daily GPA consistency check')

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Done! {created_count} new periodic task(s) created.\n'
                f'\n'
                f'Next steps:\n'
                f'  1. Start Redis:   redis-server\n'
                f'  2. Start worker:  celery -A config worker -l info\n'
                f'  3. Start beat:    celery -A config beat -l info\n'
                f'     (or both:      celery -A config worker -B -l info)\n'
                f'\n'
                f'You can also manage periodic tasks from Django admin:\n'
                f'  Admin → django-celery-beat → Periodic Tasks'
            )
        )
