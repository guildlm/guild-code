#!/usr/bin/env bash
# bridge_dapt.sh — bring a Kaggle-trained DAPT LoRA adapter home to MLX.
#
# Takes an HF PEFT adapter (trained by anvil/notebooks/kaggle_go_dapt.ipynb),
# merges it into the fp16 base on CPU, converts the merged model to 4-bit MLX,
# and leaves it where serve_specialist.sh / the Builder stack can serve it.
#
# Usage:
#   ./bridge_dapt.sh <adapter>            # HF repo id (e.g. guildlm/go-dapt-7b-lora)
#   ./bridge_dapt.sh /path/to/adapter_dir # or a local adapter directory
#
# Output: $REPO/.mlx-fused/go-dapt-7b-4bit  (MLX, 4-bit, ~4GB)
# Needs ~35GB free disk for the intermediate fp16 base+merge (cleaned up after).
set -euo pipefail

ADAPTER="${1:?usage: bridge_dapt.sh <hf-repo-id-or-local-adapter-dir>}"
REPO="${GUILDLM_REPO:-$HOME/Desktop/Personal/Dev/guildlm}"
VENV="$REPO/.mlx-venv"
PY="$VENV/bin/python"
BASE="Qwen/Qwen2.5-Coder-7B-Instruct"
MERGED="$REPO/.mlx-fused/go-dapt-7b-merged"
OUT="$REPO/.mlx-fused/go-dapt-7b-4bit"

[ -x "$PY" ] || { echo "no venv at $VENV"; exit 1; }
"$PY" -c "import peft" 2>/dev/null || "$VENV/bin/pip" install -q peft

if [ ! -d "$ADAPTER" ]; then
  echo "==> downloading adapter $ADAPTER from the HF Hub"
  DL="$REPO/.mlx-fused/$(basename "$ADAPTER")-adapter"
  "$PY" -c "
from huggingface_hub import snapshot_download
print(snapshot_download('$ADAPTER', local_dir='$DL'))"
  ADAPTER="$DL"
fi

echo "==> merging adapter into $BASE (fp16, CPU — needs RAM+patience)"
"$PY" - "$ADAPTER" "$MERGED" <<'EOF'
import sys
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

adapter, out = sys.argv[1], sys.argv[2]
base = "Qwen/Qwen2.5-Coder-7B-Instruct"
model = AutoModelForCausalLM.from_pretrained(
    base, torch_dtype=torch.float16, device_map="cpu"
)
model = PeftModel.from_pretrained(model, adapter)
model = model.merge_and_unload()
model.save_pretrained(out)
AutoTokenizer.from_pretrained(base).save_pretrained(out)
print("merged ->", out)
EOF

echo "==> converting merged model to 4-bit MLX"
rm -rf "$OUT"
"$PY" -m mlx_lm convert --hf-path "$MERGED" --mlx-path "$OUT" -q

echo "==> cleaning up the fp16 intermediate"
rm -rf "$MERGED"

echo "DONE: $OUT"
echo "Serve it:  $PY -m mlx_lm server --model $OUT --port 8080"
echo "Bench it:  crucible mlx_bench against the served model (base was 19/24)"
