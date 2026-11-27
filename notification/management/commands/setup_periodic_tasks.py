from django.core.management.base import BaseCommand
from django_q.models import Schedule


class Command(BaseCommand):
    help = "Configure periodic Django Q tasks"

    def handle(self, *args, **options):
        schedule, created = Schedule.objects.get_or_create(
            name="Check overdue borrowings daily",
            defaults={
                "func": "notification.tasks.check_overdue_borrowings",
                "schedule_type": Schedule.DAILY,
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS("Daily overdue check schedule created.")
            )
        else:
            self.stdout.write("Daily overdue check schedule already exists.")
