from battery_backed.mail_processing import FileManager, ForecastProcessor, GmailService
from battery_backed.forecast_service import PopulateForecast
from battery_backed.get_price_service import GetPricesDam
from .models import BatteryLiveStatus,YearAgg, CumulativeYear
from django.db import transaction
import os
import pandas as pd
import openpyxl
import xlrd

def mail_schedule():
    processor = ForecastProcessor()
    processor.proceed_forecast(clearing=False)
    file_manager = FileManager()
    file_manager.process_files()


def make_forecast():
    forecast = PopulateForecast(devIds=['batt-0001', 'batt-0002'])
    forecast.populate_battery_schedule()


def make_optimized_schedule_send_mail():
    gmail_service = GmailService()
    file_manager = FileManager()
    fn = "sent_optimized_schedules"
    for root, dirs, files in os.walk(fn):
        xlsfiles = [f for f in files if f.endswith(('.xls', '.xlsx'))]  # Include .xlsx files as well
        for xlsfile in xlsfiles:
                my_file = file_manager.get_file_name(xlsfile)
                if my_file:
                    filepath = os.path.join(fn, xlsfile)
                    email_message = gmail_service.create_message_with_attachment(    
                        sender="georgi.manev@entra.energy",
                        to="grid.elasticity@entra.energy",
                        subject="Optimized Schedule",
                        message_text="Please find the attached Excel file.",
                        file_path=filepath,
                        file_name=xlsfile
                    )
                    gmail_service.send_message('me', email_message)



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
                timestamp=entry['timestamp'],
                defaults={
                    'cumulative_soc': entry['cumulative_soc'],
                    'cumulative_flow_last_min': entry['cumulative_flow_last_min'],
                    'cumulative_invertor_power': entry['cumulative_invertor_power'],
                }
            )


def fetch_prices_service():
    fetch = GetPricesDam()
   
    
        
