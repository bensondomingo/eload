from django.contrib import admin

from cphapp.models import (Transaction, UserAgent)

admin.site.register(Transaction)
admin.site.register(UserAgent)
