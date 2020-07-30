from django.urls import path

from cphapp.api.views import TransactionsListAPIView

urlpatterns = [
    path('transactions/', TransactionsListAPIView.as_view(),
         name='transactions-list')
]
