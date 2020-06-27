from django.urls import include, path

from rest_framework.routers import DefaultRouter

from profiles.api.views import UserAPIViewSet, ProfileAPIViewSet
from profiles.api.views import ProfileListAPIView, ProfileRUAPIView
from profiles.api.views import CurrentUser

router = DefaultRouter()
router.register('users', UserAPIViewSet, basename='users')
router.register('profiles', ProfileAPIViewSet, basename='profiles')


urlpatterns = [
    path('', include(router.urls)),
    path('user/', CurrentUser.as_view(), name='current-user'),
    # path('profiles/', ProfileListAPIView.as_view(), name='profiles-list'),
    # path('profiles/<str:user__username>/',
    #      ProfileRUAPIView.as_view(), name='profiles-detail'),
]
