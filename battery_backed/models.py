from django.db import models
from datetime import datetime, timedelta
from django.db.models import Avg, Sum, Case, When, Value, F, FloatField
from django.db.models.functions import TruncDay, TruncHour, Round
from django.utils import timezone
from pytz import timezone
import pandas as pd
import pytz
from django.core.cache import cache




class MonthManager(models.Manager):
    
    def get_queryset(self):
        # Get the start of the month
        today = datetime.today()
        start_of_month = datetime(today.year, today.month, 1)

        # Truncate timestamp to hour and aggregate data for each hour
        dataset = super().get_queryset().filter(timestamp__gte=start_of_month).annotate(
            truncated_timestamp=TruncHour('timestamp')  # Truncate timestamp to hour
        ).values('devId', 'truncated_timestamp').annotate(
            state_of_charge_avg=Round(Avg('state_of_charge'), 2),
            flow_last_min_avg=Round(Avg('flow_last_min'), 2),
            invertor_power_avg=Round(Avg('invertor_power'), 2)
        ).order_by('truncated_timestamp')

        return dataset
    
    def get_cumulative_data_month(self):
        
        # cache_key = f"year_data_{cumulative}"
        # cached_data = cache.get(cache_key)

        # if cached_data is not None:
        #     print(f"We Have Cached Data Year")
        #     return cached_data  # Return cached result if available
        
        queryset = self.get_queryset()

        data = list(queryset.values())
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
        return cumulative_result
        
     
           


class YearManager(models.Manager):
    
    def get_queryset(self):
        # Get the start of the current year
        today = datetime.today()
        start_of_year = datetime(today.year, 1, 1)

        # Query the dataset, truncate timestamp to day, and aggregate data
        dataset = super().get_queryset().filter(timestamp__gte=start_of_year).annotate(
            truncated_timestamp=TruncHour('timestamp')  # Truncate timestamp to day/hour
        ).values('devId', 'truncated_timestamp').annotate(
            state_of_charge_avg=Round(Avg('state_of_charge'), 2),
            flow_last_min_avg=Round(Avg('flow_last_min'), 2),
            invertor_power_avg=Round(Avg('invertor_power'), 2)
        ).order_by('truncated_timestamp')

        return dataset
    
    
    def get_cumulative_data_year(self):
        
        # cache_key = f"year_data_{cumulative}"
        # cached_data = cache.get(cache_key)

        # if cached_data is not None:
        #     print(f"We Have Cached Data Year")
        #     return cached_data  # Return cached result if available
        
        queryset = self.get_queryset()

        data = list(queryset.values())
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
        return cumulative_result
        
    


