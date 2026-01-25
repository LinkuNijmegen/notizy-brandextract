# DOCX/PDF Branding Extractor

Extracts branding information (fonts, headings, headers/footers, margins, spacing, colors) from DOCX or PDF files and maps it into a structured branding profile template. DOCX logos/images are also saved as assets.

## Requirements

- Python 3.9+
- For PDF input: `pdfplumber`
- For XLSX output: `openpyxl`

Install optional dependencies:

```bash
pip install pdfplumber openpyxl
```

## Usage

Run the script with a DOCX or PDF file:

```bash
python extract_branding.py path/to/file.docx --format json
python extract_branding.py path/to/file.pdf --format json
python extract_branding.py path/to/file.docx --format xlsx
```

### Output location

All outputs are saved to `./results`.

- Default filename: `<input_stem>.branding.<format>`
- You can set a custom filename with `--output` (extension is derived from `--format`):

```bash
python extract_branding.py path/to/file.docx --format json --output klantA
```

This produces `results/klantA.json`.

### Assets (logos/images)

For DOCX inputs, embedded images (including header/footer logos) are saved to `results/assets`. The JSON output includes:

- `extras.assets`: list of extracted assets with original DOCX paths and sources.
- `extras.logo_files`: logo candidates (images found in headers).

## Notes

- DOCX parsing reads styles, theme fonts/colors, margins, headings, and header/footer formatting.
- PDF parsing uses heuristics; header/footer detection and spacing are best-effort.
- The output includes `extras.fonts_used` and `extras.colors_used` for auditing.
