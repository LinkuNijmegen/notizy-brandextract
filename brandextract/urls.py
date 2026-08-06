from django.urls import path

from .api import ExtractView
from .views import IndexView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('api/extract/', ExtractView.as_view(), name='extract'),
]
