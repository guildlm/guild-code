# -*- coding: utf-8 -*-
"""go_swe_bench — the SELF-TEST WRITER, and its instrument test on the known case (the gold fix).
For every task the writer (a model that never sees any candidate fix) writes ONE test file from the
commit message + the buggy files. Deterministic repairs: fence-stutter collapse, stripdecl against every
source file of the package (the router line's lesson: the writer re-implements the function), goimports.
Then the Go toolchain measures the test, in isolation (every other _test.go of the package removed):
  compiles at the parent · RED at the parent (teeth for this bug) · GREEN on the gold fix (validity)
  · RED on the gold fix (a false alarm: this test would push a right fix into a wrong one).
A test is KEPT for the loop/router only if it compiles at the parent and is red there — the gold is
never consulted for keeping, only for the instrument numbers.
    python swe_bench_selftest_writer.py --model qwen3-coder:30b-32k --save data/go_swe_bench_v0_selftests_qwen3-coder_30b-32k.jsonl
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STRIPDECL = os.path.join(HERE, "tools", "stripdecl", "stripdecl")
GOIMPORTS = os.path.expanduser("~/go/bin/goimports")
spec = importlib.util.spec_from_file_location("L", os.path.join(HERE, "swe_bench_loop.py"))
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
h = L.h
SELFTEST_NAME = "zz_swe_selftest_test.go"

SYSTEM = ("You are a senior Go engineer. You are given a commit message describing a bug and the CURRENT, "
          "still buggy, content of the source files involved. Write ONE Go test file that reproduces the bug: "
          "its tests must FAIL on the current code and PASS once the described bug is fixed. Use only the "
          "package's existing API exactly as shown. Do NOT re-implement, copy or redefine any function, type, "
          "variable or constant from the files. Only TestXxx functions, plus small helpers with new names if "
          "needed; the file must be self-contained (no helpers from other test files). Return the complete "
          "test file in ONE ```go block that starts with the package clause. No commentary.")


def pkg_of(src):
    m = re.search(r"^package\s+(\w+)", src, re.M)
    return m.group(1) if m else "main"


def build_prompt(t):
    parts = [f"Commit message:\n{t['subject']}\n{t['body']}".rstrip(), ""]
    for p, src in t["before"].items():
        parts.append(f"// file: {p}\n```go\n{src}\n```")
    pkg = pkg_of(t["before"][t["src_files"][0]])
    parts.append(f"Write the test file for package `{pkg}` (directory of {t['src_files'][0]}). Its tests must fail on the code above and pass once the bug is fixed.")
    return "\n\n".join(parts)


def extract_test(out):
    out = h.normalize(out)
    if out.count("```") % 2 == 1:  # the model forgot to close the last fence (age, smoke test): close it
        out = out.rstrip() + "\n```"
    blocks = re.findall(r"```go\s*\n(.*?)```", out, re.S)
    blocks = [b for b in blocks if "func Test" in b] or blocks
    if not blocks:
        return None
    return max(blocks, key=len)


def repair(test_src, t, tmp):
    """stripdecl against every source file of the task's package, then goimports"""
    pkgdir = os.path.dirname(t["src_files"][0])
    if not re.search(r"^package\s+\w+", test_src, re.M):
        test_src = f"package {pkg_of(t['before'][t['src_files'][0]])}\n\n" + test_src
    tpath = os.path.join(tmp, "t_test.go")
    open(tpath, "w").write(test_src)
    for p, src in t["before"].items():
        if os.path.dirname(p) != pkgdir:
            continue
        ipath = os.path.join(tmp, "impl.go"); open(ipath, "w").write(src)
        q = subprocess.run([STRIPDECL, "-impl", ipath, "-test", tpath], capture_output=True, text=True, timeout=60)
        if q.returncode == 0 and q.stdout.strip():
            open(tpath, "w").write(q.stdout)
    q = subprocess.run([GOIMPORTS, tpath], capture_output=True, text=True, timeout=60)
    return q.stdout if q.returncode == 0 and q.stdout.strip() else open(tpath).read()


def test_names(src):
    return set(re.findall(r"^func (Test\w+)\s*\(", src, re.M))


def run_selftest(t, files, test_src, cache, env, workroot):
    """isolated: every other _test.go in the package dir is removed. -> (status, failing self-test names, output)
    status: 'nocompile' (the self-test itself does not build) | 'red' | 'green' | 'error' (the package/test binary broke elsewhere)"""
    pkgdir = os.path.dirname(t["src_files"][0]) or "."
    wt = L.Worktree(cache, t, workroot)
    try:
        wt.write(files)
        d = os.path.join(wt.wt, pkgdir)
        for f in os.listdir(d):
            if f.endswith("_test.go"):
                os.remove(os.path.join(d, f))
        with open(os.path.join(d, SELFTEST_NAME), "w", encoding="utf-8") as f:
            f.write(test_src)
        rc, out = h.sh(["go", "test", "-count=1", "-timeout", "120s", "-run", "^Test", f"./{pkgdir}" if pkgdir != "." else "."], wt.wt, env)
        names = test_names(test_src)
        if rc == 0:
            return "green", set(), out
        if any(SELFTEST_NAME in l for l in out.splitlines() if re.search(r"\.go:\d+:\d+:", l)):
            return "nocompile", set(), out
        fails = set(L.FAIL_RE.findall(out)) & names
        if fails or "panic" in out or "timed out" in out:
            return "red", fails or {"<panic/timeout>"}, out
        return "error", set(), out  # built and ran, failed for a reason outside the self-test's own names
    finally:
        wt.close()


