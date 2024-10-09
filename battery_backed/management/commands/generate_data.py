from django.core.management.base import BaseCommand
from datetime import datetime
from battery_backed.models import BatterySchedule, BatteryLiveStatus
import os
import csv

class Command(BaseCommand):
    help = 'Fills the BatteryLiveStatus model with data'

    def handle(self, *args, **kwargs):                      
        
        current_dir = os.path.dirname(os.path.abspath(__file__))  # Get current directory
        csv_file_path = os.path.join(current_dir, 'csvfile1.csv')  # Replace with your CSV filename
        
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
                       
            soc = 0  # Initialize state of charge

            for row in reader:
                try:
                    date_range = row['DateRange']  # Extracting using correct key
                    invertor_power = float(row['Net Power (MW)'])  # Extracting using correct key
                
                    start_time_str = date_range.split(' - ')[1]
                    timestamp = datetime.strptime(start_time_str, '%d.%m.%Y %H:%M')
                    #print(f"timestamp:{timestamp}||invertor:{net_power}")
                except KeyError as e:
                    print(f"KeyError: {e} in row: {row}")
                    continue  # Skip this row if the key is not found
                # Calculate the flow
                flow = (invertor_power / 60) * 15
                
                # Update state of charge
                soc += flow

                obj, created = BatteryLiveStatus.objects.get_or_create(
                        devId='batt-0001',
                        timestamp=timestamp,
                        defaults={
                            'invertor_power': invertor_power,
                            'flow_last_min': flow,
                            'state_of_charge': soc,
                        }
                    )                    
                # If the entry already exists, update its values
                if not created:
                    obj.invertor_power = invertor_power
                    obj.flow_last_min = flow
                    obj.state_of_charge = soc
                    obj.save()


# def test():
#     current_dir = os.path.dirname(os.path.abspath(__file__))  # Get current directory
#     csv_file_path = os.path.join(current_dir, 'csvfile1.csv')  # Replace with your CSV filename

#     with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
#         # Read the CSV using comma as the delimiter
#         reader = csv.DictReader(csvfile, delimiter=',')  # Change to comma
#         soc = 0  # Initialize state of charge

#         for row in reader:
#             # Since row contains the entire header as a single key, we split it
#             # Split the row to get separate keys
#             try:
#                 date_range = row['DateRange']  # Extracting using correct key
#                 net_power = float(row['Net Power (MW)'])  # Extracting using correct key
#                 start_time_str = date_range.split(' - ')[1]
#                 timestamp = datetime.strptime(start_time_str, '%d.%m.%Y %H:%M')
#                 print(f"timestamp:{timestamp}||invertor:{net_power}")
#             except KeyError as e:
#                 print(f"KeyError: {e} in row: {row}")
#                 continue  # Skip this row if the key is not found
# test()

# def test():
   

#     # Define the timestamp range
#     start_time = Timestamp('2024-10-09 01:00:00+0000', tz='UTC')
#     end_time = Timestamp('2024-10-09 12:15:00+0000', tz='UTC')

#     sched = BatterySchedule.dam.prepare_consistent_response_dam()

#     filtered_data = [entry for entry in sched if start_time <= entry['timestamp'] <= end_time and entry['devId'] == 'batt-0002']

#     # Iterate over filtered data and create or update records
#     for entry in filtered_data:
#         BatterySchedule.objects.update_or_create(
#             devId='batt-0001',
#             timestamp=entry['timestamp'],
#             defaults={
#                 'invertor': entry['invertor'],
#                 'soc': entry['soc'],
#                 'flow': entry['flow']
#             }
#         )







            
