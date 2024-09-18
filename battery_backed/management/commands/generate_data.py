from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware
from datetime import timedelta
from battery_backed.models import BatteryLiveStatus

class Command(BaseCommand):
    help = 'Fills the BatteryLiveStatus model with data from a specified timestamp range'

    def handle(self, *args, **kwargs):
        #BatteryLiveStatus.objects.all().delete()
        start_time = "2024-08-28 00:00"
        end_time = "2024-08-28 17:36"
        
        # Parse the start and end timestamps
        start_time = make_aware(parse_datetime(start_time))
        end_time = make_aware(parse_datetime(end_time))
        
        # Invertor power data provided for every 15 minutes
  
        data = [25, 25, 25, 25, 0, 0, 0, 0, 0, 0, 0, 0, 25, 25, 25, 25, 25, 25, 25, 25, 
    25, 25, 25, 25, -10, 0, 0, 0, 0, 0, 0, 0, -25, -25, -25, -25, -25, -25, 
    -25, -25, 10, 10, 10, 10, 10, 10, 10, 10, -25, -25, -25, -25, -25, -25, 
    -25, -25, -25, -25, -19, 0, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 
    25, 25, 25, 25, 25, 25, 25, 25, 15, 0, 0, 0, -25, -25, -25, -25, -25, 
    -25, -25, -25, -25, -25, -25, -25, -25]


        # Resample the data to have a value for each minute
        invertor_power = []
        for i in data:
            invertor_power.extend([i] * 15)
        
        # Generate timestamps with corresponding data
        current_time = start_time
        index = 0
        state_of_charge = 0
        flow_last_min = 0
        while current_time <= end_time and index < len(invertor_power):
            state_of_charge += (invertor_power[index]*0.97)/60            
            flow_last_min = (invertor_power[index]*0.97)/60
            invertor = invertor_power[index]*0.97
            rounded_soc = f"{round(state_of_charge, 2):.2f}"
            rounded_flow_last_min = f"{round(flow_last_min, 2):.2f}"
            rounded_invertor = f"{round(invertor, 2):.2f}"
            BatteryLiveStatus.objects.create(
                devId='batt-0001',
                timestamp=current_time,
                state_of_charge=rounded_soc,  # Add logic here if you have specific state_of_charge data
                flow_last_min=rounded_flow_last_min,  # Add logic here if you have specific flow_last_min data
                invertor_power=rounded_invertor
            )
            current_time += timedelta(minutes=1)
            index += 1

        self.stdout.write(self.style.SUCCESS('Database successfully filled with BatteryLiveStatus data'))
