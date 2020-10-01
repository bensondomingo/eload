from django.conf import settings
from rest_framework import status
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from fcm.models import FCMDevice
from fcm.api.serializers import FCMDeviceSerializer
from fcm.tasks import fcm_check_valid_tokens


class FCMConfigRetrieveAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        fcm_config = settings.FCM_CONFIG
        return Response(data=fcm_config, status=status.HTTP_200_OK)


class FCMDeviceAPIViewSet(viewsets.GenericViewSet,
                          mixins.ListModelMixin,
                          mixins.CreateModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.DestroyModelMixin):

    queryset = FCMDevice.objects.all()
    serializer_class = FCMDeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user.profile)

    def create(self, request, *args, **kwargs):

        token = request.data.get('token')
        owner = request.user.profile

        try:
            obj = FCMDevice.objects.get(token=token, owner=owner)
            status_code = status.HTTP_200_OK
        except FCMDevice.DoesNotExist:
            serializer = FCMDeviceSerializer(
                data={'token': token, 'owner': owner.id})
            if not serializer.is_valid():
                raise ValidationError(serializer.error_messages)
            obj = serializer.create(serializer.validated_data)
            status_code = status.HTTP_201_CREATED

        # Launch FCMToken-checking task
        fcm_check_valid_tokens.apply_async(kwargs={'owner_id': owner.id})

        serializer = FCMDeviceSerializer(obj)
        return Response(data=serializer.data, status=status_code)
