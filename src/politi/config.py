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


# The CEAlex digital library serves this collection as OCR'd, text-searchable
# PDFs under https://bdd.cealex.org/diffusion/etud_anc_alex/<ID>_w.pdf
CEALEX_PDF = "https://bdd.cealex.org/diffusion/etud_anc_alex/{cealex_id}_w.pdf"
CEALEX_INDEX = "https://bdd.cealex.org/ressources-documentaires/lvr_i.php"

EDITIONS: dict[int, Edition] = {
    1932: Edition(
        year=1932, edition=3, edition_verified=False, place="Le Caire",
        cealex_id="LVR_000323",
        url=CEALEX_PDF.format(cealex_id="LVR_000323"),
        note="Direct PDF confirmed in the CEAlex digital library.",
    ),
    1938: Edition(
        year=1938, edition=9, edition_verified=False, place="Le Caire",
        cealex_id=None, url=None,
        note="Not yet located online; resolve via the CEAlex LVR index.",
    ),
    1942: Edition(
        year=1942, edition=13, edition_verified=False, place="Le Caire",
        cealex_id=None, url=None,
        note="Not yet located online; resolve via the CEAlex LVR index.",
    ),
    1947: Edition(
        year=1947, edition=18, edition_verified=True, place="Alexandrie",
        cealex_id=None, url=None,
        note="18e édition, confirmed by the CEAlex catalogue record; "
             "LVR identifier not yet resolved.",
    ),
    1950: Edition(
        year=1950, edition=21, edition_verified=True, place="Alexandrie",
        cealex_id=None, url=None,
        note="21e édition, confirmed by the CEAlex catalogue record; "
             "LVR identifier not yet resolved.",
    ),
}


def edition(year: int) -> Edition:
    if year not in EDITIONS:
        raise KeyError(f"{year} is not one of the waves {WAVES}")
    return EDITIONS[year]


def available_waves() -> list[int]:
    """Waves whose PDF is actually present on disk."""
    return [y for y in WAVES if EDITIONS[y].pdf_path.exists()]
