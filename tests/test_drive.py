"""Ingesting volumes handed over through Drive or git.

Covers the transport layer: a volume too large for a connector is split into
parts, and the parts must read back as one continuous document.
"""

import base64
import json

import pytest

from politi.drive import DRIVE_LIMIT_BYTES, decode_tool_result, split_pdf
from politi.pdftext import PAGE_MARK_RE, extract_pdf


def _make_pdf(path, pages=40):
    from pypdf import PdfWriter

    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=612, height=792)
    with path.open("wb") as fh:
        w.write(fh)
    return path


def test_decode_rejects_read_file_content_output(tmp_path):
    """read_file_content returns truncated text; it must never be mistaken
    for a faithful download."""
    bad = tmp_path / "r.json"
    bad.write_text(json.dumps({"fileContent": "some text"}), encoding="utf-8")
    with pytest.raises(ValueError, match="no 'content' field"):
        decode_tool_result(bad)


def test_decode_rejects_non_pdf(tmp_path):
    bad = tmp_path / "r.json"
    bad.write_text(json.dumps({"content": base64.b64encode(b"not a pdf").decode()}),
                   encoding="utf-8")
    with pytest.raises(ValueError, match="not a PDF"):
        decode_tool_result(bad)


def test_decode_round_trip(tmp_path):
    pdf = _make_pdf(tmp_path / "v.pdf", pages=3)
    payload = {"content": base64.b64encode(pdf.read_bytes()).decode(),
               "title": "politi_1932.pdf"}
    res = tmp_path / "r.json"
    res.write_text(json.dumps(payload), encoding="utf-8")
    raw, title = decode_tool_result(res)
    assert raw == pdf.read_bytes()
    assert title == "politi_1932.pdf"


def test_small_pdf_is_not_split(tmp_path):
    pdf = _make_pdf(tmp_path / "v.pdf", pages=5)
    assert split_pdf(pdf, tmp_path / "out", max_bytes=DRIVE_LIMIT_BYTES) == [pdf]


def test_split_respects_the_cap(tmp_path):
    pdf = _make_pdf(tmp_path / "v.pdf", pages=60)
    cap = max(2000, pdf.stat().st_size // 5)
    parts = split_pdf(pdf, tmp_path / "out", max_bytes=cap)
    assert len(parts) > 1
    assert all(p.stat().st_size <= cap for p in parts), "a part exceeded the cap"


def test_split_preserves_every_page_exactly_once(tmp_path):
    from pypdf import PdfReader

    pdf = _make_pdf(tmp_path / "v.pdf", pages=60)
    parts = split_pdf(pdf, tmp_path / "out", max_bytes=pdf.stat().st_size // 4)
    assert sum(len(PdfReader(str(p)).pages) for p in parts) == 60


def test_parts_extract_as_one_continuous_document(tmp_path):
    pdf = _make_pdf(tmp_path / "v.pdf", pages=30)
    parts = split_pdf(pdf, tmp_path / "out", max_bytes=pdf.stat().st_size // 3)
    text = extract_pdf(parts, ocr_fallback=False)
    seen = [int(m.group(1)) for m in PAGE_MARK_RE.finditer(text)]
    assert seen == list(range(1, 31)), "page numbering must run across parts"


def test_single_path_and_list_agree(tmp_path):
    pdf = _make_pdf(tmp_path / "v.pdf", pages=6)
    assert extract_pdf(pdf, ocr_fallback=False) == extract_pdf([pdf], ocr_fallback=False)


def test_empty_source_list_is_an_error():
    with pytest.raises(ValueError, match="no PDF given"):
        extract_pdf([])


def test_a_defective_text_layer_is_recorded_in_the_edition():
    """1942 ships a text layer that is present, long, and wrong; the short-page
    fallback cannot catch it, so the defect is recorded explicitly."""
    from politi import config
    assert config.edition(1942).bad_text_layer
    assert not config.edition(1932).bad_text_layer


def test_force_ocr_ignores_the_embedded_text_layer(tmp_path, monkeypatch):
    from politi import pdftext

    pdf = _make_pdf(tmp_path / "v.pdf", pages=2)
    calls = []

    def fake_ocr(path, page_no, lang="fra"):
        calls.append(page_no)
        return f"OCR page {page_no}"

    monkeypatch.setattr(pdftext, "_ocr_page", fake_ocr)
    text = pdftext.extract_pdf(pdf, force_ocr=True)
    assert calls == [1, 2], "every page must be re-read from its image"
    assert "OCR page 1" in text
