from django.utils import timezone
from datetime import timedelta
from .models import BatterySchedule




class PopulateForecast:
    def __init__(self, devIds=[]) -> None:
        self.devIds = devIds


    def populate_battery_schedule(self):
            # Get the current time and round up to the next quarter-hour
            now = timezone.now()

            start_time = (now + timedelta(days=1)).replace(hour=1, minute=0, second=0, microsecond=0)
           
            
            # Calculate the end time (day after tomorrow at 01:00)
            end_time = (now + timedelta(days=2)).replace(hour=1, minute=0, second=0, microsecond=0)
            
            # Initialize values
            invertor_value = 1

            for dev in self.devIds:
                if dev == 'bat-0002':
                     invertor_value = 2
                # Reset SOC for each new device
                soc = 0  
                # Reset the next_quarter_hour for each device
                fifteen_min_step = start_time

                # Loop through timestamps from the next quarter-hour to the end time
                while fifteen_min_step <= end_time:
                    flow = invertor_value / 60 * 15
                    soc += flow

                    # Use get_or_create to check for existing entries or create new ones
                    obj, created = BatterySchedule.objects.get_or_create(
                        devId=dev,
                        timestamp=fifteen_min_step,
                        defaults={
                            'invertor': invertor_value,
                            'flow': flow,
                            'soc': soc,
                        }
                    )
                    
                    # If the entry already exists, update its values
                    if not created:
                        obj.invertor = invertor_value
                        obj.flow = flow
                        obj.soc = soc
                        obj.save()

                    # Move to the next timestamp (15 minutes later)
                    fifteen_min_step += timedelta(minutes=15)