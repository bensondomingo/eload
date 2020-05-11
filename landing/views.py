from django.views.generic.base import TemplateView
from django.conf import settings


class IndexTemplateView(TemplateView):

    def get_template_names(self):
        return 'cphapp/index.html'