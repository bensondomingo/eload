from django.contrib import admin

from cphapp.models import (LoadOutlet, LoadTransaction, Device)

admin.site.register(LoadOutlet)
admin.site.register(LoadTransaction)
admin.site.register(Device)
