from django.utils import timezone
from datetime import timedelta
from .models import BatterySchedule




class PopulateForecast:
    def __init__(self, devId=None) -> None:
        self.devId = devId
        

    def populate_battery_schedule(self):
        # Get the current time and round up to the next quarter-hour
        now = timezone.now()
        next_quarter_hour = (now + timedelta(minutes=15 - now.minute % 15)).replace(second=0, microsecond=0)
        
        # Calculate the end time (day after tomorrow at 01:00)
        end_time = (now + timedelta(days=2)).replace(hour=1, minute=0, second=0, microsecond=0)
        
        # Initialize values
        invertor_value = 1
        soc = 0
        
        # Loop through timestamps from the next quarter-hour to the end time
        while next_quarter_hour <= end_time:
            flow = invertor_value / 60 * 15
            soc += flow
            
            # Create and save a new BatterySchedule entry
            BatterySchedule.objects.create(
                devId=self.devId,
                timestamp=next_quarter_hour,
                invertor=invertor_value,
                flow=flow,
                soc=soc
            )
            
            # Move to the next timestamp (15 minutes later)
            next_quarter_hour += timedelta(minutes=15)