def selftest_feedback(kind, fails, out, limit=2500):
    """what the loop is told about the self-test: its failing tests' blocks, or its build errors"""
    if kind == "nocompile":
        lines = [l for l in out.splitlines() if SELFTEST_NAME in l and re.search(r"\.go:\d+:\d+:", l)]
        return f"The test file {SELFTEST_NAME} (written for this bug) no longer compiles against your change:\n" + "\n".join(lines)[:limit]
    keep, take = [], False
    for l in out.splitlines():
        m = L.FAIL_RE.match(l)
        if m:
            take = m.group(1) in fails
        if take or ("panic" in l and not keep):
            keep.append(l)
    body = "\n".join(keep)[:limit] or out[-limit:]
    return f"The test file {SELFTEST_NAME} (written for this bug) still fails on your change:\n" + body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default=os.path.join(HERE, "data", "go_swe_bench_v0_eval.jsonl"))
    ap.add_argument("--cache", default=os.path.join(HERE, "..", "datasets", "mining", "repos"))
    ap.add_argument("--model", required=True); ap.add_argument("--base-url", default="http://localhost:11434/v1")
    ap.add_argument("--temp", type=float, default=0.0); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--save", required=True); ap.add_argument("--ids"); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    tasks = [json.loads(l) for l in open(a.bench)]
    if a.limit:
        tasks = tasks[:a.limit]
    if a.ids:
        keep = set(a.ids.split(",")); tasks = [t for t in tasks if f"{t['repo']}@{t['sha'][:8]}" in keep]
    env = dict(os.environ, GOFLAGS="-mod=mod", GOTOOLCHAIN="auto", CGO_ENABLED="0")
    workroot = tempfile.mkdtemp(prefix="goswe-selftest-"); tmp = tempfile.mkdtemp(prefix="selftest-")
    done = {}
    if os.path.exists(a.save):
        done = {r["id"]: r for r in (json.loads(l) for l in open(a.save))}
        print(f"resuming: {len(done)} rows already in {a.save}", flush=True)
    out_f = open(a.save, "a")
    rows, t0 = [], time.time()
    for t in tasks:
        tid = f"{t['repo']}@{t['sha'][:8]}"
        if tid in done:
            rows.append(done[tid]); continue
        if a.model == "hidden":  # instrument test: the commit's own test file plays the self-test (no model)
            pkgdir = os.path.dirname(t["src_files"][0])
            cands = [p for p in t["tests"] if os.path.dirname(p) == pkgdir]
            out = "```go\n" + (t["tests"][cands[0]] if cands else "") + "\n```"
        else:
            try:
                out = h.ask(a.base_url, a.model, build_prompt(t), a.temp, a.max_tokens, a.seed)
            except Exception as e:  # noqa: BLE001
                out = f"ERR {type(e).__name__}"
        raw = extract_test(out)
        row = {"id": tid, "model": a.model, "parent_status": t["parent_status"], "output": out, "test": None,
               "parent": None, "gold": None, "parent_fails": [], "gold_fails": [], "kept": False}
        if raw:
            test_src = repair(raw, t, tmp)
            row["test"] = test_src
            st_p, f_p, out_p = run_selftest(t, dict(t["before"]), test_src, a.cache, env, workroot)
            row["parent"], row["parent_fails"] = st_p, sorted(f_p)
            row["kept"] = st_p == "red"
            st_g, f_g, out_g = run_selftest(t, dict(t["after"]), test_src, a.cache, env, workroot)
            row["gold"], row["gold_fails"] = st_g, sorted(f_g)
            row["parent_tail"], row["gold_tail"] = out_p[-400:], out_g[-400:]
        verdict = ("USEFUL" if row["kept"] and row["gold"] == "green" else
                   "FALSE-ALARM" if row["kept"] and row["gold"] in ("red", "nocompile") else
                   "toothless" if row["parent"] == "green" else
                   "nocompile" if row["parent"] == "nocompile" else "no-test" if raw is None else row["parent"] or "?")
        row["verdict"] = verdict
        print(f"{tid:40} [{t['parent_status']}] parent={row['parent']} gold={row['gold']} -> {verdict}", flush=True)
        rows.append(row); out_f.write(json.dumps(row) + "\n"); out_f.flush()
    n = len(rows)
    from collections import Counter
    c = Counter(r["verdict"] for r in rows)
    kept = sum(r["kept"] for r in rows)
    print(f"\n{a.model} as test writer on {n} tasks: compiles at parent {sum(r['parent'] in ('red','green','error') for r in rows)}/{n} · "
          f"KEPT (red at parent) {kept}/{n} · of kept: green on gold (USEFUL) {c['USEFUL']} · red on gold (FALSE ALARM) {c['FALSE-ALARM']} · "
          f"toothless (green at parent) {c['toothless']} · nocompile {c['nocompile']} · no test block {c['no-test']} · wall {time.time()-t0:.0f}s", flush=True)
    out_f.close(); shutil.rmtree(workroot, ignore_errors=True); shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
