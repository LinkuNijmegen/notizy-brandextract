from django.contrib.auth.middleware import LoginRequiredMiddleware
from django.http import JsonResponse


class ForceHTTPSProtoMiddleware:
    # De proxy voor deze app stuurt wel X-Forwarded-For maar geen X-Forwarded-Proto,
    # waardoor Django elke request als HTTP ziet en OIDC een http-redirect_uri bouwt.
    # We zetten de header hier zelf, zodat SECURE_PROXY_SSL_HEADER weer klopt.
    # Vereist dat gunicorn alleen via de proxy bereikbaar is.
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.META['HTTP_X_FORWARDED_PROTO'] = 'https'
        return self.get_response(request)


class RequireLoginMiddleware(LoginRequiredMiddleware):
    def process_view(self, request, view_func, view_args, view_kwargs):
        # DRF zet login_required = False op al zijn views, waardoor de basisklasse ze
        # overslaat. Onder /api/ negeren we dat, zodat de deny-by-default check op één
        # plek blijft in plaats van af te hangen van de DRF-permissieklassen.
        if request.path.startswith('/api/') and not request.user.is_authenticated:
            return self.handle_no_permission(request, view_func)
        return super().process_view(request, view_func, view_args, view_kwargs)

    def handle_no_permission(self, request, view_func):
        # Zonder dit krijgt een fetch() een 302 naar Google in plaats van een fout.
        if request.path.startswith('/api/'):
            return JsonResponse({'detail': 'Authentication required'}, status=401)
        return super().handle_no_permission(request, view_func)
