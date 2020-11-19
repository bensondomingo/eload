from rest_framework.serializers import ModelSerializer
from fcm.models import FCMDevice


class FCMDeviceSerializer(ModelSerializer):

    class Meta:
        model = FCMDevice
        fields = '__all__'
