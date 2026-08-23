"""Source registry and pipeline-wide constants.

Édition numbering
-----------------
Politi's annuaire is numbered by édition rather than year. Two editions are
confirmed from the CEAlex catalogue: 1947 = 18e édition, 1950 = 21e édition.
Both satisfy ``year - edition = 1929``, which implies an unbroken annual run
and gives the inferred numbering below. Editions marked ``verified=False``
are INFERRED and must be checked against the volume's own title page before
being cited. See docs/SOURCES.md.
"""

from dataclasses import dataclass, field
from pathlib import Path

# Repository layout -----------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"            # the annuaire PDFs, as downloaded
INCOMING = DATA / "incoming"  # volumes delivered through git (see docs/SOURCES.md)
INTERIM = DATA / "interim"    # extracted page text, one .txt per volume
PROCESSED = DATA / "processed"  # analysis-ready tables and graph files

WAVES = (1932, 1938, 1942, 1947, 1950)


@dataclass(frozen=True)
class Edition:
    """One annuaire volume: a single observation wave of the network."""

    year: int
    edition: int | None          # nth édition, per the title page
    edition_verified: bool       # False => inferred from the 1929 offset
    place: str                   # place of publication
    cealex_id: str | None        # CEAlex "Études rares et anciennes" identifier
    url: str | None              # direct PDF, when known
    note: str = ""

    @property
    def pdf_path(self) -> Path:
        return RAW / f"politi_{self.year}.pdf"

    @property
    def text_path(self) -> Path:
        return INTERIM / f"politi_{self.year}.txt"

    def pdf_sources(self) -> list[Path]:
        """Every PDF making up this volume, in reading order.

        A volume may arrive whole (``politi_1932.pdf``) or split into parts
        (``politi_1932_part01.pdf``, ``_part02.pdf``, …). Splitting is how a
        volume gets through the Google Drive connector, which refuses any
        download over 10 MB. Parts are concatenated as one continuous
        document, so page numbering runs across the whole volume.
        """
        for folder in (RAW, INCOMING):
            parts = sorted(folder.glob(f"politi_{self.year}_part*.pdf"))
            if parts:
                return parts
            whole = folder / f"politi_{self.year}.pdf"
            if whole.exists():
                return [whole]
        return []

    def has_source(self) -> bool:
        return bool(self.pdf_sources()) or self.text_path.exists()


# The CEAlex digital library serves this collection as OCR'd, text-searchable
# PDFs under https://bdd.cealex.org/diffusion/etud_anc_alex/<ID>_w.pdf
CEALEX_PDF = "https://bdd.cealex.org/diffusion/etud_anc_alex/{cealex_id}_w.pdf"
CEALEX_INDEX = "https://bdd.cealex.org/ressources-documentaires/lvr_i.php"

EDITIONS: dict[int, Edition] = {
    1932: Edition(
        year=1932, edition=3, edition_verified=False, place="Le Caire",
        cealex_id="LVR_000323",
        url=CEALEX_PDF.format(cealex_id="LVR_000323"),
        note="Digitised. Direct PDF in the CEAlex digital library.",
    ),
    1938: Edition(
        year=1938, edition=9, edition_verified=False, place="Le Caire",
        cealex_id=None, url=None,
        note="No digitisation found anywhere. Print only — see docs/SOURCES.md.",
    ),
    1942: Edition(
        year=1942, edition=13, edition_verified=False, place="Le Caire",
        cealex_id=None, url=None,
        note="No digitisation found anywhere. Print only — see docs/SOURCES.md.",
    ),
    1947: Edition(
        year=1947, edition=18, edition_verified=True, place="Alexandrie",
        cealex_id=None, url=None,
        note="18e édition. CEAlex holds a catalogue record but no PDF in the "
             "diffusion tree. Print only — see docs/SOURCES.md.",
    ),
    1950: Edition(
        year=1950, edition=21, edition_verified=True, place="Alexandrie",
        cealex_id=None, url=None,
        note="21e édition. CEAlex holds a catalogue record but no PDF in the "
             "diffusion tree. Print only — see docs/SOURCES.md.",
    ),
}

# Adjacent CEAlex volumes that ARE digitised, with identifiers confirmed by
# search against the diffusion tree. These are *social and community
# registers*, not company registers: they carry board and directorship
# information but under a different selection rule, so they complement Politi
# rather than substituting for him. See docs/SOURCES.md before using them as
# network waves.
ADJACENT: dict[str, dict] = {
    "LVR_000091": {"title": "Le Mondain Égyptien", "year": 1939},
    "LVR_000055_I": {"title": "Le Mondain Égyptien, Part I", "year": 1941},
    "LVR_000055_II": {"title": "Le Mondain Égyptien, Part II", "year": 1941},
    "LVR_000018_I": {"title": "Le Mondain Égyptien, Part I", "year": 1943},
    "LVR_000018_II": {"title": "Le Mondain Égyptien, Part II", "year": 1943},
    "LVR_000164": {"title": "Annuaire des Juifs d'Égypte et du Proche-Orient", "year": 1942},
    "LVR_000249": {"title": "Annuaire des Juifs d'Égypte et du Proche-Orient", "year": 1943},
    "LVR_000251": {"title": "Les Juifs en Égypte", "year": 1938},
    "LVR_000315": {"title": "L'Annuaire Mondain", "year": 1950},
    "LVR_000084_IV": {"title": "Egyptian Directory", "year": 1913},
}


def adjacent_url(cealex_id: str) -> str:
    """Direct PDF URL for one of the adjacent digitised volumes."""
    return CEALEX_PDF.format(cealex_id=cealex_id)


def edition(year: int) -> Edition:
    if year not in EDITIONS:
        raise KeyError(f"{year} is not one of the waves {WAVES}")
    return EDITIONS[year]


def available_waves() -> list[int]:
    """Waves whose source is actually present on disk."""
    return [y for y in WAVES if EDITIONS[y].pdf_sources()]
