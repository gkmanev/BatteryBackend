from battery_backed.mail_processing import FileManager, ForecastProcessor
from battery_backed.forecast_service import PopulateForecast
from .models import BatteryLiveStatus,YearAgg, CumulativeYear
from django.db import transaction

import pandas as pd

def mail_schedule():
    processor = ForecastProcessor()
    processor.proceed_forecast(clearing=False)
    file_manager = FileManager()
    file_manager.process_files()


def make_forecast():
    forecast = PopulateForecast(devIds=['batt-0001', 'batt-0002'])
    forecast.populate_battery_schedule()


def agg_for_year_endpoint():
    year_dataset = BatteryLiveStatus.year.all()

    for item in year_dataset:          

        obj, created = YearAgg.objects.get_or_create(
                            devId=item["devId"],
                            timestamp=item["truncated_timestamp"],
                            defaults={
                                'invertor_power': item["invertor_power_avg"],
                                'flow_last_min': item["flow_last_min_avg"],
                                'state_of_charge': item["state_of_charge_avg"],
                            }
                        )                    
                    # If the entry already exists, update its values
        if not created:
            obj.invertor_power = item["invertor_power_avg"]
            obj.flow_last_min = item["flow_last_min_avg"]
            obj.state_of_charge = item["state_of_charge_avg"]
            obj.save()

    

def get_cumulative_data_year():
    
    year_dataset = YearAgg.objects.all()
     
    data = list(year_dataset.values())
    if not data:
        return []
    
    df = pd.DataFrame(data)
    # Convert 'timestamp' field to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])        
    
    df = df.sort_values(by='timestamp')

    # Round numerical columns to 2 decimal places
    numeric_columns = ['invertor_power', 'state_of_charge', 'flow_last_min']  # Adjust based on your data fields
    df[numeric_columns] = df[numeric_columns].round(2)   
    df.fillna(0, inplace=True) 
    
    
    # Group by timestamp and calculate cumulative sum of state_of_charge
    df_cumulative = df.groupby('timestamp').agg(
    cumulative_soc=('state_of_charge', 'sum'),
    cumulative_flow_last_min=('flow_last_min', 'sum'),
    cumulative_invertor_power=('invertor_power', 'sum')
    ).reset_index()
    # Round the cumulative sums to 2 decimal places
    df_cumulative['cumulative_soc'] = df_cumulative['cumulative_soc'].round(2)
    df_cumulative['cumulative_flow_last_min'] = df_cumulative['cumulative_flow_last_min'].round(2)
    df_cumulative['cumulative_invertor_power'] = df_cumulative['cumulative_invertor_power'].round(2)
    df_cumulative.fillna(0, inplace=True)
    # Convert back to a list of dictionaries
    cumulative_result = df_cumulative.to_dict(orient='records')
    
    with transaction.atomic():  # Ensure atomicity of database operations
        for entry in cumulative_result:
            CumulativeYear.objects.update_or_create(
                devId=entry['devId'],
                timestamp=entry['timestamp'],
                defaults={
                    'cumulative_soc': entry['cumulative_soc'],
                    'cumulative_flow_last_min': entry['cumulative_flow_last_min'],
                    'cumulative_invertor_power': entry['cumulative_invertor_power'],
                }
            )

   
    
        
