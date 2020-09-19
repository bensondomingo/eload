from rest_framework.permissions import BasePermission
from django.contrib.auth.models import Group


class IsRetailer(BasePermission):

    def has_permission(self, request, view):
        try:
            request.user.groups(name='retailers')
        except Group.DoesNotExist:
            return False
        else:
            return True
