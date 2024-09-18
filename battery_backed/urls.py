from django.urls import path
from rest_framework import routers
from .views import StateViewSet, ScheduleViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = routers.DefaultRouter()
router.register(r'state_of_charge', StateViewSet)
router.register(r'schedule', ScheduleViewSet)

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
]

urlpatterns += router.urls