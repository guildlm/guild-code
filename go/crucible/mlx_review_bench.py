# -*- coding: utf-8 -*-
"""Score an MLX go-review specialist on the review benchmark, locally, $0.

For each task the model reviews buggy Go; it scores a point if its review names
the real defect — measured by whether the output mentions any of the task's
concept keywords (case-insensitive). Heuristic but objective and reproducible.
This is the FAIR benchmark for a review model (vs the edit benchmark, which asks
for a corrected file — a different job).

Usage (with the mlx venv's python):
    python mlx_review_bench.py --adapter ~/Desktop/Personal/Dev/guildlm/.mlx-adapters/go-review
    python mlx_review_bench.py            # base (no adapter)
"""
import argparse
import json
import os

SYSTEM = (
    "You are a Go code reviewer. Identify the single real bug in the code and "
    "explain precisely what is wrong and why. Be specific and name the defect."
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")
    ap.add_argument("--adapter", default=None)
    ap.add_argument(
        "--bench", default=os.path.join(os.path.dirname(__file__), "data", "go_review_bench.jsonl")
    )
    ap.add_argument("--max-tokens", type=int, default=400)
    args = ap.parse_args()

    from mlx_lm import generate, load

    model, tokenizer = load(args.model, adapter_path=args.adapter)
    label = os.path.basename(args.adapter) if args.adapter else "BASE (untuned)"
    tasks = [json.loads(l) for l in open(args.bench)]
    print(f"mlx review-bench: {len(tasks)} tasks · model={label}\n")

    passed, detail = 0, []
    for t in tasks:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": t["prompt"]}]
        prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        try:
            out = generate(model, tokenizer, prompt=prompt, max_tokens=args.max_tokens, verbose=False).lower()
            ok = any(k.lower() in out for k in t["metadata"]["keywords"])
        except Exception as e:
            ok = False
            detail.append(f"{t['id']}:ERR({type(e).__name__})")
            continue
        passed += ok
        detail.append(f"{'+' if ok else '-'}{t['id']}")

    print(f"{label}: identify@1 = {passed}/{len(tasks)}  [{' '.join(detail)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
