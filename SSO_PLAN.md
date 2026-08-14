# Plan: Google Workspace SSO

Implementatieplan om de Branding Extractor volledig achter Google Workspace SSO te
zetten. Nog niet uitgevoerd.

## Uitgangssituatie

De app is nu volledig open: geen auth-app, geen sessies, `DATABASES = {}` en DRF op
`AllowAny`. Er zijn twee endpoints: `/` (`IndexView`) en `/api/extract/` (`ExtractView`).
SSO toevoegen betekent state introduceren — dat is de kern van dit plan.

## Keuzes

**Library: `mozilla-django-oidc`.** Klein, één flow, geen signup/password-reset/
e-mailverificatie-URLs die je daarna weer dicht moet timmeren. `django-allauth` kan ook
maar sleept veel extra endpoints mee = groter aanvalsoppervlak.

**State: SQLite-bestand.** `django.contrib.auth` heeft een User-model nodig, dus een DB
is onvermijdelijk zodra je een echte auth-backend gebruikt. Geen databaseserver nodig:
SQLite is één bestand, Python heeft het ingebouwd. Alternatief zonder DB is de OIDC-flow
zelf schrijven plus e-mail in een signed-cookie session — dan schrijf je zelf
token-exchange, JWKS-validatie en nonce/state. Niet doen.

**Geen wachtwoord-login.** `AUTHENTICATION_BACKENDS` bevat alleen de OIDC-backend, dus
`ModelBackend` bestaat niet. Er is precies één manier om een sessie te krijgen.

---

## Fase 1 — Dependencies en settings

`requirements.txt`: `mozilla-django-oidc` toevoegen.

`config/settings.py`:

```python
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'rest_framework',
    'mozilla_django_oidc',
    'brandextract',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

MIDDLEWARE, exacte volgorde. `SessionMiddleware` vóór `AuthenticationMiddleware`, en die
vóór `RequireLoginMiddleware` — anders bestaat `request.user` nog niet bij de check:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'brandextract.middleware.RequireLoginMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

Context processor erbij voor `{{ user }}` in templates:

```python
'context_processors': [
    'django.template.context_processors.request',
    'django.contrib.auth.context_processors.auth',
],
```

OIDC-config:

```python
AUTHENTICATION_BACKENDS = ['brandextract.auth.WorkspaceOIDCBackend']

# Leeg domein weigert elke login — veilige kant om op te falen.
GOOGLE_WORKSPACE_DOMAIN = os.environ.get('GOOGLE_WORKSPACE_DOMAIN', '')

OIDC_RP_CLIENT_ID = os.environ.get('GOOGLE_OIDC_CLIENT_ID', '')
OIDC_RP_CLIENT_SECRET = os.environ.get('GOOGLE_OIDC_CLIENT_SECRET', '')

OIDC_OP_AUTHORIZATION_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
OIDC_OP_TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token'
OIDC_OP_USER_ENDPOINT = 'https://openidconnect.googleapis.com/v1/userinfo'
OIDC_OP_JWKS_ENDPOINT = 'https://www.googleapis.com/oauth2/v3/certs'

OIDC_RP_SIGN_ALGO = 'RS256'
OIDC_RP_SCOPES = 'openid email profile'

# Alleen een hint voor Google's accountkiezer; de echte check staat in verify_claims.
OIDC_AUTH_REQUEST_EXTRA_PARAMS = {'hd': GOOGLE_WORKSPACE_DOMAIN}

OIDC_CREATE_USER = True

LOGIN_URL = '/oidc/authenticate/'
LOGIN_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL_FAILURE = '/'
LOGOUT_REDIRECT_URL = '/'

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 12
```

In het bestaande `DJANGO_SECURE_SSL`-blok erbij: `SESSION_COOKIE_SECURE = True`.

DRF omzetten (staat nu op `AllowAny`):

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
}
```

Fail-hard op de secret key, bovenaan bij `SECRET_KEY`:

```python
DEV_SECRET_KEY = 'dev-insecure-key-change-in-production'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', DEV_SECRET_KEY)
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# De dev-sleutel ondertekent sessiecookies: wie hem kent, vervalst een sessie
# en komt zonder Google-login binnen. Buiten DEBUG dus weigeren te starten.
if not DEBUG and SECRET_KEY == DEV_SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY moet gezet zijn als DJANGO_DEBUG=False')
```

