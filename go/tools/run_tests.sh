#!/usr/bin/env bash
# Run Crucible eval suites for the Code Guild's Go specialists.
#
# Usage:
#   go/tools/run_tests.sh [specialist ...]
#
# With no arguments it runs every specialist suite. Each argument must be one of:
#   go_generator  go_reviewer  go_tester  go_explainer
#
# Environment:
#   CRUCIBLE_DIR   Path to the crucible checkout (default: ../../../crucible).
#   Functional suites (go_generator, go_tester) require Docker for the sandbox;
#   judge suites (go_reviewer, go_explainer) run offline by default.
set -euo pipefail

GUILD_GO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CRUCIBLE_DIR="${CRUCIBLE_DIR:-$GUILD_GO_DIR/../../crucible}"

ALL_SPECIALISTS="go_generator go_reviewer go_tester go_explainer"
SPECIALISTS=("$@")
if [ "$#" -eq 0 ]; then
  # shellcheck disable=SC2206
  SPECIALISTS=($ALL_SPECIALISTS)
fi

if [ ! -d "$CRUCIBLE_DIR" ]; then
  echo "error: crucible not found at $CRUCIBLE_DIR (set CRUCIBLE_DIR)" >&2
  exit 1
fi

echo "GuildLM Code Guild — Go eval runner"
echo "crucible: $CRUCIBLE_DIR"

status=0
for specialist in "${SPECIALISTS[@]}"; do
  suite="$GUILD_GO_DIR/crucible/$specialist.yaml"
  if [ ! -f "$suite" ]; then
    echo "skip: no suite for '$specialist' ($suite)" >&2
    status=1
    continue
  fi
  echo
  echo "== $specialist =="
  # crucible exposes its runner as a console script; fall back to the module.
  if command -v crucible >/dev/null 2>&1; then
    ( cd "$CRUCIBLE_DIR" && crucible run "$suite" ) || status=1
  else
    ( cd "$CRUCIBLE_DIR" && python3 -m src.cli run "$suite" ) || status=1
  fi
done

exit "$status"
