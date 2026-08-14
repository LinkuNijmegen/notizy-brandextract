# Plan: keuze SSO-domein

Vervolg op `SSO_PLAN.md`, dat is uitgevoerd. De code is klaar en sluit op precies één
Workspace-domein; alleen de waarde staat nog open. Nog niet uitgevoerd.

## Stand van zaken

`GOOGLE_WORKSPACE_DOMAIN` is nog leeg. Leeg betekent: elke login wordt geweigerd
(`verify_claims` in `brandextract/auth.py` geeft `False` bij een leeg domein). De app is
dus dicht, niet stuk — er kan alleen nog niemand in.

Openstaand: wordt het `notizy.nl` of `notizy.com`. `linku.nl` is vervallen; dat was een
losse Workspace-organisatie en de enige reden om meerdere domeinen te ondersteunen.

## Scenario A — één domein (verwacht)

Geen codewijziging. Alleen invullen:

1. `.env` lokaal en `deploy/supervisor.conf` op de server: `GOOGLE_WORKSPACE_DOMAIN=<gekozen domein>`.
2. Google Cloud Console, in de Workspace-organisatie van dat domein: OAuth-client type
   **Web application**, user type **Internal**, redirect-URI's
   `https://brandextract.notizy.nl/oidc/callback/` en `http://localhost:8000/oidc/callback/`.
3. `GOOGLE_OIDC_CLIENT_ID` en `GOOGLE_OIDC_CLIENT_SECRET` invullen. Secret nooit in git.
4. `sudo supervisorctl restart application`.

Zit het andere domein als **domein-alias** in dezelfde tenant, dan hoeft er ook daarna
niets: accounts houden hun primaire adres, en zowel de `hd`- als de `email`-claim blijven
het primaire domein. Het aliasadres komt nooit in de token voor.

## Scenario B — beide domeinen tegelijk toestaan

Alleen nodig als `notizy.nl` en `notizy.com` echt naast elkaar blijven bestaan als
aparte accounts (secundair domein of aparte tenant). Dan meervoud maken.

`config/settings.py`:

```python
GOOGLE_WORKSPACE_DOMAINS = {
    d.strip().lower()
    for d in os.environ.get('GOOGLE_WORKSPACE_DOMAINS', '').split(',')
    if d.strip()
}

# hd accepteert één waarde; '*' beperkt de accountkiezer tot Workspace-accounts.
OIDC_AUTH_REQUEST_EXTRA_PARAMS = {
    'hd': next(iter(GOOGLE_WORKSPACE_DOMAINS)) if len(GOOGLE_WORKSPACE_DOMAINS) == 1 else '*'
}
```

`brandextract/auth.py`:

```python
def verify_claims(self, claims):
    domains = settings.GOOGLE_WORKSPACE_DOMAINS
    hd = (claims.get('hd') or '').lower()
    email = (claims.get('email') or '').lower()

    return (
        bool(domains)
        and claims.get('email_verified') is True
        and hd in domains
        and email.endswith('@' + hd)
    )
```

Even streng als nu: leeg weigert alles, en het e-mailadres moet horen bij de `hd` uit
dezelfde token — niet bij een willekeurig domein uit de lijst.

Verder: env-var hernoemen naar `GOOGLE_WORKSPACE_DOMAINS` in `.env.example`,
`deploy/supervisor.conf`, `deploy/gunicorn.service`, `DEPLOY.md`.

**Gevolg voor de beveiliging.** Twee losse tenants betekent dat het consent-scherm niet
meer op **Internal** kan staan — dat is per definitie beperkt tot één organisatie. Met
**External** komt iedereen met een Google-account door het consent-scherm en is
`verify_claims` de enige controle die overblijft. Geen app-verificatie of gebruikerslimiet
nodig (`openid email profile` zijn non-sensitive scopes), maar wel één laag minder dan nu.
Zijn het twee domeinen binnen dezelfde tenant, dan blijft Internal staan en verandert er
niets aan het risico.

## Bij wisselen van domein na ingebruikname

`verify_claims` draait bij élke login, dus accounts van het oude domein komen er niet meer
in. Bestaande sessiecookies blijven wel geldig tot ze verlopen (`SESSION_COOKIE_AGE`, nu
12 uur). Direct afsluiten:

```bash
.venv/bin/python manage.py clearsessions   # alleen verlopen sessies
```

`clearsessions` ruimt alleen verlopen rijen op. Om iedereen er echt uit te gooien: de
tabel `django_session` legen, en de users van het oude domein verwijderen zodat er geen
dode rijen achterblijven.

## Verificatie

Zelfde tests als in `SSO_PLAN.md`, met het gekozen domein ingevuld. Belangrijkste twee:

| Test | Verwacht |
|---|---|
| Login met account van het gekozen domein | werkt, user aangemaakt |
| Login met privé-Gmail, `hd` handmatig uit de autorisatie-URL gesloopt | geweigerd bij de callback |

## Geraakte bestanden

Scenario A: `.env` (server), `deploy/supervisor.conf`. Geen code.

Scenario B: aanvullend `config/settings.py`, `brandextract/auth.py`, `.env.example`,
`deploy/gunicorn.service`, `DEPLOY.md`.
