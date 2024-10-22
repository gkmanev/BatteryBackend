from rest_framework import serializers
from .models import BatteryLiveStatus, BatterySchedule, YearAgg, CumulativeYear, Price




class BatteryLiveSerializer(serializers.ModelSerializer):
    timestamp = serializers.SerializerMethodField()  # Use SerializerMethodField to rename 'truncated_timestamp'
    state_of_charge = serializers.SerializerMethodField()
    flow_last_min = serializers.SerializerMethodField()
    invertor_power = serializers.SerializerMethodField()

    class Meta:
        model = BatteryLiveStatus
        fields = ('devId', 'timestamp', 'state_of_charge', 'flow_last_min', 'invertor_power')

    def get_timestamp(self, obj):
        # Access the annotated 'truncated_timestamp' field
        return obj.get('truncated_timestamp')

    def get_state_of_charge(self, obj):
        # Access the annotated 'state_of_charge_avg' field
        return obj.get('state_of_charge_avg')

    def get_flow_last_min(self, obj):
        # Access the annotated 'flow_last_min_avg' field
        return obj.get('flow_last_min_avg')

    def get_invertor_power(self, obj):
        # Access the annotated 'invertor_power_avg' field
        return obj.get('invertor_power_avg')



class BatteryLiveSerializerToday(serializers.ModelSerializer):
    timestamp = serializers.ReadOnlyField()  # Ensure the field is included

    class Meta:
        model = BatteryLiveStatus
        fields = ('devId', 'timestamp', 'state_of_charge', 'flow_last_min', 'invertor_power')



class BatteryScheduleSerializer(serializers.ModelSerializer):    
    
    class Meta:
        model = BatterySchedule
        fields = ('devId', 'timestamp', 'invertor','soc','flow')


class BatteryCumulativeSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    total_state_of_charge = serializers.FloatField()
    total_invertor_power = serializers.FloatField()
    total_flow_last_min = serializers.FloatField()
    


class ScheduleCumulativeSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    total_sched_soc = serializers.FloatField()
    total_sched_invertor = serializers.FloatField()
    total_sched_flow = serializers.FloatField()
    

class YearAggSerializer(serializers.ModelSerializer):    
    
    class Meta:
        model = YearAgg
        fields = ('devId', 'timestamp', 'invertor_power','state_of_charge','flow_last_min')


class CumulativeYearSerializer(serializers.ModelSerializer):    
    
    class Meta:
        model = CumulativeYear
        fields = ('timestamp', 'cumulative_invertor_power','cumulative_soc','cumulative_flow_last_min')


class PriceSerializer(serializers.ModelSerializer):    
    
    class Meta:
        model = Price
        fields = ('timestamp', 'price', 'currency')