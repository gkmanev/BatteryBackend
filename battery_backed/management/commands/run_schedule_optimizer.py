from django.core.management.base import BaseCommand
from battery_backed.create_optimized_schedule import run_optimizer
#from battery_backed.models import BatteryLiveStatus

class Command(BaseCommand):
    help = 'Run Schedule Optimizer'

    def handle(self, *args, **kwargs):
        run_optimizer()
        self.stdout.write(self.style.SUCCESS('Run Schedule Optimizer'))
