from battery_backed.models import BatterySchedule, Price, ForecastedPrice
from datetime import datetime
from django.utils.timezone import now
import pandas as pd
from django.core.cache import cache


def revenue_calculations():
    BatterySchedule.revenue.revenue_calc()


    
    # Resample data at 1-minute intervals
    # aggregated_flow = (
    #     battery_df.groupby('timestamp')['flow'].sum()  # Sum flow values at each timestamp
    #     .resample('1T')  # Resample to 1-minute intervals
    #     .sum()  # Perform resampling aggregation
    #     .fillna(method='ffill')  # Fill NaN values by forward filling
    #     .reset_index()  # Reset index to return a flat DataFrame
    # )
    
    
    # cache.set('accumulated_flow_price_data', merged_df[['timestamp', 'accumulated_flow_price']].to_dict(orient='records'), timeout=3600)

    # # Merge aggregated_flow and price_resampled on 'timestamp'
    # merged_df = pd.merge(aggregated_flow, price_resampled, on='timestamp', how='inner')

    # # Create a new column that is the product of 'total_flow' and 'price'
    # merged_df['flow_price'] = merged_df['flow'] * merged_df['price']

    # merged_df['accumulated_flow_price'] = merged_df['flow_price'].cumsum()


    # # Optionally reset index if needed
    # merged_df.reset_index(drop=True, inplace=True)    
    
    
    # cache.set('accumulated_flow_price_data', merged_df[['timestamp', 'accumulated_flow_price']].to_dict(orient='records'), timeout=3600)

    #forecasted_price_resampled = forecasted_price_df.resample('1T').mean().reset_index()