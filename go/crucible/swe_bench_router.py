# -*- coding: utf-8 -*-
"""go_swe_bench — the test-gated ROUTER, offline. Candidates are the FINAL files of two loop draws
(swe_bench_loop.py rows carry final_files); the gate is the kept self-test of each task (never the hidden
test). STRICT (the router line's rule): stay on the preferred candidate unless the self-test fails it AND
passes the alternate. Hidden tests judge the routed result. Prints preferred-alone, STRICT, oracle (union).
    python swe_bench_router.py --preferred data/go_swe_bench_v0_loop_qwen3-coder_30b-32k.selftest.jsonl \\
        --alternate data/go_swe_bench_v0_loop_qwen2.5-coder_7b-32k.selftest.jsonl \\
        --selftests data/go_swe_bench_v0_selftests_qwen3-coder_30b-32k.jsonl
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
W = importlib.util.module_from_spec(importlib.util.spec_from_file_location("W", os.path.join(HERE, "swe_bench_selftest_writer.py")))
W.__spec__.loader.exec_module(W)
L, h = W.L, W.h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preferred", required=True); ap.add_argument("--alternate", required=True)
    ap.add_argument("--selftests", required=True)
    ap.add_argument("--bench", default=os.path.join(HERE, "data", "go_swe_bench_v0_eval.jsonl"))
    ap.add_argument("--cache", default=os.path.join(HERE, "..", "datasets", "mining", "repos"))
    a = ap.parse_args()
    ev = {f"{t['repo']}@{t['sha'][:8]}": t for t in (json.loads(l) for l in open(a.bench))}
    P = {r["id"]: r for r in (json.loads(l) for l in open(a.preferred))}
    A = {r["id"]: r for r in (json.loads(l) for l in open(a.alternate))}
    S = {r["id"]: r["test"] for r in (json.loads(l) for l in open(a.selftests)) if r.get("kept")}
    env = dict(os.environ, GOFLAGS="-mod=mod", GOTOOLCHAIN="auto", CGO_ENABLED="0")
    workroot = tempfile.mkdtemp(prefix="goswe-router-")
    ids = [i for i in ev if i in P and i in A]
    pref = strict = oracle = 0; switches = []; gate_calls = 0
    for i in ids:
        t = ev[i]; vp, va = P[i]["ladder"][-1], A[i]["ladder"][-1]
        pref += vp; oracle += (vp or va)
        choice = vp
        if i in S and P[i]["final_files"] and A[i]["final_files"]:
            gate_calls += 1
            kp, _, _ = W.run_selftest(t, P[i]["final_files"], S[i], a.cache, env, workroot)
            if kp != "green":
                ka, _, _ = W.run_selftest(t, A[i]["final_files"], S[i], a.cache, env, workroot)
                if ka == "green":
                    choice = va; switches.append((i.split("@")[0], "GOOD" if va and not vp else "BAD" if vp and not va else "neutral"))
        strict += choice
        print(f"{'+' if choice else '-'} {i:40} pref={int(vp)} alt={int(va)} gate={'kept' if i in S else '-'}", flush=True)
    n = len(ids)
    print(f"\nROUTER on {n} tasks: preferred alone {pref} · STRICT {strict} · oracle {oracle} · gate consulted {gate_calls} · "
          f"switches {len(switches)}: {switches}")
    shutil.rmtree(workroot, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
