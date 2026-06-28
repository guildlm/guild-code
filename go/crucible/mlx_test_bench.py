# -*- coding: utf-8 -*-
"""Score an MLX go-test specialist on the mutation benchmark, locally, $0.

For each task the model is asked to write a test for a function; the test scores
a point only if it PASSES against the correct implementation AND FAILS against
the planted buggy mutant — i.e. it genuinely catches the bug. Same local-MLX
approach as mlx_bench.py; no GGUF/Ollama needed.

Usage (with the mlx venv's python):
    python mlx_test_bench.py --adapter ~/Desktop/Personal/Dev/guildlm/.mlx-adapters/go-test
    python mlx_test_bench.py            # base (no adapter)
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
    "You are a Go test-writing specialist. Output one complete Go test file in a "
    "single ```go block, package sandbox, standard library testing only, no "
    "commentary. Do not redefine the function under test."
)


def extract_code(text: str) -> str:
    m = _FENCE.search(text)
    return (m.group(1) if m else text).strip() + "\n"


def _go_test(impl: str, test: str) -> bool:
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "go.mod"), "w").write(f"module {MODULE}\n\ngo 1.23\n")
        open(os.path.join(d, "impl.go"), "w").write(impl)
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
    ap.add_argument("--adapter", default=None)
    ap.add_argument(
        "--bench", default=os.path.join(os.path.dirname(__file__), "data", "go_test_bench.jsonl")
    )
    ap.add_argument("--max-tokens", type=int, default=700)
    args = ap.parse_args()

    from mlx_lm import generate, load

    model, tokenizer = load(args.model, adapter_path=args.adapter)
    label = os.path.basename(args.adapter) if args.adapter else "BASE (untuned)"
    tasks = [json.loads(l) for l in open(args.bench)]
    print(f"mlx test-bench (mutation): {len(tasks)} tasks · model={label}\n")

    passed, detail = 0, []
    for t in tasks:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": t["prompt"]}]
        prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        try:
            test = extract_code(generate(model, tokenizer, prompt=prompt, max_tokens=args.max_tokens, verbose=False))
            # Catches the bug iff it passes on correct AND fails on the mutant.
            ok = _go_test(t["metadata"]["correct"], test) and not _go_test(t["metadata"]["mutant"], test)
        except Exception as e:
            ok = False
            detail.append(f"{t['id']}:ERR({type(e).__name__})")
            continue
        passed += ok
        detail.append(f"{'+' if ok else '-'}{t['id']}")

    print(f"{label}: bug-catch@1 = {passed}/{len(tasks)}  [{' '.join(detail)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