## Fase 2 — Domeincontrole

> **Waarschuwing.** De `hd`-parameter in het autorisatieverzoek is alleen een UI-hint van
> Google. Een aanvaller haalt hem uit de URL en logt in met een willekeurig privé
> Gmail-account. Zonder servercontrole is "SSO" hier gelijk aan "iedereen met een
> Google-account mag erin". De controle moet server-side op de claims, en bij élke login
> opnieuw — ook bij bestaande gebruikers.

Nieuw bestand `brandextract/auth.py`:

```python
from django.conf import settings
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class WorkspaceOIDCBackend(OIDCAuthenticationBackend):
    def verify_claims(self, claims):
        domain = settings.GOOGLE_WORKSPACE_DOMAIN
        email = (claims.get('email') or '').lower()

        return (
            bool(domain)
            and claims.get('email_verified') is True
            # hd ontbreekt bij persoonlijke Gmail-accounts.
            and claims.get('hd') == domain
            and email.endswith('@' + domain.lower())
        )
```

`verify_claims` draait vóór het aanmaken én vóór het updaten van een user. Alias-domeinen
van dezelfde Workspace geven een andere `hd` en worden dus ook geweigerd — bewust.

Optioneel strenger: extra allowlist van e-mailadressen in een env-var. Aan te raden als
de tenant groot is en niet iedereen erbij hoeft.

## Fase 3 — Deny-by-default middleware

Niet per view `@login_required` zetten — dat is opt-in, en één vergeten view is een gat.
Django 5.2 heeft `LoginRequiredMiddleware`: alles dicht, expliciet openen met
`@login_not_required`.

Eén aanpassing nodig: een niet-ingelogde `fetch()` naar `/api/extract/` krijgt anders een
302 naar Google in plaats van een bruikbare fout.

Nieuw bestand `brandextract/middleware.py`:

```python
from django.contrib.auth.middleware import LoginRequiredMiddleware
from django.http import JsonResponse


class RequireLoginMiddleware(LoginRequiredMiddleware):
    def handle_no_permission(self, request, view_func):
        if request.path.startswith('/api/'):
            return JsonResponse({'detail': 'Authentication required'}, status=401)
        return super().handle_no_permission(request, view_func)
```

De views van `mozilla-django-oidc` zijn niet gedecoreerd. Onder deze middleware zouden ze
zelf ook login vereisen — dat geeft een **oneindige redirect-loop**. Los dat op door de
drie views expliciet vrij te geven, per view en niet per pad-prefix, zodat er nooit per
ongeluk iets anders onder `/oidc/` open komt te staan.

`config/urls.py`:

```python
from django.contrib.auth.decorators import login_not_required
from django.urls import include, path
from mozilla_django_oidc import views as oidc_views

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
```

`OIDCLogoutView` accepteert alleen POST (GET geeft 405, tenzij `ALLOW_LOGOUT_GET_METHOD`
aan staat — laten staan op de standaard).

## Fase 4 — Frontend

Nieuwe partial `templates/brandextract/partials/_session.html`:

```html
<div class="session">
  <span class="session-email">{{ user.email }}</span>
  <form class="session-logout" method="post" action="{% url 'oidc_logout' %}">
    {% csrf_token %}
    <button class="btn-secondary" type="submit">Uitloggen</button>
  </form>
</div>
```

Op twee plekken invoegen, niet als één fixed balk — de viewer is `height: 100vh` en de
`viewer-actions` staan al rechtsboven, dus een fixed balk zou daar overheen vallen:

- `index.html`, onderin `.upload-card`
- `index.html`, in `.viewer-actions` vóór de bestaande knoppen

`app.css`: `.session` als flexregel met `gap`, `.session-email` klein en grijs
(sluit aan bij `.subtitle`, `#666`).

`app.js`: in de `fetch('/api/extract/')`-handler bij `response.status === 401` de pagina
herladen. De sessie is dan verlopen en de gebruiker landt op de Google-login.

## Fase 5 — Google Cloud Console

- OAuth-client type **Web application**.
- Redirect-URI exact `https://<domein>/oidc/callback/`.
- User type **Internal** binnen de Workspace-organisatie. Dat is een tweede slot bovenop
  de `hd`-controle: externe accounts komen niet eens door het consent-scherm.
