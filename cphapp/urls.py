from django.urls import path, include

urlpatterns = [
    path('api/', include('cphapp.api.urls')),
]
