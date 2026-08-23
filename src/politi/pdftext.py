"""Turn an annuaire PDF into plain text, one page per record.

The CEAlex scans are distributed as OCR'd, text-searchable PDFs, so the text
layer is usually extractable directly. ``extract_pdf`` falls back to an OCR
pass (Tesseract, French) only for pages whose text layer is empty or
suspiciously short, which is the usual signature of a plate or a page the OCR
missed.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

MIN_CHARS = 120  # below this a page is treated as having no usable text layer

_PAGE_SEP = "\n\f<<<PAGE {n}>>>\f\n"
PAGE_MARK_RE = re.compile(r"<<<PAGE (\d+)>>>")


def _ocr_page(pdf: Path, page_no: int, lang: str = "fra") -> str:
    """OCR a single page. Returns '' when the tooling is unavailable."""
    if not (shutil.which("pdftoppm") and shutil.which("tesseract")):
        return ""
    with tempfile.TemporaryDirectory() as td:
        stem = Path(td) / "pg"
        subprocess.run(
            ["pdftoppm", "-r", "300", "-gray", "-f", str(page_no), "-l", str(page_no),
             "-png", str(pdf), str(stem)],
            check=False, capture_output=True,
        )
        images = sorted(Path(td).glob("pg*.png"))
        if not images:
            return ""
        out = subprocess.run(
            ["tesseract", str(images[0]), "stdout", "-l", lang, "--psm", "6"],
            check=False, capture_output=True, text=True,
        )
        return out.stdout or ""


def extract_pdf(pdf: Path, ocr_fallback: bool = True, lang: str = "fra") -> str:
    """Extract the full text of *pdf*, page-marked for later provenance."""
    import pdfplumber

    chunks: list[str] = []
    with pdfplumber.open(str(pdf)) as doc:
        for i, page in enumerate(doc.pages, start=1):
            text = page.extract_text() or ""
            if ocr_fallback and len(text.strip()) < MIN_CHARS:
                text = _ocr_page(pdf, i, lang=lang) or text
            chunks.append(_PAGE_SEP.format(n=i))
            chunks.append(text)
    return "".join(chunks)


def page_of(text: str, offset: int) -> int | None:
    """Which printed page does character *offset* fall on?"""
    last = None
    for m in PAGE_MARK_RE.finditer(text):
        if m.start() > offset:
            break
        last = int(m.group(1))
    return last


def strip_page_marks(text: str) -> str:
    return PAGE_MARK_RE.sub(" ", text).replace("\f", "\n")