class TodayManager(models.Manager):
    def get_queryset(self):
        today = datetime.now(timezone('Europe/Sofia')).date()
        tomorrow = today + timedelta(1)
        today_start = str(today)+'T'+'00:00:00Z'
        today_end = str(tomorrow)+'T'+'00:00:00Z'

        queryset = super().get_queryset().filter(timestamp__gt = today_start, timestamp__lt = today_end).order_by('timestamp')
        # Ensure there are no data below 0 and above 100
        queryset = queryset.annotate(
            adjusted_soc=Case(
                When(state_of_charge__lte=0, then=Value(0)),
                When(state_of_charge__gte=100, then=Value(100)),
                default=F('state_of_charge'),
                output_field=FloatField()
            )
        )
        return queryset
    
    def prepare_consistent_response(self, cumulative=None, devId=None):        
        
        queryset = self.get_queryset()
        if devId is not None:
            queryset = queryset.filter(devId=devId)
        data = list(queryset.values())
        if not data:
            return []
        # Convert data to pandas DataFrame
        df = pd.DataFrame(data)
        # Convert 'timestamp' field to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        df = df.loc[df.groupby(['devId', 'timestamp'])['state_of_charge'].idxmax()]


        # Set the timestamp as index for resampling
        df.set_index('timestamp', inplace=True)
        # Resample for each device separately (assuming there's a 'devId' field)
        resampled_data = []
        for dev_id in df['devId'].unique():
            df_device = df[df['devId'] == dev_id]

            df_device.drop(columns=['id'])

            # Resample to 1-minute intervals and interpolate missing data
            df_resampled = df_device.resample('1T').asfreq()

            df_resampled['state_of_charge'] = df_resampled['state_of_charge'].interpolate()
            df_resampled['flow_last_min'] = df_resampled['flow_last_min'].bfill()
            df_resampled['invertor_power'] = df_resampled['invertor_power'].bfill()

            # Add 'devId' column back
            df_resampled['devId'] = dev_id

            # Reset index to make 'timestamp' a column again
            df_resampled = df_resampled.reset_index()

            # Append to the resampled data list
            resampled_data.append(df_resampled)

        # Combine resampled data
        df_combined = pd.concat(resampled_data)
        # Sort by timestamp
        df_combined = df_combined.sort_values(by='timestamp')

        # Round numerical columns to 2 decimal places
        numeric_columns = ['invertor_power', 'state_of_charge', 'flow_last_min']  # Adjust based on your data fields
        df_combined[numeric_columns] = df_combined[numeric_columns].round(2)        
        

        if cumulative is not None:
            # Group by timestamp and calculate cumulative sum of state_of_charge
            df_cumulative = df_combined.groupby('timestamp').agg(
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
           
            return cumulative_result
        
        df_combined.fillna(0, inplace=True)
        resampled_result = df_combined.to_dict(orient='records')        
        return resampled_result
  

class DayAheadManager(models.Manager):

    def get_queryset(self) -> models.QuerySet:
        today = datetime.now(tz=pytz.UTC).date()   
        print(f"today start with UTC: {today}")
        today_start = str(today)+'T'+'00:00:00Z'        
        return super().get_queryset().filter(timestamp__gte=today_start).order_by('timestamp')

        
    
    def prepare_consistent_response_dam(self, cumulative=None, devId=None):

        queryset = self.get_queryset()
        if devId is not None:
            queryset=queryset.filter(devId=devId)
        data = list(queryset.values())
        if not data:
            return []
        # Convert data to pandas DataFrame
        df = pd.DataFrame(data)
        # Convert 'timestamp' field to datetime        
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        # Get the current time in the specified timezone
        # now = datetime.now(pytz.UTC) + timedelta(hours=2, minutes=45)       
        
        
        df.set_index('timestamp', inplace=True)
        # Resample for each device separately (assuming there's a 'devId' field)
        #df = df[df.index > now]  # Use df.index for the comparison

        resampled_data = []
        for dev_id in df['devId'].unique():
            df_device = df[df['devId'] == dev_id]

            # df_no_id = df_device.drop(columns=['id'])            
           
            df_resampled = df_device.resample('1T').asfreq()
            
             # Interpolate 'soc' and 'flow' columns
            df_resampled['soc'] = df_resampled['soc'].interpolate(method='linear')
            df_resampled['flow'] = df_resampled['flow'].bfill()

            # Divide the flow by 15 to have it per min
            df_resampled['flow'] = df_resampled['flow']/15

            # Backward fill 'invertor' column
            df_resampled['invertor'] = df_resampled['invertor'].bfill()

            # Add 'devId' column back
            df_resampled['devId'] = dev_id

            # Reset index to make 'timestamp' a column again
            df_resampled = df_resampled.reset_index()

            # Append to the resampled data list
            resampled_data.append(df_resampled)

        # Combine resampled data
        df_combined = pd.concat(resampled_data)
        # Sort by timestamp
        df_combined = df_combined.sort_values(by='timestamp')

        # Round numerical columns to 2 decimal places
        numeric_columns = ['invertor', 'soc', 'flow']  # Adjust based on your data fields        
        df_combined[numeric_columns] = df_combined[numeric_columns].round(2)

        if cumulative is not None:
            # Group by timestamp and calculate cumulative sum of state_of_charge
            df_cumulative = df_combined.groupby('timestamp').agg(
            cumulative_soc=('soc', 'sum'),
            cumulative_flow_last_min=('flow', 'sum'),
            cumulative_invertor_power=('invertor', 'sum')
            ).reset_index()
            # Round the cumulative sums to 2 decimal places
            df_cumulative['cumulative_soc'] = df_cumulative['cumulative_soc'].round(2)
            df_cumulative['cumulative_flow_last_min'] = df_cumulative['cumulative_flow_last_min'].round(2)
            df_cumulative['cumulative_invertor_power'] = df_cumulative['cumulative_invertor_power'].round(2)
            df_cumulative.fillna(0, inplace=True)
            # Convert back to a list of dictionaries
            cumulative_result = df_cumulative.to_dict(orient='records')
              
            return cumulative_result

        resampled_result = df_combined.drop(columns=['id'], errors='ignore').to_dict(orient='records')   
        
        return resampled_result

class CalculateRevenue(models.Manager):

    def get_queryset(self) -> models.QuerySet:
        today = datetime.now(tz=pytz.UTC).date()   
        print(f"today start with UTC: {today}")
        today_start = str(today)+'T'+'00:00:00Z'        
        return super().get_queryset().filter(timestamp__gte=today_start).order_by('timestamp')
    
    def revenue_calc(self, devId):
        # Get the current timestamp with timezone support
        today = datetime.now(tz=pytz.UTC).date()
        today_start = str(today)+'T'+'00:00:00Z'
        dam_schedule = self.get_queryset()  
        if devId:
            dam_schedule = self.get_queryset.filter(devId=devId)
        # Filter prices and forecasted prices from today onward
        price_dam = Price.objects.filter(timestamp__gte=today_start)
        

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

        # Group by devId and resample to 1-minute frequency with forward fill
        resampled_flow = (
            battery_df.groupby('devId', group_keys=False) 
            .resample('1T')
            .ffill()  # Forward fill missing values
            .reset_index()
        )
        price_resampled = (
            price_df.resample('1T')
            .ffill()
            .reset_index()
        )
        
        resampled_flow = resampled_flow.sort_values(by=['timestamp', 'devId']).reset_index(drop=True)
        aggregated_flow_df = resampled_flow.groupby("timestamp", as_index=False)["flow"].sum()

        merged_df = pd.merge(aggregated_flow_df, price_resampled, on='timestamp', how='left')
        
        merged_df['price'] = merged_df['price'].astype(float)

        merged_df['price_flow'] = merged_df['flow'] * merged_df['price']

        merged_df['revenue'] = merged_df['price_flow'].cumsum()

        merged_df['revenue'] = merged_df['revenue'].round(2)

        merged_df.dropna(axis=0, inplace=True)
        
        pd.set_option('display.max_rows', None)
        print(merged_df.iloc[:200])
        if not devId: 
            cache.set('accumulated_flow_price_data', merged_df[['timestamp', 'revenue']].to_dict(orient='records'), timeout=3600)
            return merged_df[['timestamp', 'revenue']].to_dict(orient='records')



       

   

class BatteryLiveStatus(models.Model):
    devId = models.CharField(default='batt-0001', max_length=20)
    timestamp = models.DateTimeField()
    state_of_charge = models.FloatField(default=0)
    flow_last_min = models.FloatField(default=0)
    invertor_power = models.FloatField(default=0)
    today = TodayManager()
    month = MonthManager()
    year = YearManager()  
    objects = models.Manager()


class BatterySchedule(models.Model):
    devId = models.CharField(default='batt1', max_length=20)
    timestamp = models.DateTimeField()
    dam = DayAheadManager()
    objects = models.Manager()   
    revenue = CalculateRevenue() 
    invertor = models.FloatField(default=0)
    soc = models.FloatField(default=0)
    flow = models.FloatField(default=0)

    class Meta:
        unique_together = ('devId', 'timestamp')


class YearAgg(models.Model):
    devId = models.CharField(default='batt-0001', max_length=20)
    timestamp = models.DateTimeField()
    state_of_charge = models.FloatField(default=0)
    flow_last_min = models.FloatField(default=0)
    invertor_power = models.FloatField(default=0)    

    class Meta:
        unique_together = ('devId', 'timestamp')


    
class CumulativeYear(models.Model):
   
    timestamp = models.DateTimeField()
    cumulative_soc = models.FloatField(default=0)
    cumulative_flow_last_min = models.FloatField(default=0)
    cumulative_invertor_power = models.FloatField(default=0)    


class Price(models.Model):
    timestamp = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')

    def __str__(self):
        return f"{self.timestamp}: {self.price} {self.currency}"
    
class ForecastedPrice(models.Model):
    timestamp = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')

    def __str__(self):
        return f"{self.timestamp}: {self.price} {self.currency}"
    
    