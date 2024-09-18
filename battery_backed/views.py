from rest_framework import viewsets
from .models import BatteryLiveStatus, BatterySchedule
from .serializers import BatteryLiveSerializer,BatteryLiveSerializerToday, BatteryScheduleSerializer
from django.db.models import Case, When, Value, F, FloatField
from rest_framework.response import Response
from rest_framework.views import APIView


class StateViewSet(viewsets.ModelViewSet):

    queryset = BatteryLiveStatus.objects.all()   
    
    def get_serializer_class(self):
        # Determine if you're dealing with raw data or aggregated data
        date_range = self.request.query_params.get('date_range', None)
        if date_range == 'year' or date_range == 'month':
            return BatteryLiveSerializer  # Use the serializer for yearly aggregation (by day)
        else:
            return BatteryLiveSerializerToday
        
        

    def get_queryset(self):
        queryset = super().get_queryset()

        # Applying filters based on query parameters
        date_range = self.request.query_params.get('date_range', None)     
        dev_id = self.request.query_params.get('devId', None)

        if date_range:
            if date_range == 'today':
                queryset = BatteryLiveStatus.today.all()
            elif date_range == 'month':
                queryset = BatteryLiveStatus.month.all()
            else:
                queryset = BatteryLiveStatus.year.all()

        if dev_id:
            queryset = queryset.filter(devId=dev_id)

        # Adjust state_of_charge to be within 0-100 range in a single database operation
        queryset = queryset.annotate(
            adjusted_soc=Case(
                When(state_of_charge__lte=0, then=Value(0)),
                When(state_of_charge__gte=100, then=Value(100)),
                default=F('state_of_charge'),
                output_field=FloatField()
            )
        )

        return queryset


class ScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = BatteryScheduleSerializer
    queryset = BatterySchedule.objects.all().order_by('timestamp')
    def get_queryset(self):
        queryset = super().get_queryset()
        date_range = self.request.query_params.get('date_range', None)
        if date_range:
            if date_range == "dam":
                queryset = BatteryLiveStatus.month.all()        
        return queryset
