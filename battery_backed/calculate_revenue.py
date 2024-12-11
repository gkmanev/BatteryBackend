from battery_backed.models import BatterySchedule, Price, ForecastedPrice
from datetime import datetime, timedelta
from django.utils.timezone import now
import pandas as pd
from django.core.cache import cache


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
    aggregated_flow = (
        battery_df.groupby('timestamp')['flow'].sum()  # Sum flow values at each timestamp
        .resample('1T')  # Resample to 1-minute intervals
        .sum()  # Perform resampling aggregation
        .fillna(method='ffill')  # Fill NaN values by forward filling
        .reset_index()  # Reset index to return a flat DataFrame
    )

    # Print the first 200 rows for inspection
    pd.set_option('display.max_rows', None)

        
    price_resampled = price_df.resample('1T').mean().fillna(method='ffill').reset_index()

    # Merge aggregated_flow and price_resampled on 'timestamp'
    merged_df = pd.merge(aggregated_flow, price_resampled, on='timestamp', how='inner')

    # Create a new column that is the product of 'total_flow' and 'price'
    merged_df['flow_price'] = merged_df['flow'] * merged_df['price']

    merged_df['accumulated_flow_price'] = merged_df['flow_price'].cumsum()


    # Optionally reset index if needed
    merged_df.reset_index(drop=True, inplace=True) 

    # divide merged_df to 2 data frames - before and after now!
    today_end = today + timedelta(days=1) - timedelta(seconds=1) 
    now = datetime.now()
    # Filter for data from today at 00:00 to now
    df_today_to_now = merged_df[(merged_df['timestamp'] >= today) & (merged_df['timestamp'] <= now)]
    df_today_to_now = {
        'to_now':df_today_to_now
    }

    # Filter for data from now to the end of today
    df_now_to_end = merged_df[(merged_df['timestamp'] > now) & (merged_df['timestamp'] <= today_end)]
    df_now_to_end = {
        'from_now':df_now_to_end
    }
    
    cache.set('today_to_now', df_today_to_now[['timestamp', 'accumulated_flow_price']].to_dict(orient='records'), timeout=3600)
    cache.set('now_to_tomorrow', df_now_to_end[['timestamp', 'accumulated_flow_price']].to_dict(orient='records'), timeout=3600)

    #forecasted_price_resampled = forecasted_price_df.resample('1T').mean().reset_index()