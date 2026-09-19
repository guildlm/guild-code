# -*- coding: utf-8 -*-
"""go_swe_bench v0 — file-level evaluation, as registered in PREREG-go-swe-bench-v0-a-bench-with-room.txt.
For each task: prompt = the commit message (the "issue") + the BEFORE content of every source file;
the tests are hidden. The model returns every file in full, in ```go blocks tagged with the path.
The files are written over a parent worktree, the commit's test files are copied in, and `go test`
runs on the changed packages. pass@1 iff green. No repair, no retry — the algorithm comes later and
gets its own prereg. Generations are saved so the score re-computes offline.
    python swe_bench_eval.py --model qwen3-coder:30b --save data/go_swe_bench_v0_qwen3coder30b.jsonl
    python swe_bench_eval.py --load data/go_swe_bench_v0_qwen3coder30b.jsonl        # re-score, no model
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

SYSTEM = ("You are a senior Go engineer fixing a bug in a real repository. You are given the commit "
          "message describing the bug and the current content of the files that must change. Return "
          "EVERY given file in full, each in its own ```go block whose first line is a comment "
          "`// file: <path>` exactly as given. Change only what the fix needs. No commentary.")

FILE_RE = re.compile(r"```go\s*\n//\s*file:\s*(\S+)\s*\n(.*?)```", re.S)


def ask(base_url, model, prompt, temp, max_tokens, seed):
    body = json.dumps({"model": model, "temperature": temp, "max_tokens": max_tokens, "seed": seed,
                       "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"] or ""


def build_prompt(t):
    parts = [f"Commit message:\n{t['subject']}\n{t['body']}".rstrip(), ""]
    for p, src in t["before"].items():
        parts.append(f"// file: {p}\n```go\n{src}\n```")
    parts.append("Return every file above in full, fixed.")
    return "\n\n".join(parts)


def extract_files(out, wanted):
    got = {}
    for path, body in FILE_RE.findall(out):
        if path in wanted:
            got[path] = body
    return got


def sh(args, cwd, env=None, timeout=900):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode, p.stdout + p.stderr


def score(t, files, cache, env, workroot):
    repo = os.path.join(cache, t["repo"])
    wt = os.path.join(workroot, "wt")
    sh(["git", "worktree", "remove", "--force", wt], repo)
    shutil.rmtree(wt, ignore_errors=True)
    if sh(["git", "worktree", "add", "--detach", wt, t["parent"]], repo)[0]:
        return False, "worktree"
    try:
        for p, src in files.items():
            with open(os.path.join(wt, p), "w", encoding="utf-8") as f:
                f.write(src)
        for p, src in t["tests"].items():
            os.makedirs(os.path.dirname(os.path.join(wt, p)) or wt, exist_ok=True)
            with open(os.path.join(wt, p), "w", encoding="utf-8") as f:
                f.write(src)
        rc, out = sh(["go", "test", "-count=1", "-timeout", "180s"] + [f"./{p}" if p != "." else "." for p in t["packages"]], wt, env)
        return rc == 0, out[-600:]
    finally:
        sh(["git", "worktree", "remove", "--force", wt], repo)
        shutil.rmtree(wt, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "go_swe_bench_v0.jsonl"))
    ap.add_argument("--cache", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datasets", "mining", "repos"))
    ap.add_argument("--model"); ap.add_argument("--base-url", default="http://localhost:11434/v1")
    ap.add_argument("--temp", type=float, default=0.0); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=6000)
    ap.add_argument("--save"); ap.add_argument("--load"); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    tasks = [json.loads(l) for l in open(a.bench)]
    if a.limit:
        tasks = tasks[:a.limit]
    env = dict(os.environ, GOFLAGS="-mod=mod", GOTOOLCHAIN="auto", CGO_ENABLED="0")
    workroot = tempfile.mkdtemp(prefix="goswe-eval-")
    gens = {}
    if a.load:
        gens = {r["id"]: r for r in (json.loads(l) for l in open(a.load))}
    passed, rows, t0 = 0, [], time.time()
    by_status = {"compile_error": [0, 0], "test_fail": [0, 0]}
    for t in tasks:
        tid = f"{t['repo']}@{t['sha'][:8]}"
        if tid in gens:
            out = gens[tid]["output"]
        else:
            if not a.model:
                sys.exit("--model or --load required")
            try:
                out = ask(a.base_url, a.model, build_prompt(t), a.temp, a.max_tokens, a.seed)
            except Exception as e:  # noqa: BLE001
                out = f"ERR {type(e).__name__}"
        files = extract_files(out, set(t["src_files"]))
        complete = len(files) == len(t["src_files"])
        ok, tail = (score(t, files, a.cache, env, workroot) if complete else (False, "incomplete: missing files"))
        passed += ok
        by_status[t["parent_status"]][0] += ok; by_status[t["parent_status"]][1] += 1
        print(f"{'+' if ok else '-'} {tid:40} [{t['parent_status']}] {'' if complete else 'INCOMPLETE '}{t['subject'][:60]}")
        rows.append({"id": tid, "model": a.model or gens[tid].get("model"), "verdict": ok, "complete": complete,
                     "parent_status": t["parent_status"], "output": out, "tail": tail})
    n = len(tasks)
    print(f"\n{a.model or 'loaded'}: pass@1 = {passed}/{n} ({100*passed/n:.0f}%)  "
          f"compile_error {by_status['compile_error'][0]}/{by_status['compile_error'][1]} · "
          f"test_fail {by_status['test_fail'][0]}/{by_status['test_fail'][1]} · "
          f"incomplete outputs {sum(not r['complete'] for r in rows)} · wall {time.time()-t0:.0f}s")
    if a.save:
        with open(a.save, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        print(f"wrote {len(rows)} generations -> {a.save}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
