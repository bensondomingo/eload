from django.urls import include, path
from rest_framework.routers import DefaultRouter

from cphapp.api.views import ProductAPIView, TransactionAPIViewset

router = DefaultRouter()
router.register('transactions', TransactionAPIViewset, basename='transactions')

urlpatterns = [
    path('', include(router.urls)),
    path('buy-product/', ProductAPIView.as_view(), name='buy-product')
    # path('payout-outlets/<slug:outlet_id>/',
    #      PayoutOutletAPIView.as_view(), name='payout-outlets-detail')
]
