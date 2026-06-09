# Branding Extractor (DOCX/PDF)

Extract branding and layout settings from DOCX or PDF files and convert them into a structured branding profile JSON (or XLSX).

This repository includes:

- A Python extraction engine
- A FastAPI backend with one upload endpoint
- A React UI to upload documents and edit/copy the resulting JSON profile

## What it extracts

- Typography: body, headings, lists, table, quote styles
- Layout: page size, margins, orientation, spacing
- Header/footer configuration and logo metadata
- Color and font inventories (`extras.colors_used`, `extras.fonts_used`)
- Embedded DOCX images as assets (saved under `results/assets`)

Notes:

- DOCX extraction is the most complete.
- PDF extraction is heuristic-based and best effort for structure details.

## Project structure

```text
.
|- api.py                   # FastAPI app (/extract) + static UI serving in production
|- extract_branding.py      # CLI + core extraction/build logic
|- requirements.txt
|- railway.toml
|- frontend/                # Vite + React UI
|- input/                   # Example input files
`- results/                 # Generated outputs and extracted assets
```

## Requirements

- Python 3.9+
- Node.js 18+ (for frontend development/build)

Install backend dependencies:

```bash
pip install -r requirements.txt
```

## Local development

Run backend and frontend in separate terminals.

1) Start backend (FastAPI)

```bash
uvicorn api:app --reload
```

Backend runs on `http://localhost:8000`.

2) Start frontend (Vite)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173` and proxies `/extract` to `localhost:8000`.

## CLI usage

Basic examples:

```bash
python3 extract_branding.py input/file.docx --format json
python3 extract_branding.py input/file.pdf --format json
python3 extract_branding.py input/file.docx --format xlsx
```

### Options

```text
input_path                 Path to .docx or .pdf (required)
--format {json,xlsx}       Output format (default: json)
--output NAME              Output filename stem (extension follows --format)
--template PATH            Base template JSON (default: results/finc.json)
--template-docx PATH       Optional DOCX attached as template asset
```

### Output behavior

- Output folder: `results/`
- Default output name: `<input_stem>.branding.<format>`
- Example custom output:

```bash
python3 extract_branding.py input/file.docx --format json --output klantA
```

Writes: `results/klantA.json`

### Template DOCX as asset

If you pass `--template-docx`, the file is copied to `results/assets` and linked using slug `template-file` in the extracted asset list.

## API usage

### Endpoint

- `POST /extract`
- `multipart/form-data`

Form fields:

- `document` (required): DOCX or PDF
- `template_docx` (optional): DOCX template file

Example:

```bash
curl -X POST http://localhost:8000/extract \
	-F "document=@input/finc.docx" \
	-F "template_docx=@input/finc.docx"
```

Response shape:

```json
{
	"profile": {"version": "2.0.0"},
	"document_filename": "example.docx",
	"warnings": []
}
```

For DOCX uploads, the API also checks for required placeholders and may return warnings when placeholders are missing.

## Production build (single service)

Build frontend and run backend:

```bash
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
uvicorn api:app --host 0.0.0.0 --port 8000
```

When `frontend/dist` exists, `api.py` serves the built UI and static assets.

## Deployment

Railway is preconfigured via `railway.toml`:

- Build command installs Python deps, then builds frontend
- Start command runs `uvicorn api:app --host 0.0.0.0 --port $PORT`

See `DEPLOY.md` for the full step-by-step Railway flow.
