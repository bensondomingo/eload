from django.urls import include, path

from rest_framework.routers import DefaultRouter

from profiles.api.views import UserAPIViewSet, ProfileAPIViewSet
from profiles.api.views import ProfileListAPIView, ProfileRUAPIView

router = DefaultRouter()
router.register('users', UserAPIViewSet, basename='users')
router.register('profiles', ProfileAPIViewSet, basename='profiles')


urlpatterns = [
    path('', include(router.urls)),
    # path('profiles/', ProfileListAPIView.as_view(), name='profiles-list'),
    # path('profiles/<str:user__username>/',
    #      ProfileRUAPIView.as_view(), name='profiles-detail'),
]
