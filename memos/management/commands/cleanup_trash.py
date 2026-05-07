"""Permanently delete memos that have been in the trash for more than 30 days.

Usage (cron):
    0 4 * * * cd /home/ec2-user/github/memo-app && /home/ec2-user/github/memo-app/venv/bin/python manage.py cleanup_trash >> /var/log/memo-cleanup.log 2>&1
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from memos.models import Memo


DEFAULT_DAYS = 30


class Command(BaseCommand):
    help = "Permanently delete trashed memos older than N days (default 30)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=DEFAULT_DAYS,
            help="Retention period in days (default: 30)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show count without deleting",
        )

    def handle(self, *args, **options):
        days = options["days"]
        cutoff = timezone.now() - timedelta(days=days)
        qs = Memo.objects.filter(deleted_at__lt=cutoff)
        count = qs.count()
        if options["dry_run"]:
            self.stdout.write(f"[dry-run] {count} memos would be deleted (older than {days} days in trash)")
            return
        deleted, _ = qs.delete()
        self.stdout.write(f"Deleted {deleted} memos (older than {days} days in trash)")
