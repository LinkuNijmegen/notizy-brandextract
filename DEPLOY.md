# Deploy naar Railway

## Vereisten

- GitHub account
- Railway account (railway.app) — gratis tier voldoet
- Code staat in een GitHub repository

---

## Stap 1 — Push naar GitHub

Als je nog geen GitHub repo hebt:

```bash
git init
git add .
git commit -m "Initial commit"
gh repo create docx-extract --private --push --source .
```

Of via github.com: New repository → push bestaande code.

---

## Stap 2 — Project aanmaken op Railway

1. Ga naar [railway.app](https://railway.app) en log in
2. Klik **New Project**
3. Kies **Deploy from GitHub repo**
4. Selecteer je `docx-extract` repository
5. Railway detecteert automatisch `railway.toml` en start de build

De build doet automatisch:
- `pip install -r requirements.txt`
- `cd frontend && npm install && npm run build`
- Start: `uvicorn api:app --host 0.0.0.0 --port $PORT`

---

## Stap 3 — Domein instellen

1. In Railway: klik op je service → tabblad **Settings**
2. Scroll naar **Networking** → **Generate Domain**
3. Je krijgt een URL zoals `docx-extract-production.up.railway.app`

---

## Stap 4 — Verifiëren

Open de gegenereerde URL in je browser. Je ziet de Branding Extractor interface.

Test: upload een DOCX → profiel moet verschijnen.

---

## Updates deployen

Elke push naar de `main` branch triggert automatisch een nieuwe deploy op Railway.

```bash
git add .
git commit -m "update"
git push
```

---

## Gratis tier limieten

| Resource | Limiet |
|----------|--------|
| Credits | $5/maand |
| RAM | 512 MB |
| CPU | Gedeeld |
| Opslag | Geen persistent (niet nodig — alles in memory) |

Voor licht gebruik (intern tool, occasionele extracties) past dit ruim binnen $5/maand.

---

## Lokaal draaien (ontwikkeling)

```bash
# Terminal 1 — backend
uvicorn api:app --reload

# Terminal 2 — frontend dev server
cd frontend && npm run dev
```

Frontend dev server draait op `localhost:5173` en proxyt API calls naar `localhost:8000`.
