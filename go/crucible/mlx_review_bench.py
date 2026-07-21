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
    ap.add_argument("--min-keywords", type=int, default=1,
                    help="how many concept keywords a review must name to score. The audit "
                         "found generic keywords (loop/once/leak) that a rambling review can "
                         "hit by chance; >=2 is the stricter rule. Default 1 keeps every "
                         "recorded number comparable — do not change the default.")
    ap.add_argument("--save-generations", metavar="PATH",
                    help="write each review plus the keywords it matched to JSONL, so a "
                         "scoring-rule change can be re-measured without a model run")
    args = ap.parse_args()

    from mlx_lm import generate, load

    model, tokenizer = load(args.model, adapter_path=args.adapter)
    # The mlx-community Qwen configs carry eos_token_id=<|endoftext|> only, so
    # generation never stops at <|im_end|> — tuned adapters (which stop emitting
    # <|endoftext|>) then ramble to max_tokens on every prompt. Register the
    # chat EOS explicitly so stopping works for base AND adapters.
    im_end = tokenizer.encode("<|im_end|>")
    if len(im_end) == 1:
        tokenizer.eos_token_ids.add(im_end[0])
    label = os.path.basename(args.adapter) if args.adapter else "BASE (untuned)"
    tasks = [json.loads(l) for l in open(args.bench)]
    print(f"mlx review-bench: {len(tasks)} tasks · model={label}\n")

    passed, detail, saved = 0, [], []
    for t in tasks:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": t["prompt"]}]
        prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        try:
            out = generate(model, tokenizer, prompt=prompt, max_tokens=args.max_tokens, verbose=False).lower()
            hits = [k for k in t["metadata"]["keywords"] if k.lower() in out]
            ok = len(hits) >= args.min_keywords
        except Exception as e:
            ok = False
            detail.append(f"{t['id']}:ERR({type(e).__name__})")
            continue
        passed += ok
        detail.append(f"{'+' if ok else '-'}{t['id']}")
        if args.save_generations:
            saved.append({"id": t["id"], "label": label, "verdict": ok, "matched": hits,
                          "keywords": t["metadata"]["keywords"], "review": out})

    rule = "" if args.min_keywords == 1 else f" (>= {args.min_keywords} keywords)"
    print(f"{label}: identify@1{rule} = {passed}/{len(tasks)}  [{' '.join(detail)}]")
    if args.save_generations:
        with open(args.save_generations, "w") as f:
            for row in saved:
                f.write(json.dumps(row) + "\n")
        print(f"  wrote {len(saved)} reviews -> {args.save_generations} (re-scorable model-free)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
