from django.core.management.base import BaseCommand
from battery_backed.utils import make_optimized_schedule_send_mail

class Command(BaseCommand):
    help = 'Empty db'

    def handle(self, *args, **kwargs):     
        make_optimized_schedule_send_mail()
        self.stdout.write(self.style.SUCCESS('Email has been sent'))
