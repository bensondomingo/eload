from django.contrib.auth import get_user_model

from rest_framework import generics
from rest_framework import mixins
from rest_framework import permissions
from rest_framework import viewsets
from rest_framework import filters

from rest_framework.views import APIView
from rest_framework.response import Response

from profiles.models import Profile, SummaryCard
from profiles.api.permissions import IsOwnProfileOrReadOnly
from profiles.api.serializers import ProfileSerializer
# from profiles.api.serializers import ProfileAvatarSerializer
from profiles.api.serializers import UserSerializer
from profiles.api.serializers import SummaryCardSerializer


USER_MODEL = get_user_model()


class UserAPIViewSet(viewsets.GenericViewSet,
                     mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin):

    queryset = USER_MODEL.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'is_active']
    ordering_fields = ['name', 'amount_planned']
    lookup_field = 'username'

    def get_queryset(self):
        return USER_MODEL.objects.exclude(is_superuser=True)


class CurrentUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        serializer = UserSerializer(instance=request.user)
        return Response(serializer.data)


class ProfileAPIViewSet(viewsets.GenericViewSet,
                        mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.UpdateModelMixin):

    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnProfileOrReadOnly]
    lookup_field = 'user__username'

    def get_queryset(self):
        return super().get_queryset().exclude(devices=None)

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ProfileListAPIView(generics.ListAPIView):

    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProfileRUAPIView(generics.RetrieveUpdateAPIView):

    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnProfileOrReadOnly]
    lookup_field = 'user__username'


class SummaryCardAPIViewSet(viewsets.GenericViewSet,
                            mixins.ListModelMixin,
                            mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            mixins.DestroyModelMixin):

    queryset = SummaryCard.objects.all()
    serializer_class = SummaryCardSerializer
    permission_classes = [permissions.IsAuthenticated]
