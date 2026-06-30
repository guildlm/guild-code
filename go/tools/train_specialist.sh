#!/usr/bin/env bash
# Train a GuildLM Go specialist LoRA adapter locally via Apple MLX ($0).
#
# Works for both SFT (chat {"messages"} dirs) and DAPT/continued-pretraining
# (raw {"text"} dirs) — mlx_lm auto-detects the format from the data. Mirrors the
# env conventions of serve_specialist.sh so a trained adapter serves directly:
#   GUILDLM_MLX_BASE, GUILDLM_ADAPTERS_DIR, GUILDLM_MLX_VENV
#
# Usage:
#   ./train_specialist.sh <name> <data_dir> [iters] [layers] [lr] [maxseq] [batch]
#
# Examples (mined real-data recipe):
#   # role-SFT go-dev on real git-history edits (dev+bugfix)
#   ./train_specialist.sh go-dev-mined  ../datasets/mining/... /godev   1500
#   # DAPT continued-pretraining on the 291M-token real Go corpus
#   ./train_specialist.sh go-dapt       .../dapt  4000 16 1e-4 2048 2
#
# Then serve it: ./serve_specialist.sh <name> [port]
set -euo pipefail

NAME="${1:?usage: train_specialist.sh <name> <data_dir> [iters] [layers] [lr] [maxseq] [batch]}"
DATA="${2:?data dir with train.jsonl/valid.jsonl}"
ITERS="${3:-1500}"
LAYERS="${4:-16}"
LR="${5:-1e-4}"
MAXSEQ="${6:-2048}"
BATCH="${7:-1}"

BASE_MODEL="${GUILDLM_MLX_BASE:-mlx-community/Qwen2.5-Coder-7B-Instruct-4bit}"
ADAPTERS_DIR="${GUILDLM_ADAPTERS_DIR:-$HOME/Desktop/Personal/Dev/guildlm/.mlx-adapters}"
VENV="${GUILDLM_MLX_VENV:-$HOME/Desktop/Personal/Dev/guildlm/.mlx-venv}"

if [[ ! -f "$DATA/train.jsonl" ]]; then
  echo "no train.jsonl in $DATA — run prepare_mlx_data.py first" >&2
  exit 1
fi
OUT="$ADAPTERS_DIR/$NAME"
mkdir -p "$OUT"

# grad-checkpoint trades compute for memory — only worth it when memory is tight.
# Off by default (M1 Max has headroom; saw peak ~11GB at seq 4096) for speed.
# Set GUILDLM_GRAD_CKPT=1 to re-enable for very long sequences / OOM.
# (scalar, not array — macOS bash 3.2 errors on empty "${arr[@]}" under set -u)
GC_FLAG=""
[[ "${GUILDLM_GRAD_CKPT:-0}" == "1" ]] && GC_FLAG="--grad-checkpoint"

echo "Training '$NAME'  base=$BASE_MODEL"
echo "  data=$DATA  iters=$ITERS layers=$LAYERS lr=$LR maxseq=$MAXSEQ batch=$BATCH"
echo "  grad-checkpoint=${GUILDLM_GRAD_CKPT:-0}  -> adapter: $OUT"

exec "$VENV/bin/python" -m mlx_lm lora \
  --model "$BASE_MODEL" --train --data "$DATA" \
  --adapter-path "$OUT" \
  --fine-tune-type lora --num-layers "$LAYERS" \
  --iters "$ITERS" --batch-size "$BATCH" --learning-rate "$LR" \
  --max-seq-length "$MAXSEQ" $GC_FLAG \
  --steps-per-report 25 --steps-per-eval 200 --save-every 200 --val-batches 20
