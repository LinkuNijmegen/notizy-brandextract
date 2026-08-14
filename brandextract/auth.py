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
