from django.db.models import Q
from django.core.management.base import BaseCommand
from cphapp.models import LoadTransaction


class Command(BaseCommand):
    help = 'Bind LoadTransaction objects to retailer using device_hash'

    def handle(self, *args, **options):
        transactions = LoadTransaction.objects.filter(
            ~Q(device__device_hash=None),
            transaction_type='sellorder',
            retailer=None)

        for transaction in transactions:
            retailer = transaction.device.owner
            transaction.retailer = retailer
            transaction.save()
            print(transaction)
