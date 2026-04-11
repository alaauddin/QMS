import datetime
from django.core.management.base import BaseCommand
from qms_core.models import CounterAssignment
from django.utils import timezone

class Command(BaseCommand):
    help = 'Cleans up old inactive counter assignments to keep the database lean.'

    def handle(self, *args, **options):
        # Keep only last 30 days of history
        cutoff = timezone.now() - datetime.timedelta(days=30)
        deleted_count, _ = CounterAssignment.objects.filter(
            is_active=False, 
            end_time__lt=cutoff
        ).delete()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} old assignments.'))
