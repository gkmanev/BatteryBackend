from rest_framework import viewsets
from .models import BatteryLiveStatus, BatterySchedule
from .serializers import BatteryLiveSerializer,BatteryLiveSerializerToday, BatteryScheduleSerializer, BatteryCumulativeSerializer, ScheduleCumulativeSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import pandas as pd



class StateViewSet(viewsets.ModelViewSet):

    queryset = BatteryLiveStatus.objects.all()   
    
    def get_serializer_class(self):
        # Determine if you're dealing with raw data or aggregated data
        date_range = self.request.query_params.get('date_range', None)
        if date_range == 'year' or date_range == 'month':
            return BatteryLiveSerializer  # Use the serializer for yearly aggregation (by day)
        else:
            return BatteryLiveSerializerToday 

    
    
    def list(self, request, *args, **kwargs):
        
        date_range = self.request.query_params.get('date_range', None)
        cumulative = self.request.query_params.get('cumulative', None)

        # If it's today and cumulative is requested
        if date_range == 'today':
            if cumulative:
                # Fetch cumulative response directly from manager
                response = BatteryLiveStatus.today.prepare_consistent_response(cumulative)
                return Response(response, status=status.HTTP_200_OK)
            else:
                response = BatteryLiveStatus.today.prepare_consistent_response(cumulative)
                return Response(response, status=status.HTTP_200_OK)
        # Handle month with cumulative or non-cumulative response
        elif date_range == 'month':
            if cumulative:
                pass
            else:
                queryset = BatteryLiveStatus.month.all()
                serializer_class = self.get_serializer_class()  # Retrieve the serializer class
                serializer = serializer_class(queryset, many=True)  # Instantiate the serializer
                response = serializer.data
            return Response(response, status=status.HTTP_200_OK)

        # Handle year with cumulative or non-cumulative response
        elif date_range == 'year':
            if cumulative:
                pass
            else:
                queryset = BatteryLiveStatus.year.all()
                serializer_class = self.get_serializer_class()  # Retrieve the serializer class
                serializer = serializer_class(queryset, many=True)  # Instantiate the serializer
                response = serializer.data
            return Response(response, status=status.HTTP_200_OK)
        
        return super().list(request, *args, **kwargs)
    
    
#DAM             
class ScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = BatteryScheduleSerializer
    queryset = BatterySchedule.objects.all().order_by('timestamp')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        date_range = self.request.query_params.get('date_range', None)
        if date_range:
            if date_range == "dam":
                queryset = BatterySchedule.dam.all()
        return queryset             
        
        
    def list(self, request, *args, **kwargs):
        date_range = self.request.query_params.get('date_range', None)
        cumulative = self.request.query_params.get('cumulative', None)
        if date_range == "dam":
            print(f"CUMULATIVE PARM:{cumulative}")
            if cumulative is not None:
                response = BatterySchedule.dam.prepare_consistent_response_dam(cumulative)            
                return Response(response, status=status.HTTP_200_OK)
            else:
                response = BatterySchedule.dam.prepare_consistent_response_dam(cumulative) 
                return Response(response, status=status.HTTP_200_OK)     


# Bellow is not needed

class BatteryCumulativeDataView(APIView):
    def get(self, request, *args, **kwargs):
        cumulative_data = None
        date_range = self.request.query_params.get('date_range', None)
        if date_range:
            if date_range == 'today':
                cumulative_data = BatteryLiveStatus.today.get_cumulative_data_today()
            elif date_range == 'month':
                cumulative_data = BatteryLiveStatus.month.get_cumulative_data_month()
            else:
                cumulative_data = BatteryLiveStatus.year.get_cumulative_data_year()
        serializer = BatteryCumulativeSerializer(cumulative_data, many=True)
        return Response(serializer.data)


class ScheduleCumulativeDataView(APIView):

    def get(self, request, *args, **kwargs):
        cumulative_data = None
        date_range = self.request.query_params.get('date_range', None)
        if date_range:
            if date_range == 'dam':
                cumulative_data = BatterySchedule.dam.get_cumulative_data_dam()            
        serializer = BatteryCumulativeSerializer(cumulative_data, many=True)
        return Response(serializer.data)




