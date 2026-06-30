#!/usr/bin/env bash
# Measure a mined-data specialist after training — the honest A/B vs the base /
# the published v1, on both the fast unit bench and the real project_bench.
#
# Run AFTER training finishes (don't contend the GPU with a running train).
#
# Usage:
#   ./eval_mined.sh go-dev-mined          # unit bench A/B + project_bench maintain
#   EVAL_LIMIT=3 ./eval_mined.sh go-dev-mined   # quick: only 3 projects
#
# What it does:
#   1) crucible mlx_bench.py — go_dev unit bench, adapter vs BASE (real `go test`).
#      Fast, objective, but NOISE-dominated (per-role SFT barely moves it; the
#      base ~19/24). Sanity check, not the headline.
#   2) builder project_bench.py maintain — serve the adapter, run the Builder loop
#      on the verified multi-file projects. THE headline metric: the v1 plateau
#      was maintain 0/8. Does real-data SFT beat it?
set -euo pipefail

NAME="${1:?usage: eval_mined.sh <adapter-name>  (e.g. go-dev-mined)}"
REPO="$HOME/Desktop/Personal/Dev/guildlm"
BASE="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
VENV="${GUILDLM_MLX_VENV:-$REPO/.mlx-venv}"
ADAPTERS="${GUILDLM_ADAPTERS_DIR:-$REPO/.mlx-adapters}"
ADAPTER="$ADAPTERS/$NAME"
PORT="${EVAL_PORT:-8080}"
LIMIT="${EVAL_LIMIT:-8}"

[[ -d "$ADAPTER" ]] || { echo "no adapter at $ADAPTER" >&2; exit 1; }

echo "######## 1) UNIT BENCH A/B (crucible mlx_bench, real go test) ########"
echo "---- $NAME ----"
"$VENV/bin/python" "$REPO/guild-code/go/crucible/mlx_bench.py" \
  --model "$BASE" --adapter "$ADAPTER" || echo "(unit bench failed)"
echo "---- BASE (untuned, for A/B) ----"
"$VENV/bin/python" "$REPO/guild-code/go/crucible/mlx_bench.py" \
  --model "$BASE" || echo "(base bench failed)"

echo ""
echo "######## 2) PROJECT_BENCH maintain (serve + Builder loop) ########"
echo "serving $NAME on :$PORT ..."
GUILDLM_ADAPTERS_DIR="$ADAPTERS" \
  "$REPO/guild-code/go/tools/serve_specialist.sh" "$NAME" "$PORT" \
  > "/tmp/serve_${NAME}.log" 2>&1 &
SERVE_PID=$!
trap 'kill $SERVE_PID 2>/dev/null || true' EXIT

# wait for the server to accept connections
for _ in $(seq 1 60); do
  curl -sf "http://localhost:$PORT/v1/models" >/dev/null 2>&1 && break
  sleep 2
done

cd "$REPO/builder"
.venv/bin/python project_bench.py \
  --projects ../guild-code/go/projects \
  --base-url "http://localhost:$PORT/v1" --model "$BASE" \
  --capabilities maintain --limit "$LIMIT" || echo "(project_bench failed)"

echo ""
echo "######## done. compare maintain vs the v1 baseline (0/8). ########"
