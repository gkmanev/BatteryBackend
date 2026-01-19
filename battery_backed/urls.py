from django.urls import path
from rest_framework import routers
from .views import StateViewSet, ScheduleViewSet, BatteryCumulativeDataView, ScheduleCumulativeDataView, PopulateBatteryScheduleView, AggregateYearDataView, CumulativeYearDataView, PriceView, ForecastedPriceView, AccumulatedFlowPriceView

router = routers.DefaultRouter()
router.register(r'state_of_charge', StateViewSet)
router.register(r'schedule', ScheduleViewSet)

urlpatterns = [
    path('battery-cumulative/', BatteryCumulativeDataView.as_view(), name='battery-cumulative'),
    path('schedule-cumulative/', ScheduleCumulativeDataView.as_view(), name='schedule-cumulative'), 
    path('populate-schedule/', PopulateBatteryScheduleView.as_view(), name='populate_schedule'),   
    path('year-agg/', AggregateYearDataView.as_view(), name='agg-year'),
    path('year-sum/', CumulativeYearDataView.as_view(), name='sum-year'),
    path('price/', PriceView.as_view(), name='price'),
    path('forecasted_price/', ForecastedPriceView.as_view(), name='forecasted_price'),
    path('accumulated-flow-price/', AccumulatedFlowPriceView.as_view(), name='accumulated-flow-price'),
]
    
urlpatterns += router.urls
