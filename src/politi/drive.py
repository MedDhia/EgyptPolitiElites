"""Ingest annuaire PDFs handed over through Google Drive.

Why this exists
---------------
When the machine running the pipeline cannot reach the CEAlex host directly,
Google Drive works as a courier: a human downloads the volume and drops it in
Drive, and the agent reads it back through the Drive connector.

Two connector limits shape the design, both established by testing rather than
assumption:

* ``download_file_content`` returns faithful base64 bytes but **refuses any
  file over 10 MB**.
* ``read_file_content`` has no size limit but returns *truncated* text — it
  stopped at page 80 of a ~400-page volume — and carries no page markers.

So the only faithful route is base64, and any volume over 10 MB must be
**split into parts** before upload. ``split_pdf`` prepares those parts;
``save_tool_result`` lands each one in ``data/raw/``. The parser then treats
the parts as one continuous document.
"""

from __future__ import annotations

import base64
import json
import math
from pathlib import Path

from . import config

DRIVE_LIMIT_BYTES = 10 * 1024 * 1024  # the connector's hard download cap


def decode_tool_result(result_path: Path) -> tuple[bytes, str]:
    """Decode a saved ``download_file_content`` result into (bytes, title).

    Large tool results are written to disk by the harness rather than returned
    inline; this reads that JSON without pulling the base64 through context.
    """
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))
    if "content" not in payload:
        raise ValueError(
            f"{result_path} has no 'content' field. This should be the saved "
            f"result of download_file_content, not read_file_content "
            f"(whose text output is truncated and unusable here)."
        )
    raw = base64.b64decode(payload["content"])
    if not raw.startswith(b"%PDF"):
        raise ValueError(f"decoded content is not a PDF (magic={raw[:8]!r})")
    return raw, payload.get("title", "")


def save_tool_result(result_path: Path, year: int, part: int | None = None) -> Path:
    """Write a downloaded volume (or one part of it) into ``data/raw/``."""
    raw, title = decode_tool_result(Path(result_path))
    config.RAW.mkdir(parents=True, exist_ok=True)
    name = (f"politi_{year}.pdf" if part is None
            else f"politi_{year}_part{part:02d}.pdf")
    dest = config.RAW / name
    dest.write_bytes(raw)
    return dest


def split_pdf(pdf: Path, out_dir: Path, max_bytes: int = 9 * 1024 * 1024,
              stem: str | None = None) -> list[Path]:
    """Split *pdf* into parts small enough for the Drive connector.

    Pages are apportioned by a byte estimate and each part is checked after
    writing, so a part that overshoots is split again rather than silently
    exceeding the cap.
    """
    from pypdf import PdfReader, PdfWriter

    pdf = Path(pdf)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = stem or pdf.stem
    reader = PdfReader(str(pdf))
    n_pages = len(reader.pages)
    total = pdf.stat().st_size
    if total <= max_bytes:
        return [pdf]

    per_part = max(1, math.floor(n_pages * max_bytes / total))
    written: list[Path] = []
    start = 0
    while start < n_pages:
        size = per_part
        while True:
            writer = PdfWriter()
            for i in range(start, min(start + size, n_pages)):
                writer.add_page(reader.pages[i])
            dest = out_dir / f"{stem}_part{len(written) + 1:02d}.pdf"
            with dest.open("wb") as fh:
                writer.write(fh)
            if dest.stat().st_size <= max_bytes or size == 1:
                break
            size = max(1, size // 2)  # overshot: halve and retry
        written.append(dest)
        start += size
    return written
