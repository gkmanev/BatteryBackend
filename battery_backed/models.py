from django.db import models
from datetime import datetime, timedelta
from django.db.models import Avg, Sum, Case, When, Value, F, FloatField
from django.db.models.functions import TruncDay, TruncHour, Round
from pytz import timezone
import pandas as pd
import pytz
from django.core.cache import cache




class MonthManager(models.Manager):
    
    def get_queryset(self):        
        return super().get_queryset()
    
    def get_cumulative_data_month(self, cumulative=None):

        cache_key = f"month_data_{cumulative}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print(f"We Have Cached Data Month")
            return cached_data  # Return cached result if available


       # Access the raw model's manager instead of the aggregated queryset
        queryset = self.get_queryset()

        data = list(queryset.values())
        if not data:
            return []
        
        df = pd.DataFrame(data)
        # Convert 'timestamp' field to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Group by 'devId' and 'timestamp', aggregating to handle duplicates
        df = df.groupby(['devId', 'timestamp']).agg({
            'state_of_charge': 'mean',  # Adjust the aggregation as needed
            'flow_last_min': 'mean',
            'invertor_power': 'mean'
        }).reset_index()

        # Set the timestamp as index for resampling
        df.set_index('timestamp', inplace=True)
        
        # Resample for each device separately
        resampled_data = []
        for dev_id in df['devId'].unique():
            df_device = df[df['devId'] == dev_id]

            # Resample to 1-hour intervals and interpolate missing data
            df_resampled = df_device.resample('1H').interpolate()

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
        df_combined.fillna(0, inplace=True)
        resampled_result = df_combined.to_dict(orient='records')

        cache.set(cache_key, resampled_result, timeout=60 * 15)  # Cache for 15 minutes   
        
        # Check if cumulative is requested
        if cumulative:
            # Calculate cumulative sums across all devIds for each timestamp
            df_cumulative = df_combined.groupby('timestamp').agg({
                'state_of_charge': 'sum',
                'flow_last_min': 'sum',
                'invertor_power': 'sum'
            }).reset_index()

            # Optionally, add devId as a representative (you could choose the first or leave it out)
            df_cumulative['devId'] = 'all'  # Indicate this is the cumulative data

            # Rename cumulative columns with the specified prefix
            df_cumulative.rename(columns={
                'state_of_charge': 'cumulative_state_of_charge',
                'flow_last_min': 'cumulative_flow_last_min',
                'invertor_power': 'cumulative_invertor_power'
            }, inplace=True)
            
            # Round numerical columns to 2 decimal places
            numeric_columns = ['cumulative_invertor_power', 'cumulative_state_of_charge', 'cumulative_flow_last_min']
            df_cumulative[numeric_columns] = df_cumulative[numeric_columns].round(2)
            df_cumulative.fillna(0, inplace=True)
            cumulative_result = df_cumulative.to_dict(orient='records')
            cache.set(cache_key, cumulative_result, timeout=60 * 15)  # Cache for 15 minutes
            return cumulative_result   
        
        return resampled_result

        


class YearManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()
    
    
    # def get_cumulative_data_year(self, cumulative=None):
        
    #     cache_key = f"year_data_{cumulative}"
    #     cached_data = cache.get(cache_key)

    #     if cached_data is not None:
    #         print(f"We Have Cached Data Year")
    #         return cached_data  # Return cached result if available
        
    #     queryset = self.get_queryset()

    #     data = list(queryset.values())
    #     if not data:
    #         return []
        
    #     df = pd.DataFrame(data)
    #     # Convert 'timestamp' field to datetime
    #     df['timestamp'] = pd.to_datetime(df['timestamp'])
        
    #     # Group by 'devId' and 'timestamp', aggregating to handle duplicates
    #     df = df.groupby(['devId', 'timestamp']).agg({
    #         'state_of_charge': 'mean',  # Adjust the aggregation as needed
    #         'flow_last_min': 'mean',
    #         'invertor_power': 'mean'
    #     }).reset_index()

    #     # Set the timestamp as index for resampling
    #     df.set_index('timestamp', inplace=True)
        
    #     # Resample for each device separately
    #     resampled_data = []
    #     for dev_id in df['devId'].unique():
    #         df_device = df[df['devId'] == dev_id]

    #         # Resample to 1-hour intervals and interpolate missing data
    #         df_resampled = df_device.resample('1D').interpolate()

    #         # Add 'devId' column back
    #         df_resampled['devId'] = dev_id

    #         # Reset index to make 'timestamp' a column again
    #         df_resampled = df_resampled.reset_index()

    #         # Append to the resampled data list
    #         resampled_data.append(df_resampled)

    #     # Combine resampled data
    #     df_combined = pd.concat(resampled_data)
    #     # Sort by timestamp
    #     df_combined = df_combined.sort_values(by='timestamp')

    #     # Round numerical columns to 2 decimal places
    #     numeric_columns = ['invertor_power', 'state_of_charge', 'flow_last_min']  # Adjust based on your data fields
    #     df_combined[numeric_columns] = df_combined[numeric_columns].round(2)   
    #     df_combined.fillna(0, inplace=True)        
    #     resampled_result = df_combined.to_dict(orient='records')
    #     cache.set(cache_key, resampled_result, timeout=60 * 15)  # Cache for 15 minutes   
        
    #     # Check if cumulative is requested
    #     if cumulative:
    #         # Calculate cumulative sums across all devIds for each timestamp
    #         df_cumulative = df_combined.groupby('timestamp').agg({
    #             'state_of_charge': 'sum',
    #             'flow_last_min': 'sum',
    #             'invertor_power': 'sum'
    #         }).reset_index()

    #         # Optionally, add devId as a representative (you could choose the first or leave it out)
    #         df_cumulative['devId'] = 'all'  # Indicate this is the cumulative data

    #         # Rename cumulative columns with the specified prefix
    #         df_cumulative.rename(columns={
    #             'state_of_charge': 'cumulative_state_of_charge',
    #             'flow_last_min': 'cumulative_flow_last_min',
    #             'invertor_power': 'cumulative_invertor_power'
    #         }, inplace=True)
            
    #         # Round numerical columns to 2 decimal places
    #         numeric_columns = ['cumulative_invertor_power', 'cumulative_state_of_charge', 'cumulative_flow_last_min']
    #         df_cumulative[numeric_columns] = df_cumulative[numeric_columns].round(2)
    #         df_cumulative.fillna(0, inplace=True)
    #         cumulative_result = df_cumulative.to_dict(orient='records')
    #         cache.set(cache_key, cumulative_result, timeout=60 * 15)  # Cache for 15 minutes   
    #         return cumulative_result
        
    #     return resampled_result



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
    
    def prepare_consistent_response(self, cumulative=None):

        cache_key = f"today_data_{cumulative}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print(f"We Have Cached Data")
            return cached_data  # Return cached result if available
        
        queryset = self.get_queryset()
        data = list(queryset.values())
        if not data:
            return []
        # Convert data to pandas DataFrame
        df = pd.DataFrame(data)
        # Convert 'timestamp' field to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
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
            cache.set(cache_key, cumulative_result, timeout=60 * 15)  # Cache for 15 minutes   
            return cumulative_result
        
        df_combined.fillna(0, inplace=True)
        resampled_result = df_combined.to_dict(orient='records')
        cache.set(cache_key, resampled_result, timeout=60 * 15)  # Cache for 15 minutes   
        return resampled_result
  

class DayAheadManager(models.Manager):

    def get_queryset(self) -> models.QuerySet:
        today = datetime.now().date()   
        today_start = str(today)+'T'+'00:00:00Z'        
        return super().get_queryset().filter(timestamp__gte=today_start).order_by('timestamp')
    
    def prepare_consistent_response_dam(self, cumulative=None):   

        cache_key = f"dam_data_{cumulative}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            print(f"We Have Cached Data DAM")
            return cached_data  # Return cached result if available

        queryset = self.get_queryset()
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
            df_resampled['soc'] = df_resampled['soc'].interpolate()
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
            cache.set(cache_key, cumulative_result, timeout=60 * 15)  # Cache for 15 minutes    
            return cumulative_result

        resampled_result = df_combined.drop(columns=['id'], errors='ignore').to_dict(orient='records')   
        cache.set(cache_key, resampled_result, timeout=60 * 15)  # Cache for 15 minutes         
        return resampled_result
   

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
    invertor = models.FloatField(default=0)
    soc = models.FloatField(default=0)
    flow = models.FloatField(default=0)

    
