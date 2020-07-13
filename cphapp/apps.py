from django.apps import AppConfig


class CphappConfig(AppConfig):
    name = 'cphapp'

    def ready(self):
        import cph
        return super().ready()
