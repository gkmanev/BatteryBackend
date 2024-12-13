from django.core.management.base import BaseCommand
from battery_backed.create_optimized_schedule import run_optimizer
from battery_backed.models import BatteryLiveStatus
from datetime import datetime
import pandas as pd

class Command(BaseCommand):
    help = 'Run Schedule Optimizer'

    def handle(self, *args, **kwargs):
        optimized_schedule = run_optimizer()        
        soc=0
        for row in optimized_schedule.itertuples():            
            
            invertor = row.schedule
            flow = invertor/60*15          
            flow_min = invertor/60
            soc += flow

            BatteryLiveStatus.objects.get_or_create(
                    devId='batt-0001', 
                    timestamp=row.Index,
                    invertor_power=invertor,
                    flow_last_min=flow_min,
                    state_of_charge=soc
                )                    

        self.stdout.write(self.style.SUCCESS('Run Schedule Optimizer'))
