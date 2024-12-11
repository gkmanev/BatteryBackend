
import pandas as pd
from rest_framework import viewsets
from .models import BatteryLiveStatus, BatterySchedule, YearAgg, CumulativeYear, Price, ForecastedPrice
from .serializers import BatteryLiveSerializer,BatteryLiveSerializerToday, BatteryScheduleSerializer, BatteryCumulativeSerializer, ScheduleCumulativeSerializer, YearAggSerializer, CumulativeYearSerializer, PriceSerializer, ForecastedPriceSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from datetime import datetime, timedelta
from .tasks import task_forecast_schedule_populate, task_cumulaticve_revenue
from django.utils import timezone
from pytz import timezone as pytz_timezone
from django.core.cache import cache




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
                print(queryset)
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
        date_range = self.request.query_params.get('date_range', None)
        today = datetime.today()
        start_of_month = datetime(today.year, today.month, 1)

        if devId:
            if date_range == 'month':
                data = YearAgg.objects.filter(devId=devId, timestamp__gte=start_of_month).order_by('timestamp')
            else:
                data = YearAgg.objects.filter(devId=devId).order_by('timestamp')
        else:
            if date_range == 'month':
                data = YearAgg.objects.filter(timestamp__gte=start_of_month).order_by('timestamp')
            else:
                data = YearAgg.objects.all().order_by('timestamp')      
        serializer = YearAggSerializer(data, many=True)
        return Response(serializer.data)
    


class CumulativeYearDataView(APIView):

    def get(self, request, *args, **kwargs):        
        date_range = self.request.query_params.get('date_range', None)
        today = datetime.today()
        start_of_month = datetime(today.year, today.month, 1)
        
        if date_range == 'month':
            data = CumulativeYear.objects.filter(timestamp__gte=start_of_month).order_by('timestamp')
        else:
            data = CumulativeYear.objects.all().order_by('timestamp')  

        serializer = CumulativeYearSerializer(data, many=True)
        return Response(serializer.data)
    
    
class PriceView(APIView):

    def get(self, request, *args, **kwargs):        
        date_range = self.request.query_params.get('date_range', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)

        user_timezone = pytz_timezone("Europe/Warsaw") 
        today = timezone.now().astimezone(user_timezone).replace(hour=0, minute=0, second=0, microsecond=0)
        
        if date_range == 'today':
            data = Price.objects.filter(timestamp__gte=today, timestamp__lte=today+timedelta(days=1)).order_by('timestamp')
        elif start_date and end_date:
            data = Price.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date).order_by('timestamp')
        elif date_range == 'dam':
            data = Price.objects.filter(timestamp__gte=today+timedelta(days=1)).order_by('timestamp')

        else:
            data = Price.objects.all().order_by('timestamp')  

        serializer = PriceSerializer(data, many=True)
        return Response(serializer.data)
    
class ForecastedPriceView(APIView):

    def get(self, request, *args, **kwargs):        
        date_range = self.request.query_params.get('date_range', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)

        user_timezone = pytz_timezone("Europe/Warsaw") 
        today = timezone.now().astimezone(user_timezone).replace(hour=0, minute=0, second=0, microsecond=0)
        
        if date_range == 'today':
            data = ForecastedPrice.objects.filter(timestamp__gte=today, timestamp__lte=today+timedelta(days=1)).order_by('timestamp')
        elif start_date and end_date:
            data = ForecastedPrice.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date).order_by('timestamp')
        elif date_range == 'dam':
            data = ForecastedPrice.objects.filter(timestamp__gte=today+timedelta(days=1)).order_by('timestamp')

        else:
            data = ForecastedPrice.objects.all().order_by('timestamp')  

        serializer = ForecastedPriceSerializer(data, many=True)
        return Response(serializer.data)
    

class AccumulatedFlowPriceView(APIView):
    def get(self, request, format=None):
        # Fetch the processed data from Redis (or your database)
        accumulated_flow_price_data = cache.get('accumulated_flow_price_data')
        
        if accumulated_flow_price_data:
            return Response(accumulated_flow_price_data, status=status.HTTP_200_OK)
        else:            
            return Response({"detail": "Data not available or expired."}, status=status.HTTP_404_NOT_FOUND)