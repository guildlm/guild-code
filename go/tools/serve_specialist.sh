#!/usr/bin/env bash
# Serve a trained GuildLM Go specialist as an OpenAI-compatible endpoint, $0,
# locally via Apple MLX — the bridge from a trained LoRA adapter to a model the
# Builder (or any OpenAI-compatible client) can actually call. No GGUF, no Ollama.
#
# Usage:
#   ./serve_specialist.sh go-dev   [port]   # default port 8080
#   ./serve_specialist.sh go-test  8081
#   ./serve_specialist.sh go-review 8082
#
# Then point the Builder at it:
#   guildlm-build --spec specs/demo-small.yaml --out ./generated/x \
#     --model guildlm --base-url http://localhost:8080/v1
#
# Or wire role-routing (dev writes impl, test specialist writes _test.go) by
# serving go-dev on 8080 and go-test on 8081, then:
#   guildlm-build ... --base-url http://localhost:8080/v1 \
#     --test-model guildlm --test-base-url http://localhost:8081/v1
set -euo pipefail

SPECIALIST="${1:?usage: serve_specialist.sh <go-dev|go-test|go-review> [port]}"
PORT="${2:-8080}"
BASE_MODEL="${GUILDLM_MLX_BASE:-mlx-community/Qwen2.5-Coder-7B-Instruct-4bit}"
ADAPTERS_DIR="${GUILDLM_ADAPTERS_DIR:-$HOME/Desktop/Personal/Dev/guildlm/.mlx-adapters}"
VENV="${GUILDLM_MLX_VENV:-$HOME/Desktop/Personal/Dev/guildlm/.mlx-venv}"

ADAPTER="$ADAPTERS_DIR/$SPECIALIST"
if [[ ! -d "$ADAPTER" ]]; then
  echo "adapter not found: $ADAPTER" >&2
  echo "trained adapters live under \$GUILDLM_ADAPTERS_DIR ($ADAPTERS_DIR)" >&2
  exit 1
fi

echo "Serving $SPECIALIST  (base=$BASE_MODEL)  on http://localhost:$PORT/v1"
echo "  -> use with the Builder: --base-url http://localhost:$PORT/v1"
exec "$VENV/bin/python" -m mlx_lm server \
  --model "$BASE_MODEL" \
  --adapter-path "$ADAPTER" \
  --port "$PORT"
