from django.contrib import admin

from cphapp.models import (Transaction, Order, UserAgent)

admin.site.register(Transaction)
admin.site.register(Order)
admin.site.register(UserAgent)
