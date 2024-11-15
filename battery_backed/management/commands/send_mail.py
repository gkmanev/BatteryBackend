from django.core.management.base import BaseCommand
from battery_backed.utils import send_optimized_schedule_to_mail

class Command(BaseCommand):
    help = 'Empty db'

    def handle(self, *args, **kwargs):     
        send_optimized_schedule_to_mail()
        self.stdout.write(self.style.SUCCESS('Email has been sent'))
