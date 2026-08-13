# Deploy naar eigen VPS

Django + gunicorn achter nginx. Eén server, geen database, geen Node.

## Vereisten

- Ubuntu/Debian VPS met root/sudo
- Python 3.11+ inclusief `python3.11-venv` (Debian levert `venv` niet standaard mee)
- nginx
- supervisor
- Domeinnaam die naar de server wijst

```bash
sudo apt install python3.11-venv
```

---

## Stap 1 — Code plaatsen

De app draait uit de home-map van de deploy-user, dus hier is geen root nodig:

```bash
git clone <repo-url> /projects/notizybra_aa
cd /projects/notizybra_aa
```

Nginx (`www-data`) moet wél door de home-map heen kunnen om `staticfiles/` te lezen.
Home-mappen staan vaak op `0750`, en dan krijg je 403's op alle CSS en JS:

```bash
sudo chmod o+x /projects/notizybra_aa
```

## Stap 2 — Virtualenv

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Stap 3 — Omgevingsvariabelen

Alles komt uit `deploy/supervisor.conf` — er is geen `.env`-bestand.

| Variabele | Waarde |
|---|---|
| `DJANGO_SECRET_KEY` | willekeurige lange string, genereer met `python -c "import secrets;print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `extractor.example.com` (komma-gescheiden bij meerdere) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://extractor.example.com` |
| `DJANGO_SECURE_SSL` | `False` tot HTTPS draait, daarna `True` |

## Stap 4 — Statische bestanden

```bash
DJANGO_DEBUG=False .venv/bin/python manage.py collectstatic --noinput
```

Levert `/projects/notizybra_aa/staticfiles/`. Nginx serveert die map rechtstreeks.

## Stap 5 — gunicorn onder supervisor

```bash
sudo cp deploy/supervisor.conf /etc/supervisor/conf.d/brandextract.conf
sudo nano /etc/supervisor/conf.d/brandextract.conf   # secret key, hostname, paden
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status application
```

Het programma heet `application`, want dat is de naam die de deploy-pipeline herstart.
Draait er al een ander programma onder die naam, kies dan een unieke naam en pas
de laatste regel van de SSH-actie in de pipeline daarop aan.

Controleer dat poort 8000 vrij is, anders start gunicorn niet:

```bash
ss -ltnp | grep 8000
```

## Stap 6 — nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/brandextract
sudo nano /etc/nginx/sites-available/brandextract   # vul server_name in
sudo ln -s /etc/nginx/sites-available/brandextract /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## Stap 7 — HTTPS

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d extractor.example.com
```

Zet daarna pas `DJANGO_SECURE_SSL=True` in de supervisor-config en herstart de service.
Dat schakelt HSTS, secure cookies en de HTTPS-redirect in Django in. Eerder aanzetten
levert een redirect-lus op, want er is dan nog geen HTTPS.

```bash
sudo supervisorctl restart application
```

## Stap 8 — Verifiëren

Open het domein in de browser. Je ziet de Branding Extractor. Upload een DOCX → profiel verschijnt.

---

## Updates deployen

```bash
cd /projects/notizybra_aa
git pull
.venv/bin/pip install -r requirements.txt
DJANGO_DEBUG=False .venv/bin/python manage.py collectstatic --noinput
sudo supervisorctl restart application
```

---

## Uploadlimiet aanpassen

Op twee plekken tegelijk wijzigen, anders geeft nginx een 413:

- `config/settings.py` → `DATA_UPLOAD_MAX_MEMORY_SIZE` en `FILE_UPLOAD_MAX_MEMORY_SIZE`
- `deploy/nginx.conf` → `client_max_body_size`

---

## Lokaal draaien (ontwikkeling)

```bash
.venv/bin/python manage.py runserver
```

Draait op `localhost:8000`, statics worden door Django zelf geserveerd.

---

## Logs

```bash
sudo supervisorctl tail -f application
```
