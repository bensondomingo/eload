from django.urls import include, path

from rest_framework.routers import DefaultRouter

from profiles.api.views import (UserAPIViewSet, ProfileAPIViewSet,
                                ProfileListAPIView, ProfileRUAPIView,
                                SummaryCardAPIViewSet, CurrentUserAPIView)

router = DefaultRouter()
router.register('users', UserAPIViewSet, basename='users')
router.register('profiles', ProfileAPIViewSet, basename='profiles')
router.register('cards', SummaryCardAPIViewSet, basename='cards')


urlpatterns = [
    path('', include(router.urls)),
    path('current-user/', CurrentUserAPIView.as_view(), name='current-user'),
    # path('profiles/', ProfileListAPIView.as_view(), name='profiles-list'),
    # path('profiles/<str:user__username>/',
    #      ProfileRUAPIView.as_view(), name='profiles-detail'),
]
