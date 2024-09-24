from rest_framework import viewsets
from .models import BatteryLiveStatus, BatterySchedule
from .serializers import BatteryLiveSerializer,BatteryLiveSerializerToday, BatteryScheduleSerializer, BatteryCumulativeSerializer, ScheduleCumulativeSerializer
from django.db.models import Case, When, Value, F, FloatField
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
    
    def list(self, request, *args, **kwargs):

        date_range = self.request.query_params.get('date_range', 'false').lower() == 'true'
        cumulative = self.request.query_params.get('cumulative', 'false').lower() == 'true'

        if date_range == 'today' or date_range == 'dam':
            
            queryset = self.get_queryset() 
            # Convert queryset to a list of dictionaries
            data = list(queryset.values())
            if not data:
                return Response([], status=status.HTTP_200_OK)

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

            if cumulative:
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
                return Response(cumulative_result, status=status.HTTP_200_OK)

            # Convert back to a list of dictionaries
            resampled_result = df_combined.to_dict(orient='records')
            serializer = self.get_serializer(resampled_result, many=True)
            # Return a custom response
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        else:
            if cumulative:
                if date_range == 'month': 
                    queryset = BatteryLiveStatus.month.get_cumulative_data_month()                  
                    return Response(serializer.queryset, status=status.HTTP_200_OK)
                
               
                



   


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




