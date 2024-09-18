from battery_backed.mail_processing import FileManager, ForecastProcessor

def mail_schedule():
    processor = ForecastProcessor()
    processor.proceed_forecast(clearing=False)
    file_manager = FileManager()
    file_manager.process_files()

