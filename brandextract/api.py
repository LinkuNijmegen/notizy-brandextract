import re
import tempfile
import zipfile
from pathlib import Path

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .extract_branding import (
    EXCLUDED_SECTIONS,
    TEMPLATE_ASSET_SLUG,
    build_extracted_from_docx,
    build_extracted_from_pdf,
    build_profile,
    copy_asset_file,
    prune_sections,
)

REQUIRED_PLACEHOLDERS = ["{content}", "{{ document_title }}"]


def _check_placeholders(doc_path: Path) -> list[str]:
    """Return list of required placeholders missing from the DOCX."""
    try:
        with zipfile.ZipFile(doc_path) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
        text = re.sub(r"<[^>]+>", "", xml)
        return [p for p in REQUIRED_PLACEHOLDERS if p not in text]
    except Exception:
        return []


def _save_upload(upload, dest: Path) -> None:
    with open(dest, "wb") as handle:
        for chunk in upload.chunks():
            handle.write(chunk)


class ExtractView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        document = request.FILES.get("document")
        if not document:
            return Response({"detail": "No document uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        template_docx = request.FILES.get("template_docx")
        doc_suffix = Path(document.name or "").suffix.lower()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            doc_path = tmp_dir / ("document" + doc_suffix)
            _save_upload(document, doc_path)

            warnings = []
            if doc_suffix == ".docx":
                missing = _check_placeholders(doc_path)
                if missing:
                    warnings.append(f"Verplichte placeholders niet gevonden: {', '.join(missing)}")

            try:
                if doc_suffix == ".docx":
                    extracted = build_extracted_from_docx(str(doc_path), results_dir=tmp_dir)
                elif doc_suffix == ".pdf":
                    extracted = build_extracted_from_pdf(str(doc_path))
                else:
                    return Response(
                        {"detail": "Unsupported file type: %s" % doc_suffix},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except Exception as exc:
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            if template_docx:
                tmpl_suffix = Path(template_docx.name).suffix.lower()
                tmpl_path = tmp_dir / ("template" + tmpl_suffix)
                _save_upload(template_docx, tmpl_path)
                assets_dir = tmp_dir / "assets"
                assets_dir.mkdir(exist_ok=True)
                used_names = {item["filename"] for item in (extracted.get("assets") or []) if "filename" in item}
                filename = copy_asset_file(tmpl_path, assets_dir, used_names)
                if filename:
                    extracted.setdefault("assets", []).append({
                        "slug": TEMPLATE_ASSET_SLUG,
                        "filename": filename,
                        "original": template_docx.name,
                        "sources": ["template"],
                    })
                    extracted["template_asset_slug"] = TEMPLATE_ASSET_SLUG

            profile = build_profile(extracted)
            profile = prune_sections(profile, EXCLUDED_SECTIONS)
            profile["version"] = "2.0.0"

        return Response({
            "profile": profile,
            "document_filename": document.name or ("document" + doc_suffix),
            "warnings": warnings,
        })
