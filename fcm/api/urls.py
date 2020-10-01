from django.urls import include, path
from rest_framework.routers import DefaultRouter

from fcm.api.views import FCMConfigRetrieveAPIView, FCMDeviceAPIViewSet

router = DefaultRouter()
router.register('fcmdevices', FCMDeviceAPIViewSet, basename='fcmdevices')

urlpatterns = [
    path('', include(router.urls)),
    path('fcm-config/', FCMConfigRetrieveAPIView.as_view(), name='fcm-config')
]
