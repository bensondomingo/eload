from django.contrib import admin

from cphapp.models import (Transaction, LoadOrder, BuyOrder, UserAgent)

admin.site.register(Transaction)
admin.site.register(LoadOrder)
admin.site.register(BuyOrder)
admin.site.register(UserAgent)
