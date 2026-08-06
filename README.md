# DOCX/PDF Branding Extractor

Extracts branding information (fonts, headings, headers/footers, margins, spacing, colors) from DOCX or PDF files and maps it into a structured branding profile template. DOCX logos/images are also saved as assets.

## Requirements

- Python 3.11+

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Web app

Django serves the upload page and the profile editor:

```bash
python manage.py runserver
```

Open `http://localhost:8000`. Upload a DOCX or PDF, edit the resulting profile in the
form or directly in the JSON panel, and copy the result. See `DEPLOY.md` for the
VPS setup (gunicorn + nginx).

## CLI usage

Run the extractor with a DOCX or PDF file:

```bash
python -m brandextract.extract_branding path/to/file.docx --format json
python -m brandextract.extract_branding path/to/file.pdf --format json
python -m brandextract.extract_branding path/to/file.docx --format xlsx
```

Use this one:

```bash
python -m brandextract.extract_branding input/document.docx --format json --template-docx input/templat.docx
```

### Template (base profile)

By default the script uses `results/finc.json` as the base template if it exists. Any sections not present in the template are not filled.

You can override this with `--template`:

```bash
python -m brandextract.extract_branding path/to/file.docx --format json --template path/to/template.json
```

### Optional DOCX template asset

Attach a DOCX template file as an asset and reference it in the output:

```bash
python -m brandextract.extract_branding path/to/file.docx --format json --template-docx path/to/template.docx
```

This adds `template_file: { "asset_slug": "template-file" }` and stores the DOCX in `results/assets` with slug `template-file`.

### Output location

All outputs are saved to `./results`.

- Default filename: `<input_stem>.branding.<format>`
- You can set a custom filename with `--output` (extension is derived from `--format`):

```bash
python -m brandextract.extract_branding path/to/file.docx --format json --output klantA
```

This produces `results/klantA.json`.

### Assets (logos/images)

For DOCX inputs, embedded images (including header/footer logos) are saved to `results/assets`. The JSON output includes:

- `extras.assets`: list of extracted assets with slugs, filenames, and sources (no local paths).
- `page_header.logo.asset_slug`: slug of the header logo when detected.

## Notes

- DOCX parsing reads styles, theme fonts/colors, margins, headings, and header/footer formatting.
- PDF parsing uses heuristics; header/footer detection and spacing are best-effort.
- The output includes `extras.fonts_used` and `extras.colors_used` for auditing.
