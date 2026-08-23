# Getting a volume to the pipeline when the host can't reach CEAlex

If the machine running the pipeline is behind an egress policy that blocks
`bdd.cealex.org`, a human has to fetch the volume and hand it over. Two
couriers were tested; **git is the better one.**

## What was actually measured

| Route | Fidelity | Size limit | Verdict |
|---|---|---|---|
| **git** (commit to the repo) | exact bytes | 100 MB/file (50 MB warning) | **use this** |
| Drive `download_file_content` | exact bytes (base64) | **10 MB hard cap** | works, needs splitting |
| Drive `read_file_content` | **truncated text** | none | **do not use** |

`read_file_content` looks attractive because it has no size cap, but on a
15.7 MB test volume it returned ~147k characters and stopped at page 80 of a
roughly 400-page document, with no page markers. It would silently drop most
of a volume *and* destroy the `source_page` provenance. The pipeline rejects
its output rather than let it be mistaken for a real download.

## Route 1 — git (recommended)

```bash
# on a machine that can reach CEAlex
curl -L -o politi_1932.pdf \
  https://bdd.cealex.org/diffusion/etud_anc_alex/LVR_000323_w.pdf

# if it is over ~50 MB, split it first
pip install -e . && politi split --pdf politi_1932.pdf --year 1932 --max-mb 45

git add data/incoming/ && git commit -m "Add 1932 annuaire" && git push
```

Then, on the pipeline host:

```bash
git pull
politi extract --year 1932
politi build
```

`data/incoming/` is deliberately **not** git-ignored — it is the drop point.
`data/raw/` stays ignored, for volumes fetched directly.

**Two things to weigh before committing scans.** Large binaries in git history
are permanent: every future clone pays for them, and removing them later means
rewriting history. And CEAlex's terms govern redistribution — check whether the
repository is public before pushing their scans into it. Neither is a reason
not to do it; both are reasons to do it deliberately.

## Route 2 — Google Drive

Upload the volume to Drive, **split into parts under 10 MB**, since the
connector refuses anything larger:

```bash
politi split --pdf politi_1932.pdf --year 1932 --max-mb 9
```

The agent then downloads each part and lands it:

```bash
politi drive-import --result <saved-tool-result.json> --year 1932 --part 1
```

## Splitting is safe

Parts are read back as **one continuous document**: page numbering runs across
the whole volume, so a volume split for transport still yields citable page
numbers. This is tested against a real 251-page PDF split six ways — all 251
pages come back with identical text and unbroken numbering
(`tests/test_drive.py`).

Name parts `politi_<year>_partNN.pdf`; the pipeline finds them in either
`data/raw/` or `data/incoming/` and needs no further configuration.

Page numbers are positions in the scan, not the printed folio.
