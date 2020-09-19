from django.views.generic.base import TemplateView
from django.conf import settings


class IndexTemplateView(TemplateView):

    def get_template_names(self):
        if settings.DEBUG:
            return 'index-dev.html'
        return 'index.html'
