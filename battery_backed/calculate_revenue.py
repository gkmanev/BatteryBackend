from battery_backed.models import BatterySchedule, Price, ForecastedPrice
from datetime import datetime
from django.utils.timezone import now
import pandas as pd



def revenue_calculations():
    # Retrieve all day-ahead market schedules
    dam_schedule = BatterySchedule.dam.all()
    
    # Get the current timestamp with timezone support
    today = now().replace(hour=0, minute=0, second=0, microsecond=0)  # Midnight of today    
    # Filter prices and forecasted prices from today onward
    price_dam = Price.objects.filter(timestamp__gte=today)
    forecasted_price_dam = ForecastedPrice.objects.filter(timestamp__gte=today)

    # Convert QuerySet to DataFrame
    battery_df = pd.DataFrame.from_records(
        dam_schedule.values('timestamp', 'devId', 'flow')
    )
    price_df = pd.DataFrame.from_records(
        price_dam.values('timestamp', 'price')
    )
    forecasted_price_df = pd.DataFrame.from_records(
        forecasted_price_dam.values('timestamp', 'price')
    )
    
    # Ensure the timestamp column is a datetime object
    for df in [battery_df, price_df, forecasted_price_df]:
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Set the timestamp as the index for resampling
    battery_df.set_index('timestamp', inplace=True)
    price_df.set_index('timestamp', inplace=True)
    forecasted_price_df.set_index('timestamp', inplace=True)

    # Resample data at 1-minute intervals
    battery_resampled = (
        battery_df.groupby('devId')  # Group by devId first
        .resample('1T')  # Resample for 1-minute intervals
        .mean()  # Calculate the mean for numerical fields
        .reset_index()
    )
    # Calculate accumulated flow for each devId
    battery_resampled['accumulated_flow'] = (
        battery_resampled.groupby('devId')['flow'].cumsum()
    )
    print(battery_resampled)    
    
    price_resampled = price_df.resample('1T').mean().reset_index()
    forecasted_price_resampled = forecasted_price_df.resample('1T').mean().reset_index()