- Voor lokale ontwikkeling een tweede redirect-URI `http://localhost:8000/oidc/callback/`.
  Lokaal draaien vereist vanaf nu Google-credentials in de omgeving — bewust, want een
  lokale wachtwoord-bypass zou een tweede manier naar binnen zijn.

## Fase 6 — Deploy

- `deploy/gunicorn.service`: drie nieuwe env-vars (`GOOGLE_OIDC_CLIENT_ID`,
  `GOOGLE_OIDC_CLIENT_SECRET`, `GOOGLE_WORKSPACE_DOMAIN`). Het client secret **niet** in
  git: het bestand in de repo houdt een placeholder, de echte waarde staat op de server.
- `DEPLOY.md`: `manage.py migrate` toevoegen bij zowel de installatie- als de
  update-stappen.
- `.gitignore`: `db.sqlite3`.
- Rechten: `www-data` moet kunnen schrijven in `/srv/brandextract/`, niet alleen in het
  DB-bestand — SQLite legt journal/WAL-bestanden naast de database.
- `README.md`: de regel "geen database" klopt niet meer.

Contentie is geen issue: alleen login schrijft, extractie schrijft niets.

---

## Restrisico's

De applicatie zelf is hiermee volledig dicht. Vier punten blijven over.

1. **`/static/` gaat langs Django heen.** Nginx serveert `staticfiles/` rechtstreeks,
   zonder auth. Bevat nu alleen `app.css`, `app.js` en CodeMirror — geen data, geen
   secrets. Acceptabel, maar bewust accepteren. Wil je het ook dicht: `auth_request` in
   nginx, of statics via Django/WhiteNoise laten lopen. Voorwaarde blijft hoe dan ook:
   nooit uploads of resultaten in `staticfiles/` zetten.
2. **`DEBUG` staat standaard op `True`.** Valt de env-var op productie weg, dan draait de
   app in debug met tracebacks. Geen auth-bypass, wel een lek. De fail-hard-check uit
   fase 1 dekt de gevaarlijke helft af.
3. **Dev-`SECRET_KEY` in productie is een volledige bypass.** Sessiecookies zijn
   ondertekend met die sleutel; is de sleutel bekend, dan vervalst iemand een geldige
   sessie zonder ooit langs Google te gaan. Dit is het gevaarlijkste van de vier, en de
   reden dat de fail-hard-check erin zit.
4. **Wie de server zelf bereikt, komt overal.** Gunicorn luistert op een unix-socket, dus
   niet vanaf internet. SSH-toegang of een tweede site op dezelfde nginx vallen buiten
   applicatie-auth.

Verder gecontroleerd: geen `/admin/` (niet geïnstalleerd, houden zo), geen
health-endpoint, geen API-keys of tokens, uploads gaan naar een `TemporaryDirectory` en
overleven het request niet. Geen andere ingangen gevonden.

## Verificatie na implementatie

| Test | Verwacht |
|---|---|
| `curl -i https://<domein>/` | 302 naar accounts.google.com |
| `curl -i -X POST https://<domein>/api/extract/` | 401 JSON, niet 302 |
| Cookie `sessionid=willekeurig` | 302 naar Google |
| Login met privé-Gmail | geweigerd, geen user aangemaakt |
| Login met ander Workspace-domein | geweigerd |
| `hd` handmatig uit de autorisatie-URL slopen | nog steeds geweigerd bij de callback |
| `/admin/` | 404 |
| Logout, daarna back-knop | 302 naar Google |

De zesde test is het belangrijkste bewijs: die dekt precies het gat dat een naïeve
implementatie overhoudt.

## Geraakte bestanden

Gewijzigd: `requirements.txt`, `config/settings.py`, `config/urls.py`,
`brandextract/templates/brandextract/index.html`,
`brandextract/static/brandextract/css/app.css`,
`brandextract/static/brandextract/js/app.js`, `deploy/gunicorn.service`, `DEPLOY.md`,
`README.md`, `.gitignore`.

Nieuw: `brandextract/auth.py`, `brandextract/middleware.py`,
`brandextract/templates/brandextract/partials/_session.html`.

Ongewijzigd: `brandextract/extract_branding.py`, `brandextract/api.py`,
`brandextract/views.py`, `brandextract/form_schema.py`.
