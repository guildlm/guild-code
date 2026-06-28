# -*- coding: utf-8 -*-
"""Score an MLX-trained Go specialist on a held-out benchmark, locally, $0.

Runs the go_dev_bench (or go_edit_bench) prompts through an mlx_lm model +
optional LoRA adapter, extracts the Go, drops it next to each hidden test, runs
`go test`, and reports pass@1 — the same scoring as bench_compare.py but driven
by a local MLX model instead of an Ollama endpoint, so a freshly-trained adapter
can be evaluated immediately without GGUF/Ollama conversion.

Usage (with the mlx venv's python):
    python mlx_bench.py --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
        --adapter ~/Desktop/Personal/Dev/guildlm/.mlx-adapters/go-dev
    # base only (no --adapter) gives the untuned baseline for a fair A/B.
"""
import argparse
import json
import os
import re
import subprocess
import tempfile

MODULE = "sandbox"
_FENCE = re.compile(r"```(?:go|golang)?\s*\n(.*?)```", re.DOTALL)

SYSTEM = (
    "You are a Go development specialist. Output one complete Go file in a single "
    "```go block, package sandbox, standard library only, no commentary."
)


def extract_code(text: str) -> str:
    m = _FENCE.search(text)
    return (m.group(1) if m else text).strip() + "\n"


def runs_green(code: str, test: str) -> bool:
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "go.mod"), "w").write(f"module {MODULE}\n\ngo 1.23\n")
        open(os.path.join(d, "impl.go"), "w").write(code)
        open(os.path.join(d, "impl_test.go"), "w").write(test)
        env = dict(os.environ, GOPROXY="off", GOFLAGS="-mod=mod")
        try:
            p = subprocess.run(
                ["go", "test", "./..."], cwd=d, capture_output=True, text=True, timeout=60, env=env
            )
        except subprocess.TimeoutExpired:
            return False
        return p.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")
    ap.add_argument("--adapter", default=None, help="LoRA adapter path (omit for base)")
    ap.add_argument(
        "--bench", default=os.path.join(os.path.dirname(__file__), "data", "go_dev_bench.jsonl")
    )
    ap.add_argument("--max-tokens", type=int, default=900)
    args = ap.parse_args()

    from mlx_lm import generate, load

    model, tokenizer = load(args.model, adapter_path=args.adapter)
    label = f"{os.path.basename(args.adapter)}" if args.adapter else "BASE (untuned)"

    tasks = [json.loads(l) for l in open(args.bench)]
    print(f"mlx bench: {len(tasks)} tasks · model={label}\n")

    passed, detail = 0, []
    for t in tasks:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": t["prompt"]}]
        prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        try:
            out = generate(model, tokenizer, prompt=prompt, max_tokens=args.max_tokens, verbose=False)
            ok = runs_green(extract_code(out), t["metadata"]["tests"])
        except Exception as e:  # generation/runtime error counts as a miss
            ok = False
            detail.append(f"{t['id']}:ERR({type(e).__name__})")
            continue
        passed += ok
        detail.append(f"{'+' if ok else '-'}{t['id']}")

    print(f"{label}: pass@1 = {passed}/{len(tasks)}  [{' '.join(detail)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
