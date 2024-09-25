from django.db import models
from datetime import datetime, timedelta
from django.db.models import Avg, Sum, Case, When, Value, F, FloatField
from django.db.models.functions import TruncDay, TruncHour, Round

from pytz import timezone
import pandas as pd


class MonthManager(models.Manager):
    def get_queryset(self):
        
        queryset = super().get_queryset().annotate(
            truncated_timestamp=TruncHour('timestamp')  # Annotate with a unique name
        ).values(
            'devId', 'truncated_timestamp'
        ).annotate(
            state_of_charge=Round(Avg('state_of_charge'), 2),
            flow_last_min=Round(Avg('flow_last_min'), 2),
            invertor_power=Round(Avg('invertor_power'), 2)
        ).order_by('truncated_timestamp')

        queryset = queryset.annotate(
            adjusted_soc=Case(
                When(state_of_charge__lte=0, then=Value(0)),
                When(state_of_charge__gte=100, then=Value(100)),
                default=F('state_of_charge'),
                output_field=FloatField()
            )
        )
        return queryset
    
    def get_cumulative_data_month(self):
    # Get the aggregated monthly data
        aggregated_data = self.get_queryset()  # This contains avg values
        df = pd.DataFrame(aggregated_data)

        # Calculate cumulative sums on the average values
        df['cumulative_soc'] = df['state_of_charge'].cumsum()
        df['cumulative_flow_last_min'] = df['flow_last_min'].cumsum()
        df['cumulative_invertor_power'] = df['invertor_power'].cumsum()

        # Select the relevant columns
        cumulative_result = df[['truncated_timestamp', 'cumulative_soc', 'cumulative_flow_last_min', 'cumulative_invertor_power']]

        # Round the cumulative sums to 2 decimal places
        cumulative_result = cumulative_result.round(2)

        # Convert back to a list of dictionaries
        return cumulative_result.to_dict(orient='records')


class YearManager(models.Manager):
    def get_queryset(self):

        queryset = super().get_queryset().annotate(
            truncated_timestamp=TruncDay('timestamp')  # Annotate with a unique name
        ).values(
            'devId', 'truncated_timestamp'
        ).annotate(
            state_of_charge=Round(Avg('state_of_charge'), 2),
            flow_last_min=Round(Avg('flow_last_min'), 2),
            invertor_power=Round(Avg('invertor_power'), 2)
        ).order_by('truncated_timestamp')
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
    
    def get_cumulative_data_year(self):
        # Get today's data
        queryset = self.get_queryset()
        
        # Aggregate cumulative data
        return queryset.values('timestamp').annotate(
            total_state_of_charge=Round(Sum('state_of_charge'), 2),
            total_invertor_power=Round(Sum('invertor_power'), 2),
            total_flow_last_min=Round(Sum('flow_last_min'), 2)
        )





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

            # Resample to 1-minute intervals and interpolate missing data
            df_resampled = df_device.resample('1T').interpolate()

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
            
            # Convert back to a list of dictionaries
            cumulative_result = df_cumulative.to_dict(orient='records')
            return cumulative_result

        resampled_result = df_combined.to_dict(orient='records')
        return resampled_result
  

class DayAheadManager(models.Manager):

    def get_queryset(self) -> models.QuerySet:
        today = datetime.now(timezone('Europe/Sofia')).date()         
        timeframe_start = str(today)+'T'+'00:00:00Z'     
        return super().get_queryset().filter(timestamp__gte=timeframe_start).order_by('timestamp')
    
    def prepare_consistent_response_dam(self, cumulative=False):        
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

            df_no_id = df_device.drop(columns=['id'])
            # Resample to 1-minute intervals and interpolate missing data
            df_resampled = df_device.resample('1T').interpolate()

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
        

        resampled_result = df_combined.drop(columns=['id'], errors='ignore').to_dict(orient='records')
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

    
