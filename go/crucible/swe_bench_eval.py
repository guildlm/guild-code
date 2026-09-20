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

# the tag may sit as the first line INSIDE the fence (as asked) or on the line just BEFORE it (the
# form the prompt itself uses to show the files, which models mirror); both are the same answer.
FILE_RE = re.compile(r"(?://\s*file:\s*(\S+)\s*\n\s*)?```go\s*\n(?://\s*file:\s*(\S+)\s*\n)?(.*?)```", re.S)
# the model sometimes opens the fence, writes the tag, and opens the fence AGAIN ("```go\n// file: x\n```go\n").
# The registered regex then read an EMPTY body and the answer was lost (4 of 51 rows in the 30B v0 draw, all
# scored "expected 'package', found 'EOF'"). Collapsing the stutter is a repair of this tool, not of the model;
# added 2026-09-20 AFTER the registered v0 draw, so the v0 log carries both numbers.
STUTTER_RE = re.compile(r"```go[ \t]*\n(//\s*file:\s*\S+[ \t]*\n)```go[ \t]*\n")


def normalize(out):
    return STUTTER_RE.sub(r"```go\n\1", out)


def truncated(out):
    """an odd number of fences after normalisation = the last file was cut (max_tokens) or abandoned"""
    return normalize(out).count("```") % 2 == 1



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
    out = normalize(out)
    got, untagged = {}, []
    for before, inside, body in FILE_RE.findall(out):
        path = before or inside
        if path in wanted:
            got[path] = body
        elif path and os.path.basename(path) in {os.path.basename(w) for w in wanted}:
            got[next(w for w in wanted if os.path.basename(w) == os.path.basename(path))] = body
        elif not path:
            untagged.append(body)
    if len(wanted) == 1 and not got and len(untagged) == 1:  # one file asked, one block returned
        got[next(iter(wanted))] = untagged[0]
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
    ap.add_argument("--ids", help="comma-separated task ids (repo@sha8): draw/score only these (labelled redraws)")
    ap.add_argument("--missing-unchanged", action="store_true",
                    help="a file the model did not return is taken as unchanged (its BEFORE content); "
                         "v0's registered rule scored it INCOMPLETE = fail. Post-hoc for v0; a v0.1 rule.")
    a = ap.parse_args()
    tasks = [json.loads(l) for l in open(a.bench)]
    if a.limit:
        tasks = tasks[:a.limit]
    if a.ids:
        keep = set(a.ids.split(","))
        tasks = [t for t in tasks if f"{t['repo']}@{t['sha'][:8]}" in keep]
    env = dict(os.environ, GOFLAGS="-mod=mod", GOTOOLCHAIN="auto", CGO_ENABLED="0")
    workroot = tempfile.mkdtemp(prefix="goswe-eval-")
    gens = {}
    if a.load:
        gens = {r["id"]: r for r in (json.loads(l) for l in open(a.load))}
    elif a.save and os.path.exists(a.save):  # resume: rows already drawn are kept as drawn
        gens = {r["id"]: r for r in (json.loads(l) for l in open(a.save))}
        print(f"resuming: {len(gens)} rows already in {a.save}", flush=True)
    out_f = open(a.save, "a") if (a.save and not a.load) else None
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
        if a.missing_unchanged and files:  # returned nothing parseable -> still a fail, not "everything unchanged"
            for p in t["src_files"]:
                files.setdefault(p, t["before"][p])
        runnable = len(files) == len(t["src_files"])
        ok, tail = (score(t, files, a.cache, env, workroot) if runnable else (False, "incomplete: missing files"))
        passed += ok
        by_status[t["parent_status"]][0] += ok; by_status[t["parent_status"]][1] += 1
        print(f"{'+' if ok else '-'} {tid:40} [{t['parent_status']}] {'' if complete else 'INCOMPLETE '}{t['subject'][:60]}", flush=True)
        row = {"id": tid, "model": a.model or gens[tid].get("model"), "verdict": ok, "complete": complete,
               "truncated": truncated(out), "parent_status": t["parent_status"], "output": out, "tail": tail}
        rows.append(row)
        if out_f and tid not in gens:
            out_f.write(json.dumps(row) + "\n"); out_f.flush()
    n = len(tasks)
    print(f"\n{a.model or 'loaded'}: pass@1 = {passed}/{n} ({100*passed/n:.0f}%)  "
          f"compile_error {by_status['compile_error'][0]}/{by_status['compile_error'][1]} · "
          f"test_fail {by_status['test_fail'][0]}/{by_status['test_fail'][1]} · "
          f"incomplete outputs {sum(not r['complete'] for r in rows)} · truncated outputs "
          f"{sum(r['truncated'] for r in rows)} · wall {time.time()-t0:.0f}s", flush=True)
    if out_f:
        out_f.close()
        print(f"generations -> {a.save} ({len(rows)} rows, written as drawn)", flush=True)
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
