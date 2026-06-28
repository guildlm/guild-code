# -*- coding: utf-8 -*-
"""Head-to-head pass@1 on the go-dev benchmark: specialist vs general baseline.

The objective proof of the GuildLM thesis. For each task in go_dev_bench.jsonl
it prompts each model (any OpenAI-compatible endpoint — Ollama by default),
extracts the Go code, drops it next to the task's hidden test in a temp module,
runs `go test`, and tallies pass@1. No Docker, no judge, pure stdlib + the real
Go toolchain — a task counts only if the model's own code compiles and passes.

Examples:
    # once the specialists are trained & served in Ollama:
    python bench_compare.py --models guildlm-go-dev,qwen2.5-coder:7b
    # sanity-check the harness today (general model vs itself):
    python bench_compare.py --models qwen2.5-coder:7b,qwen2.5-coder:32b

Exit code is 0 if the FIRST model (the specialist) scores >= the others.
"""
import argparse
import json
import os
import re
import subprocess
import tempfile
import urllib.request

MODULE = "sandbox"
_FENCE = re.compile(r"```(?:go|golang)?\s*\n(.*?)```", re.DOTALL)


def extract_code(text: str) -> str:
    m = _FENCE.search(text)
    return (m.group(1) if m else text).strip() + "\n"


def ask(base_url: str, model: str, prompt: str, api_key: str) -> str:
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a Go development specialist. Output one complete Go file in a single ```go block, package sandbox, standard library only, no commentary.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 1024,
        }
    ).encode()
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"] or ""


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
    ap.add_argument("--models", required=True, help="comma list; first is the specialist")
    ap.add_argument("--base-url", default="http://localhost:11434/v1")
    ap.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", "ollama"))
    ap.add_argument("--bench", default=os.path.join(os.path.dirname(__file__), "data", "go_dev_bench.jsonl"))
    args = ap.parse_args()

    tasks = [json.loads(l) for l in open(args.bench)]
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    print(f"go-dev benchmark: {len(tasks)} tasks · models: {', '.join(models)}\n")

    scores: dict[str, int] = {}
    for model in models:
        passed, detail = 0, []
        for t in tasks:
            test = t["metadata"]["tests"]
            try:
                code = extract_code(ask(args.base_url, model, t["prompt"], args.api_key))
                ok = runs_green(code, test)
            except Exception as e:  # network/model error counts as a miss
                ok = False
                detail.append(f"{t['id']}:ERR({type(e).__name__})")
            passed += ok
            detail.append(f"{'+' if ok else '-'}{t['id']}")
        scores[model] = passed
        print(f"{model:>28}  pass@1 = {passed}/{len(tasks)}  [{' '.join(detail)}]")

    best_other = max((s for m, s in scores.items() if m != models[0]), default=-1)
    spec = scores[models[0]]
    print(f"\nspecialist={models[0]} scored {spec}/{len(tasks)}; best baseline={best_other}/{len(tasks)}")
    print("THESIS SUPPORTED ✓" if spec >= best_other else "specialist did not beat baseline ✗")
    return 0 if spec >= best_other else 1


if __name__ == "__main__":
    raise SystemExit(main())
