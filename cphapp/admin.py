from django.contrib import admin

from cphapp.models import (LoadOutlet, LoadTransaction, UserAgent)

admin.site.register(LoadOutlet)
admin.site.register(LoadTransaction)
admin.site.register(UserAgent)
