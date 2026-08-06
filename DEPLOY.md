# Deploy naar eigen VPS

Django + gunicorn achter nginx. Eén server, geen database, geen Node.

## Vereisten

- Ubuntu/Debian VPS met root/sudo
- Python 3.11+
- nginx
- Domeinnaam die naar de server wijst

---

## Stap 1 — Code plaatsen

```bash
sudo mkdir -p /srv/brandextract
sudo chown $USER /srv/brandextract
git clone <repo-url> /srv/brandextract
cd /srv/brandextract
```

## Stap 2 — Virtualenv

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Stap 3 — Omgevingsvariabelen

Alles komt uit de systemd unit — er is geen `.env`-bestand.

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

Levert `/srv/brandextract/staticfiles/`. Nginx serveert die map rechtstreeks.

## Stap 5 — gunicorn als service

```bash
sudo cp deploy/gunicorn.service /etc/systemd/system/brandextract.service
sudo nano /etc/systemd/system/brandextract.service   # vul secret key + hostname in
sudo systemctl daemon-reload
sudo systemctl enable --now brandextract
sudo systemctl status brandextract
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

Zet daarna pas `DJANGO_SECURE_SSL=True` in de systemd unit en herstart de service.
Dat schakelt HSTS, secure cookies en de HTTPS-redirect in Django in. Eerder aanzetten
levert een redirect-lus op, want er is dan nog geen HTTPS.

```bash
sudo systemctl restart brandextract
```

## Stap 8 — Verifiëren

Open het domein in de browser. Je ziet de Branding Extractor. Upload een DOCX → profiel verschijnt.

---

## Updates deployen

```bash
cd /srv/brandextract
git pull
.venv/bin/pip install -r requirements.txt
DJANGO_DEBUG=False .venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart brandextract
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
sudo journalctl -u brandextract -f
```
