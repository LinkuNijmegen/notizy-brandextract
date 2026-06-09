#!/usr/bin/env python3
import re
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from extract_branding import (
    EXCLUDED_SECTIONS,
    TEMPLATE_ASSET_SLUG,
    build_extracted_from_docx,
    build_extracted_from_pdf,
    build_profile,
    copy_asset_file,
    prune_sections,
)

TEMPLATE_REQUIRED_PLACEHOLDER = "{content}"


def _docx_contains_placeholder(doc_path: Path, placeholder: str) -> bool:
    try:
        with zipfile.ZipFile(doc_path) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
        text = re.sub(r"<[^>]+>", "", xml)
        return placeholder in text
    except Exception:
        return False


app = FastAPI(title="docx-extract API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/check-template")
async def check_template(template_docx: UploadFile = File(...)):
    suffix = Path(template_docx.filename or "").suffix.lower()
    if suffix != ".docx":
        raise HTTPException(status_code=400, detail="Alleen DOCX bestanden zijn toegestaan")

    with tempfile.TemporaryDirectory() as tmp:
        tmpl_path = Path(tmp) / "template.docx"
        tmpl_path.write_bytes(await template_docx.read())
        if not _docx_contains_placeholder(tmpl_path, TEMPLATE_REQUIRED_PLACEHOLDER):
            raise HTTPException(
                status_code=422,
                detail=f"Template mist verplichte placeholder: {TEMPLATE_REQUIRED_PLACEHOLDER}",
            )

    return {"ok": True}


@app.post("/extract")
async def extract(
    document: UploadFile = File(...),
    template_docx: UploadFile | None = File(default=None),
):
    doc_suffix = Path(document.filename or "").suffix.lower()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        doc_path = tmp_dir / ("document" + doc_suffix)
        doc_path.write_bytes(await document.read())

        warnings = []
        try:
            if doc_suffix == ".docx":
                extracted = build_extracted_from_docx(str(doc_path), results_dir=tmp_dir)
            elif doc_suffix == ".pdf":
                extracted = build_extracted_from_pdf(str(doc_path))
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type: %s" % doc_suffix)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        if template_docx and template_docx.filename:
            tmpl_suffix = Path(template_docx.filename).suffix.lower()
            tmpl_path = tmp_dir / ("template" + tmpl_suffix)
            tmpl_path.write_bytes(await template_docx.read())

            assets_dir = tmp_dir / "assets"
            assets_dir.mkdir(exist_ok=True)
            used_names = {item["filename"] for item in (extracted.get("assets") or []) if "filename" in item}
            filename = copy_asset_file(tmpl_path, assets_dir, used_names)
            if filename:
                extracted.setdefault("assets", []).append({
                    "slug": TEMPLATE_ASSET_SLUG,
                    "filename": filename,
                    "original": template_docx.filename,
                    "sources": ["template"],
                })
                extracted["template_asset_slug"] = TEMPLATE_ASSET_SLUG

        profile = build_profile(extracted)
        profile = prune_sections(profile, EXCLUDED_SECTIONS)
        profile["version"] = "2.0.0"

    return {
        "profile": profile,
        "document_filename": document.filename or ("document" + doc_suffix),
        "warnings": warnings,
    }


# ── Serve React build (production) ───────────────────────────────────────────

_dist = Path("frontend/dist")

if _dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(str(_dist / "index.html"))
