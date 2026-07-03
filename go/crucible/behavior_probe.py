# -*- coding: utf-8 -*-
"""Probe CHAT-BEHAVIOUR integrity of an MLX model/adapter, locally, $0.

DAPT recipe 1 taught us the failure mode that unit benches under-report:
continued pretraining on raw Go makes the instruct model stop emitting
<|im_end|> and closing fences — it rambles endless Go. This probe measures
exactly that, fast (a handful of prompts, no go toolchain):

  stopped   — generation ended before max_tokens (the model emitted EOS)
  fenced    — the reply contains a properly CLOSED ```go block
  len       — output length in chars (ballooning = the rambling signature)

Usage:
  python behavior_probe.py --model <mlx-model-or-path> [--adapter <dir>] [--n 6]

Exit code 0 iff every probed prompt both stopped and closed its fence.
"""
import argparse
import json
import os
import re

SYSTEM = (
    "You are a Go development specialist. Output one complete Go file in a single "
    "```go block, package sandbox, standard library only, no commentary."
)
_CLOSED_FENCE = re.compile(r"```(?:go|golang)?\s*\n.*?```", re.DOTALL)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")
    ap.add_argument("--adapter", default=None)
    ap.add_argument(
        "--bench", default=os.path.join(os.path.dirname(__file__), "data", "go_dev_bench.jsonl")
    )
    ap.add_argument("--n", type=int, default=6, help="prompts to probe")
    ap.add_argument("--max-tokens", type=int, default=900)
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
    label = os.path.basename(args.adapter) if args.adapter else "BASE"
    tasks = [json.loads(l) for l in open(args.bench)][: args.n]

    ok_all = True
    print(f"behavior probe · model={label} · {len(tasks)} prompts\n")
    for t in tasks:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": t["prompt"]}]
        prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        out = generate(model, tokenizer, prompt=prompt, max_tokens=args.max_tokens, verbose=False)
        n_tok = len(tokenizer.encode(out))
        stopped = n_tok < args.max_tokens  # hit EOS before the cap
        fenced = bool(_CLOSED_FENCE.search(out))
        ok = stopped and fenced
        ok_all &= ok
        print(f"  {'OK ' if ok else 'BAD'} {t['id']:<18} stopped={stopped} fenced={fenced} len={len(out)}")
    print(f"\n{label}: {'CHAT BEHAVIOUR INTACT' if ok_all else 'CHAT BEHAVIOUR DAMAGED'}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
