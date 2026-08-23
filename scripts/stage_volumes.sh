#!/usr/bin/env bash
# Download the digitised annuaire volumes and stage them for hand-off.
#
# Run this on any machine with ordinary network access. It downloads what is
# available, splits anything too large to travel, and leaves the parts in
# data/incoming/ ready to commit. See docs/HANDOFF.md.
#
#   ./scripts/stage_volumes.sh          # stage for git (45 MB parts)
#   ./scripts/stage_volumes.sh --drive  # stage for Google Drive (9 MB parts)

set -euo pipefail

MAX_MB=45
case "${1:-}" in
  --drive) MAX_MB=9; echo "staging for Google Drive (${MAX_MB} MB parts)" ;;
  --help|-h) sed -n '2,9p' "$0"; exit 0 ;;
  "") echo "staging for git (${MAX_MB} MB parts)" ;;
  *) echo "unknown option: $1" >&2; exit 2 ;;
esac

cd "$(dirname "$0")/.."
mkdir -p data/incoming

# Only 1932 is digitised. The other waves appear to exist in print only —
# docs/SOURCES.md records the search behind that and where to ask.
declare -A VOLUMES=(
  [1932]="https://bdd.cealex.org/diffusion/etud_anc_alex/LVR_000323_w.pdf"
)

python3 -c 'import politi' 2>/dev/null || {
  echo "installing the pipeline..."; pip install -e . --quiet; }

for year in "${!VOLUMES[@]}"; do
  url="${VOLUMES[$year]}"
  target="data/incoming/politi_${year}.pdf"
  if [[ -f "$target" ]]; then
    echo "[$year] already staged"
  else
    echo "[$year] downloading..."
    curl -fsSL --retry 4 --retry-delay 2 -o "$target" "$url" || {
      echo "[$year] download failed — check the URL in docs/SOURCES.md" >&2
      rm -f "$target"; continue; }
  fi

  size_mb=$(( $(wc -c < "$target") / 1000000 ))
  echo "[$year] ${size_mb} MB"
  if (( size_mb > MAX_MB )); then
    echo "[$year] splitting into ${MAX_MB} MB parts..."
    python3 -m politi split --pdf "$target" --year "$year" \
      --out data/incoming --max-mb "$MAX_MB"
    rm -f "$target"   # keep only the parts, so nothing oversized gets committed
  fi
done

echo
if compgen -G "data/incoming/*.pdf" > /dev/null; then
  echo "staged in data/incoming/:"
  ls -lh data/incoming/*.pdf
  echo
  echo "next:  git add data/incoming/ && git commit -m 'Add annuaire volumes' && git push"
else
  echo "nothing staged. If the download was blocked, fetch the volume by hand"
  echo "and drop it at data/incoming/politi_<year>.pdf — see docs/SOURCES.md."
  exit 1
fi
