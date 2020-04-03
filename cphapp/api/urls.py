from django.urls import path

from cphapp.api.views import TransactionsAPIView

urlpatterns = [
    path('transactions/', TransactionsAPIView.as_view(), name='transactions-list')
]
