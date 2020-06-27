from django.urls import path

from cphapp.api.views import (
    TransactionsListAPIView, OrderListAPIView)

urlpatterns = [
    path('transactions/', TransactionsListAPIView.as_view(),
         name='transactions-list'),
    path('orders/', OrderListAPIView.as_view(),
         name='loadorders-list')
]
