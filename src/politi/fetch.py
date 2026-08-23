"""Download the annuaire volumes.

This will not run in a sandbox whose egress policy blocks the host; it is
written for a machine with ordinary network access. Every download is recorded
in ``data/raw/manifest.json`` with a SHA-256 digest so that a later analysis can
prove which scan it was built from.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from pathlib import Path

from . import config

UA = "politi-dataset/0.1 (academic research; contact via repository)"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, dest: Path, retries: int = 4, timeout: int = 120) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    delay = 2.0
    last: Exception | None = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r, dest.open("wb") as out:
                while chunk := r.read(1 << 20):
                    out.write(chunk)
            return dest
        except Exception as exc:  # network conditions vary; retry with backoff
            last = exc
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"could not download {url}: {last}")


def fetch_wave(year: int, force: bool = False) -> Path | None:
    ed = config.edition(year)
    if ed.url is None:
        print(f"[{year}] no resolved URL — see docs/SOURCES.md")
        return None
    if ed.pdf_path.exists() and not force:
        print(f"[{year}] already present: {ed.pdf_path}")
        return ed.pdf_path
    print(f"[{year}] downloading {ed.url}")
    path = download(ed.url, ed.pdf_path)
    _record(year, path, ed.url)
    return path


def _record(year: int, path: Path, url: str) -> None:
    manifest_path = config.RAW / "manifest.json"
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[str(year)] = {
        "url": url,
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def fetch_all(force: bool = False) -> list[Path]:
    out = []
    for year in config.WAVES:
        try:
            p = fetch_wave(year, force=force)
        except RuntimeError as exc:
            print(f"[{year}] {exc}")
            continue
        if p:
            out.append(p)
    return out
