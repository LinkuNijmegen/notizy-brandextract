from django.contrib.auth.decorators import login_not_required
from django.urls import include, path
from mozilla_django_oidc import views as oidc_views

# Per view vrijgeven, niet per pad-prefix: onder RequireLoginMiddleware zouden deze
# views zelf ook login vereisen en dat geeft een oneindige redirect-loop.
oidc_urlpatterns = [
    path(
        'authenticate/',
        login_not_required(oidc_views.OIDCAuthenticationRequestView.as_view()),
        name='oidc_authentication_init',
    ),
    path(
        'callback/',
        login_not_required(oidc_views.OIDCAuthenticationCallbackView.as_view()),
        name='oidc_authentication_callback',
    ),
    path(
        'logout/',
        login_not_required(oidc_views.OIDCLogoutView.as_view()),
        name='oidc_logout',
    ),
]

urlpatterns = [
    path('oidc/', include(oidc_urlpatterns)),
    path('', include('brandextract.urls')),
]
