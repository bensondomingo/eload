from django.urls import path

from cphapp.api.views import (
    BuyOrderListAPIView, BuyOrderRetrieveUpdateAPIView,
    SellLoadOrderListAPIView, SellLoadOrderRetrieveUpdateAPIView,
    TransactionsListAPIView, TransactionsRetrieveUpdateAPIView)

urlpatterns = [
    path('transactions/', TransactionsListAPIView.as_view(),
         name='transactions-list'),
    path('transactions/<str:pk>/', TransactionsRetrieveUpdateAPIView.as_view(),
         name='transactions-detail'),
    path('loadorders/', SellLoadOrderListAPIView.as_view(),
         name='loadorders-list'),
    path('loadorders/<str:pk>/',
         SellLoadOrderRetrieveUpdateAPIView.as_view(),
         name='loadorders-detail'),
    path('buyorders/', BuyOrderListAPIView.as_view(), name='buyorders-list'),
    path('buyorders/<str:pk>/', BuyOrderRetrieveUpdateAPIView.as_view(),
         name='buyorders-detail')

]
