from battery_backed.mail_processing import FileManager, ForecastProcessor
from battery_backed.forecast_service import PopulateForecast

def mail_schedule():
    processor = ForecastProcessor()
    processor.proceed_forecast(clearing=False)
    file_manager = FileManager()
    file_manager.process_files()


def make_forecast():
    forecast = PopulateForecast(devIds=['batt-0001', 'batt-0002'])
    forecast.populate_battery_schedule()


