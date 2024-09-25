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
        

    def get_queryset(self):

        queryset = super().get_queryset()
        
        # Applying filters based on query parameters
        date_range = self.request.query_params.get('date_range', None)
        dev_id = self.request.query_params.get('devId', None)

        # Apply dev_id filter if provided
        if dev_id:
            queryset = queryset.filter(devId=dev_id)
        
        # Handle date range filtering
        if date_range:
            if date_range == 'today':
                queryset = BatteryLiveStatus.today.all()
            elif date_range == 'month':
                queryset = BatteryLiveStatus.month.all()
            elif date_range == 'year':
                queryset = BatteryLiveStatus.year.all()

        return queryset
    
    def list(self, request, *args, **kwargs):
        
        date_range = self.request.query_params.get('date_range', None)
        cumulative = self.request.query_params.get('cumulative', None)

        # If it's today and cumulative is requested
        if date_range == 'today' and cumulative is not None:
            # Fetch cumulative response directly from manager
            response = BatteryLiveStatus.today.prepare_consistent_response(cumulative=True)
            return Response(response, status=status.HTTP_200_OK)

        # Otherwise, use the standard queryset and serialization
        return super().list(request, *args, **kwargs)
    
   
                
               
                



   


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
        queryset = self.get_queryset() 
        # Convert queryset to a list of dictionaries
        data = list(queryset.values())
        if not data:
            return queryset

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
        numeric_columns = ['invertor', 'soc', 'flow']  # Adjust based on your data fields
        df_combined[numeric_columns] = df_combined[numeric_columns].round(2)

        # Convert back to a list of dictionaries
        resampled_result = df_combined.to_dict(orient='records')
        serializer = self.get_serializer(resampled_result, many=True)
        # Return a custom response
        return Response(serializer.data, status=status.HTTP_200_OK)



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




