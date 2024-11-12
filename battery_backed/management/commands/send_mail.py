from django.core.management.base import BaseCommand
from battery_backed.utils import make_optimized_schedule

class Command(BaseCommand):
    help = 'Empty db'

    def handle(self, *args, **kwargs):     
        make_optimized_schedule()
        self.stdout.write(self.style.SUCCESS('Database successfully empted'))
