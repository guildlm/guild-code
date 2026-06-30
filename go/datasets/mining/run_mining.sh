#!/usr/bin/env bash
# Orchestrate the GitHub Go mining pipeline end to end ($0, all free-tier).
#
#   select quality repos -> clone (bounded depth) -> DAPT corpus + git-history SFT
#
# Usage:
#   ./run_mining.sh                 # full run (thousands of repos; takes a while)
#   ./run_mining.sh smoke           # tiny validation run (10 small repos)
#   MIN_STARS=300 MAX_REPOS=800 ./run_mining.sh
#
# Env knobs (with defaults):
#   MIN_STARS=100  MAX_REPOS=0(all)  DEPTH=400  JOBS=6  MAX_SIZE_KB=0(no cap)
#   MAX_COMMITS=400  MAX_FILES=1
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-python3}"

MODE="${1:-full}"
if [[ "$MODE" == "smoke" ]]; then
  MIN_STARS="${MIN_STARS:-8000}"; MAX_REPOS="${MAX_REPOS:-25}"
  MAX_SIZE_KB="${MAX_SIZE_KB:-60000}"; LIMIT_FLAG="--limit 12"
  LICENSES="--licenses mit,apache-2.0 --max-pages 1"
  REPOS_FILE="repos.smoke.jsonl"
else
  MIN_STARS="${MIN_STARS:-100}"; MAX_REPOS="${MAX_REPOS:-0}"
  MAX_SIZE_KB="${MAX_SIZE_KB:-0}"; LIMIT_FLAG=""
  LICENSES=""
  REPOS_FILE="repos.jsonl"
fi
DEPTH="${DEPTH:-400}"; JOBS="${JOBS:-6}"
MAX_COMMITS="${MAX_COMMITS:-400}"; MAX_FILES="${MAX_FILES:-1}"

echo "=== [1/4] select repos (min_stars=$MIN_STARS max_repos=$MAX_REPOS) ==="
$PY select_repos.py --min-stars "$MIN_STARS" --max-repos "$MAX_REPOS" \
    $LICENSES --out "$REPOS_FILE"

echo "=== [2/4] clone (depth=$DEPTH jobs=$JOBS max_size_kb=$MAX_SIZE_KB) ==="
$PY clone_repos.py --repos "$REPOS_FILE" --depth "$DEPTH" --jobs "$JOBS" \
    ${MAX_SIZE_KB:+--max-size-kb "$MAX_SIZE_KB"} $LIMIT_FLAG

echo "=== [3/4] build DAPT corpus ==="
$PY build_dapt_corpus.py --merge-stdlib --sample 30

echo "=== [4/4] mine git history (commits -> SFT) ==="
$PY mine_git_history.py --max-commits "$MAX_COMMITS" --max-files "$MAX_FILES" \
    --sample 5

echo "=== done. outputs: go_dapt_mined.jsonl, mined_dev.jsonl, mined_bugfix.jsonl ==="
