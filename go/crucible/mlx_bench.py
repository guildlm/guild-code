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
import sys
import tempfile

MODULE = "sandbox"

# Shared with the test bench rather than copied: these helpers encode harness decisions
# (what counts as truncated, how a missing import is repaired) that must not drift between
# the two benches. Importing is cheap — mlx_test_bench imports mlx_lm inside main().
from mlx_test_bench import _goimports, _repair_imports, _truncated, extract_code  # noqa: E402

SYSTEM = (
    "You are a Go development specialist. Output one complete Go file in a single "
    "```go block, package sandbox, standard library only, no commentary."
)


def compiles(code: str) -> bool:
    """Is this valid Go at all? Splits a pass@1 miss into a mechanical failure (did not
    build) and a real one (built, wrong behaviour) — the same decomposition that showed
    the test bench was scoring validity rather than skill."""
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "go.mod"), "w").write(f"module {MODULE}\n\ngo 1.23\n")
        open(os.path.join(d, "impl.go"), "w").write(code)
        env = dict(os.environ, GOPROXY="off", GOFLAGS="-mod=mod")
        try:
            p = subprocess.run(["go", "build", "./..."], cwd=d, capture_output=True,
                               text=True, timeout=60, env=env)
        except subprocess.TimeoutExpired:
            return False
        return p.returncode == 0


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
    ap.add_argument("--temp", type=float, default=0.0,
                    help="sampling temperature; 0 = greedy/deterministic (default), "
                         ">0 reproduces the served regime locally (nondeterministic).")
    ap.add_argument("--repair", choices=("none", "imports"), default="none",
                    help="deterministic repair before scoring: 'imports' runs goimports, the "
                         "cheapest ALGORITHM component and one the real Builder loop already "
                         "performs with a gate.")
    ap.add_argument("--save-generations", metavar="PATH",
                    help="write each generated implementation to JSONL, so a scoring or "
                         "bench change can be re-measured without a model run")
    args = ap.parse_args()

    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler

    model, tokenizer = load(args.model, adapter_path=args.adapter)
    # The mlx-community Qwen configs carry eos_token_id=<|endoftext|> only, so
    # generation never stops at <|im_end|> — tuned adapters (which stop emitting
    # <|endoftext|>) then ramble to max_tokens on every prompt. Register the
    # chat EOS explicitly so stopping works for base AND adapters.
    im_end = tokenizer.encode("<|im_end|>")
    if len(im_end) == 1:
        tokenizer.eos_token_ids.add(im_end[0])
    else:
        # If this ever fails, NOTHING stops generation at <|im_end|>: tuned adapters
        # ramble to max_tokens on every prompt and score ~0 for the wrong reason,
        # silently corrupting the A/B. Make it loud instead of quietly biasing it.
        print(f"WARNING: <|im_end|> did not encode to a single token ({im_end}); "
              "generation may not stop and scores for tuned adapters will be biased low.",
              file=sys.stderr)
    sampler = make_sampler(temp=args.temp) if args.temp > 0 else None
    label = f"{os.path.basename(args.adapter)}" if args.adapter else "BASE (untuned)"
    regime = "greedy" if args.temp == 0 else f"temp={args.temp}"

    tasks = [json.loads(l) for l in open(args.bench)]
    print(f"mlx bench: {len(tasks)} tasks · model={label} · {regime}\n")

    imports_exe = ""
    if args.repair == "imports":
        imports_exe = _goimports()
        if not imports_exe:
            raise SystemExit("--repair imports requested but goimports was not found")

    passed, built, n_repaired, n_truncated, detail, saved = 0, 0, 0, 0, [], []
    for t in tasks:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": t["prompt"]}]
        prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        try:
            gkw = {"max_tokens": args.max_tokens, "verbose": False}
            if sampler is not None:
                gkw["sampler"] = sampler
            out = generate(model, tokenizer, prompt=prompt, **gkw)
            n_truncated += _truncated(out)
            code = extract_code(out)
            if imports_exe:
                repaired = _repair_imports(code, imports_exe)
                n_repaired += repaired != code
                code = repaired
            ok = runs_green(code, t["metadata"]["tests"])
            builds = ok or compiles(code)
        except Exception as e:  # generation/runtime error counts as a miss
            ok = False
            detail.append(f"{t['id']}:ERR({type(e).__name__})")
            continue
        passed += ok
        built += builds
        # '+' passes · 'v' compiles but fails the hidden test · '-' is not valid Go
        detail.append(f"{'+' if ok else ('v' if builds else '-')}{t['id']}")
        if args.save_generations:
            saved.append({"id": t["id"], "label": label, "regime": regime,
                          "verdict": ok, "compiles": builds, "code": code})

    n = len(tasks)
    rate = f"{passed}/{built}" if built else "n/a"
    print(f"{label}: pass@1 = {passed}/{n}  [{' '.join(detail)}]")
    print(f"  decomposition: compiles {built}/{n} · passes-given-compiles {rate}"
          f"  (+passes v=wrong -=invalid)")
    if imports_exe:
        print(f"  repair: goimports changed {n_repaired} generation(s)")
    if n_truncated:
        print(f"  WARNING: {n_truncated} generation(s) hit --max-tokens ({args.max_tokens}) "
              f"mid-fence — raise it or this penalises verbose models")
    if args.save_generations:
        with open(args.save_generations, "w") as f:
            for row in saved:
                f.write(json.dumps(row) + "\n")
        print(f"  wrote {len(saved)} generations -> {args.save_generations} (re-scorable model-free)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
