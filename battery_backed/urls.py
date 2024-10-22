from django.urls import path
from rest_framework import routers
from .views import StateViewSet, ScheduleViewSet, BatteryCumulativeDataView, ScheduleCumulativeDataView, PopulateBatteryScheduleView, AggregateYearDataView, CumulativeYearDataView, PriceView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = routers.DefaultRouter()
router.register(r'state_of_charge', StateViewSet)
router.register(r'schedule', ScheduleViewSet)

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),    
    path('battery-cumulative/', BatteryCumulativeDataView.as_view(), name='battery-cumulative'),
    path('schedule-cumulative/', ScheduleCumulativeDataView.as_view(), name='schedule-cumulative'), 
    path('populate-schedule/', PopulateBatteryScheduleView.as_view(), name='populate_schedule'),   
    path('year-agg/', AggregateYearDataView.as_view(), name='agg-year'),
    path('year-sum/', CumulativeYearDataView.as_view(), name='sum-year'),
    path('price/', PriceView.as_view(), name='price'),
    
]

urlpatterns += router.urls