from django.core.management.base import BaseCommand
from datetime import datetime
from battery_backed.models import BatterySchedule
import os
import csv


class Command(BaseCommand):
    help = 'Fills the BatterySchedule model with data'

    def handle(self, *args, **kwargs):
        current_dir = os.path.dirname(os.path.abspath(__file__))  # Get the current file's directory
        csv_file_path = os.path.join(current_dir, 'csvfile1.csv')  # Replace with your CSV filename
        
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='\t')  # Adjust delimiter if necessary
            soc = 0  # Initialize state of charge

            for row in reader:
                # Extract and parse the date range
                date_range = row['DateRange']
                net_power = float(row['Net Power (MW)'])

                # Parse the start time from the DateRange
                start_time_str = date_range.split(' - ')[1]
                timestamp = datetime.strptime(start_time_str, '%d.%m.%Y %H:%M')

                # Calculate the flow
                flow = (net_power / 60) * 15
                
                # Update state of charge
                soc += flow

                # Create and save the BatterySchedule instance
                battery_schedule = BatterySchedule(
                    devId='batt1',
                    timestamp=timestamp,
                    invertor=net_power,
                    soc=soc,
                    flow=flow
                )
                battery_schedule.save()
            
