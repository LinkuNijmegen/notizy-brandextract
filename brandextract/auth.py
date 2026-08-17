from django.conf import settings
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class WorkspaceOIDCBackend(OIDCAuthenticationBackend):
    def verify_claims(self, claims):
        domains = settings.GOOGLE_WORKSPACE_DOMAINS
        # hd ontbreekt bij persoonlijke Gmail-accounts.
        hd = (claims.get('hd') or '').lower()
        email = (claims.get('email') or '').lower()

        return (
            bool(domains)
            and claims.get('email_verified') is True
            and hd in domains
            # Het adres moet horen bij de hd uit dezelfde token,
            # niet bij een willekeurig domein uit de lijst.
            and email.endswith('@' + hd)
        )
