from django.views.generic import TemplateView

from .form_schema import TABS


class IndexView(TemplateView):
    template_name = 'brandextract/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tabs'] = TABS
        return context
