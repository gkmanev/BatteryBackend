from rest_framework import serializers
from .models import BatteryLiveStatus, BatterySchedule




class BatteryLiveSerializer(serializers.ModelSerializer):
    timestamp = serializers.SerializerMethodField()  # Use SerializerMethodField to rename

    class Meta:
        model = BatteryLiveStatus
        fields = ('devId', 'timestamp', 'state_of_charge', 'flow_last_min', 'invertor_power')

    def get_timestamp(self, obj):
        return obj.get('truncated_timestamp')  # Access the annotated field from the dictionary



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
    