from django.urls import path

from cphapp.api.views import TransactionsListAPIView, TransactionsRetrieveUpdateAPIView

urlpatterns = [
    path('transactions/', TransactionsListAPIView.as_view(),
         name='transactions-list'),
    path('transactions/<str:pk>/', TransactionsRetrieveUpdateAPIView.as_view(),
         name='transactions-detail')
]
