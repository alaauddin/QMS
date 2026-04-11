from django.core.management.base import BaseCommand
from django.utils import timezone
from qms_core.models import CounterAssignment

class Command(BaseCommand):
    help = "Activate shifts automatically based on current time"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        assignments = CounterAssignment.objects.all()
        activated_count = 0
        deactivated_count = 0
        
        for assign in assignments:
            if assign.start_time and assign.end_time:
                was_active = assign.is_active
                is_now_active = assign.start_time <= now <= assign.end_time
                if was_active != is_now_active:
                    assign.is_active = is_now_active
                    assign.save()
                    if is_now_active:
                        activated_count += 1
                    else:
                        deactivated_count += 1
                        
        self.stdout.write(self.style.SUCCESS(
            f'Shifts updated: {activated_count} activated, {deactivated_count} deactivated.'
        ))
