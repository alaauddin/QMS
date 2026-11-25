from django.core.management.base import BaseCommand
from django.utils import timezone
from qms_core.models import Token


class Command(BaseCommand):
    help = 'Marks all still-pending tickets as "Did Not Show Up" at end of day.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show how many tickets would be marked without saving.',
        )
        parser.add_argument(
            '--status',
            default='waiting',
            help='Source status to treat as pending (default: waiting).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        source_status = options['status']

        pending = Token.objects.filter(status=source_status)
        count = pending.count()

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[DRY RUN] Would mark {count} pending ticket(s) ("{source_status}") as "Did Not Show Up".'
            ))
            return

        updated = pending.update(status='no_show')

        self.stdout.write(self.style.SUCCESS(
            f'Marked {updated} pending ticket(s) as "Did Not Show Up" at {timezone.now()}.'
        ))
