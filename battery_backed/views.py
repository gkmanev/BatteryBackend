
import pandas as pd
from rest_framework import viewsets
from .models import BatteryLiveStatus, BatterySchedule, YearAgg, CumulativeYear
from .serializers import BatteryLiveSerializer,BatteryLiveSerializerToday, BatteryScheduleSerializer, BatteryCumulativeSerializer, ScheduleCumulativeSerializer, YearAggSerializer, CumulativeYearSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .tasks import task_forecast_schedule_populate





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
        cumulative = self.request.query_params.get('cumulative', None)
        
        # Handle date range filtering
        if date_range:
            if date_range == 'today':
                queryset = BatteryLiveStatus.today.all()
            elif date_range == 'month':               
                queryset = BatteryLiveStatus.month.all()
            elif date_range == 'year':
                queryset = BatteryLiveStatus.year.all()
        # Apply dev_id filter if provided
        if dev_id:
            queryset = queryset.filter(devId=dev_id)

        return queryset
    
    def list(self, request, *args, **kwargs):
        
        date_range = self.request.query_params.get('date_range', None)
        cumulative = self.request.query_params.get('cumulative', None)
        dev_id = self.request.query_params.get('devId', None) 

        # If it's today and cumulative is requested
        if date_range == 'today':
            if cumulative:
                # Fetch cumulative response directly from manager
                response = BatteryLiveStatus.today.prepare_consistent_response(cumulative)
                return Response(response, status=status.HTTP_200_OK)
            else:  
                if dev_id:
                    response = BatteryLiveStatus.today.prepare_consistent_response(devId=dev_id)                    
                else:              
                    response = BatteryLiveStatus.today.prepare_consistent_response()                
                return Response(response, status=status.HTTP_200_OK)      
     

            
        elif date_range == 'month':
            if cumulative is not None:
                response = BatteryLiveStatus.month.get_cumulative_data_month()
                return Response(response, status=status.HTTP_200_OK)
            else:                
                if dev_id:
                    response = BatteryLiveStatus.month.filter(devId=dev_id)     
                else:       
                    response = BatteryLiveStatus.month.all()
                serializer_class = self.get_serializer_class()
                serializer = serializer_class(response, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            

        elif date_range == 'year':
            if cumulative is not None:                
                response = BatteryLiveStatus.year.get_cumulative_data_year()
                return Response(response, status=status.HTTP_200_OK)
            else:
                if dev_id:
                    response = BatteryLiveStatus.year.filter(devId=dev_id)     
                else:       
                    response = BatteryLiveStatus.year.all()

                serializer_class = self.get_serializer_class()
                serializer = serializer_class(response, many=True)                
                return Response(serializer.data, status=status.HTTP_200_OK)
        

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
        dev_id = self.request.query_params.get('devId', None) 

        if date_range == "dam":           
            if cumulative is not None:
                response = BatterySchedule.dam.prepare_consistent_response_dam(cumulative)            
                return Response(response, status=status.HTTP_200_OK)
            else:
                if dev_id is not None:
                    response = BatterySchedule.dam.prepare_consistent_response_dam(devId=dev_id)
                else:
                    response = BatterySchedule.dam.prepare_consistent_response_dam() 
                return Response(response, status=status.HTTP_200_OK)   
        else:
            response = BatterySchedule.objects.all().order_by('timestamp')
            serializer_class = self.get_serializer_class()
            serializer = serializer_class(response, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)



class PopulateBatteryScheduleView(APIView):
    def post(self, request, *args, **kwargs):
        # Trigger the Celery task
        task = task_forecast_schedule_populate.delay()
        return Response({'message': 'Task started', 'task_id': task.id}, status=status.HTTP_202_ACCEPTED)





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




class AggregateYearDataView(APIView):

    def get(self, request, *args, **kwargs):        

        devId = self.request.query_params.get('devId', None)
        if devId:
            year_data = YearAgg.objects.filter(devId=devId)
        else:
            year_data = YearAgg.objects.all().order_by('timestamp')      
        serializer = YearAggSerializer(year_data, many=True)
        return Response(serializer.data)
    


class CumulativeYearDataView(APIView):

    def get(self, request, *args, **kwargs):        

        year_data = CumulativeYear.objects.all().order_by('timestamp')      
        serializer = CumulativeYearSerializer(year_data, many=True)
        return Response(serializer.data)