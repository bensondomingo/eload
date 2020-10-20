from django.views.generic.base import TemplateView
from django.conf import settings


class IndexTemplateView(TemplateView):

    template_name = 'index.html'

    def get_template_names(self):
        if settings.DEBUG:
            self.template_name = f'dev/{self.template_name}'
        return super().get_template_names()
