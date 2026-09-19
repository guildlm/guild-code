# -*- coding: utf-8 -*-
"""go_dev_bench through an OpenAI-compatible endpoint (Ollama by default), with the SAME
prompt, decoding regime, extraction and scoring as mlx_bench.py — so a run here differs
from an mlx_bench run only in the weights/backend, which is the quantization A/B question:
    "is this score a fact about the model, or about one 4-bit build of it?"
Everything that could drift is imported from mlx_bench / mlx_test_bench, not copied:
SYSTEM prompt, extract_code, _truncated, compiles, runs_green, goimports repair.
Output JSONL has the mlx_bench schema, so rescore_dev_bench.py re-scores it model-free.
    python served_bench.py --model qwen3-coder:30b --save-generations data/x.jsonl
    python served_bench.py --model qwen2.5-coder:7b --temp 0      # the backend control
Temperature 0 is the closest an Ollama endpoint gets to mlx_bench's greedy; it is not
byte-guaranteed deterministic across runs, and the log says "temp=0 (served)" not "greedy".
"""
import argparse
import json
import os
import sys
import time
import urllib.request

from mlx_bench import SYSTEM, compiles, runs_green  # noqa: E402
from mlx_test_bench import _goimports, _repair_imports, _truncated, extract_code  # noqa: E402


def ask(base_url: str, model: str, prompt: str, temp: float, max_tokens: int, seed: int) -> str:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        "temperature": temp,
        "max_tokens": max_tokens,
        "seed": seed,
    }).encode()
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"] or ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="served model name, e.g. qwen3-coder:30b")
    ap.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"))
    ap.add_argument("--bench", default=os.path.join(os.path.dirname(__file__), "data", "go_dev_bench.jsonl"))
    ap.add_argument("--max-tokens", type=int, default=900)
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--repair", choices=("none", "imports"), default="none")
    ap.add_argument("--save-generations", metavar="PATH")
    args = ap.parse_args()

    label = f"{args.model} (served)"
    regime = f"temp={args.temp} (served)"
    tasks = [json.loads(l) for l in open(args.bench)]
    print(f"served bench: {len(tasks)} tasks · model={label} · {regime} · {args.base_url}\n")
    imports_exe = _goimports() if args.repair == "imports" else ""
    if args.repair == "imports" and not imports_exe:
        raise SystemExit("--repair imports requested but goimports was not found")

    passed = built = n_repaired = n_truncated = 0
    detail, saved = [], []
    t0 = time.time()
    for t in tasks:
        try:
            out = ask(args.base_url, args.model, t["prompt"], args.temp, args.max_tokens, args.seed)
            n_truncated += _truncated(out)
            code = extract_code(out)
            if imports_exe:
                repaired = _repair_imports(code, imports_exe)
                n_repaired += repaired != code
                code = repaired
            ok = runs_green(code, t["metadata"]["tests"])
            builds = ok or compiles(code)
        except Exception as e:  # generation/runtime error counts as a miss
            detail.append(f"{t['id']}:ERR({type(e).__name__})")
            if args.save_generations:
                saved.append({"id": t["id"], "label": label, "regime": regime, "verdict": False,
                              "compiles": False, "code": "", "error": type(e).__name__})
            continue
        passed += ok
        built += builds
        detail.append(f"{'+' if ok else ('v' if builds else '-')}{t['id']}")
        if args.save_generations:
            saved.append({"id": t["id"], "label": label, "regime": regime,
                          "verdict": ok, "compiles": builds, "code": code})
    n = len(tasks)
    rate = f"{passed}/{built}" if built else "n/a"
    print(f"{label}: pass@1 = {passed}/{n}  [{' '.join(detail)}]")
    print(f"  decomposition: compiles {built}/{n} · passes-given-compiles {rate}  (+passes v=wrong -=invalid)")
    print(f"  wall: {time.time() - t0:.0f}s for {n} tasks")
    if imports_exe:
        print(f"  repair: goimports changed {n_repaired} generation(s)")
    if n_truncated:
        print(f"  WARNING: {n_truncated} generation(s) hit --max-tokens ({args.max_tokens}) mid-fence")
    if args.save_generations:
        with open(args.save_generations, "w") as f:
            for row in saved:
                f.write(json.dumps(row) + "\n")
        print(f"  wrote {len(saved)} generations -> {args.save_generations} (re-scorable model-free)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
