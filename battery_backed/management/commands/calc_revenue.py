from django.core.management.base import BaseCommand

from battery_backed.calculate_revenue import revenue_calculations

class Command(BaseCommand):
    help = 'Calc'

    def handle(self, *args, **kwargs):

        revenue_calculations()
        
        self.stdout.write(self.style.SUCCESS('Database successfully empted'))