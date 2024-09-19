from django.db import models
from datetime import datetime, timedelta
from django.db.models import Avg
from django.db.models.functions import TruncDay, TruncHour, Round
from pytz import timezone



class MonthManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(
            truncated_timestamp=TruncHour('timestamp')  # Annotate with a unique name
        ).values(
            'devId', 'truncated_timestamp'
        ).annotate(
            state_of_charge=Round(Avg('state_of_charge'), 2),
            flow_last_min=Round(Avg('flow_last_min'), 2),
            invertor_power=Round(Avg('invertor_power'), 2)
        ).order_by('truncated_timestamp')



class YearManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(
            truncated_timestamp=TruncDay('timestamp')  # Annotate with a unique name
        ).values(
            'devId', 'truncated_timestamp'
        ).annotate(
            state_of_charge=Round(Avg('state_of_charge'), 2),
            flow_last_min=Round(Avg('flow_last_min'), 2),
            invertor_power=Round(Avg('invertor_power'), 2)
        ).order_by('truncated_timestamp')



class TodayManager(models.Manager):
    def get_queryset(self):
        today = datetime.now(timezone('Europe/Sofia')).date()
        tomorrow = today + timedelta(1)
        today_start = str(today)+'T'+'00:00:00Z'
        today_end = str(tomorrow)+'T'+'00:00:00Z'
        return super().get_queryset().filter(timestamp__gt = today_start, timestamp__lt = today_end).order_by('timestamp')

class DayAheadManager(models.Manager):
    def get_queryset(self) -> models.QuerySet:
        today = datetime.now(timezone('Europe/Sofia')).date()
        tomorrow = today + timedelta(1)        
        timeframe_start = str(tomorrow)+'T'+'00:00:00Z'      

        # Fetch the last entry before the timeframe start needed for init SoC
        last_before_queryset = super().get_queryset().filter(
            timestamp__lt=timeframe_start  # Only fetch data points strictly before
        ).order_by('-timestamp').first()

        # Initialize SoC from the last data point before timeframe_start
        soc = last_before_queryset.soc if last_before_queryset else 0

        # Fetch the main filtered queryset (after timeframe_start)
        queryset = super().get_queryset().filter(
            timestamp__gte=timeframe_start  # Only fetch data points on or after
        ).order_by('timestamp')

        # Calculate SoC for each entry in the queryset
        for obj in queryset:
            invertor = obj.invertor  # Assuming 'invertor' is a field in the model
            flow = invertor / 60 * 15  # Calculate flow
            
            soc += flow  # Add flow to SoC

            # Update the object with SoC and Flow
            obj.soc = soc  # Assuming 'soc' is a field in the model
            obj.flow = flow
            obj.save()  # Save the updated object

        return queryset


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

    
    