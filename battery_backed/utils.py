from battery_backed.mail_processing import FileManager, ForecastProcessor
from battery_backed.forecast_service import PopulateForecast
from .models import BatteryLiveStatus,YearAgg

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
