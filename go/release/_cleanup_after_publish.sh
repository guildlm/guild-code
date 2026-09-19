#!/bin/sh
# Deletion gate for the local model archive. Deletes NOTHING unless the HF archive
# (guildlm/go-lora-adapters) verifies byte-complete against the local adapters and
# Kaggle checkpoints. Then removes the two folders that are pure derivatives of it:
#   .mlx-fused/   (every fused model = mlx_lm.fuse(base, adapter), deterministic)
#   .kaggle-dapt/ (HF-PEFT checkpoints, uploaded verbatim under kaggle-dapt/)
# .mlx-adapters/ is KEPT on purpose (5.5 GB): it is the seed set every bench A/B needs.
set -e
cd "$(dirname "$0")"
PY="${PY:-/Library/Frameworks/Python.framework/Versions/3.13/bin/python3}"
"$PY" publish_adapters.py --verify-only || { echo "REFUSING to delete: remote archive incomplete"; exit 1; }
R=../../..
du -sh "$R/.mlx-fused" "$R/.kaggle-dapt" 2>/dev/null || true
rm -rf "$R/.mlx-fused" "$R/.kaggle-dapt"
echo "deleted .mlx-fused and .kaggle-dapt — all reproducible from https://huggingface.co/guildlm/go-lora-adapters"
