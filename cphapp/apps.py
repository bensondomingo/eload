# flake8: noqa
from django.apps import AppConfig


class CphappConfig(AppConfig):
    name = 'cphapp'

    def ready(self):
        import cph
        import cphapp.signals
        return super().ready()
