class LoadAmountError(Exception):

    def __init__(self, amount, minimum, maximum, *args, **kwargs):
        self.amount = amount
        self.min = minimum
        self.max = maximum
        return super(LoadAmountError, self).__init__(*args, **kwargs)

    def __str__(self):
        return (f'Load amount {self.amount} is out of range. '
                f'Valid range: {self.min} <= amount <= {self.max}')


class PhoneNumberError(Exception):

    def __init__(self, phone_number, err, *args, **kwargs):
        self.phone_number = phone_number
        super().__init__(*args, **kwargs)

    def __str__(self):
        pass


class RequestNewOrderError(Exception):
    def __init__(self, data, errors, *args, **kwargs) -> None:
        self.data = data
        self.errors = errors
        super().__init__(*args, **kwargs)

    def __str__(self):
        return 'Error messages: {} caused by data {}'.format(
            ', '.join(self.errors), self.data)


class OrderStatusError(Exception):

    def __init__(self, status, eti, *args, **kwargs):
        self.status = status
        self.eti = eti
        super().__init__(self, *args, **kwargs)

    def __str__(self):
        return (f'Order {self.eti} status not yet finalized: {self.status}')
