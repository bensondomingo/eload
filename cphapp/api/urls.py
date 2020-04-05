from django.urls import path

from cphapp.api.views import TransactionsAPIView, TransactionsInitDBAPIView

urlpatterns = [
    path('transactions/', TransactionsAPIView.as_view(), name='transactions-list'),
    path('transactions-init/', TransactionsInitDBAPIView.as_view(),
         name='transactions-initdb')
]
