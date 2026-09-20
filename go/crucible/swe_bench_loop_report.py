# -*- coding: utf-8 -*-
"""Report for an algorithm-arm draw (swe_bench_loop.py): the ladder by round, where the passes sit, what
the repair rounds did, and the comparison with the file-level v0 draw of the same model. Nothing counted
by hand.    python swe_bench_loop_report.py data/go_swe_bench_v0_loop_<model>.jsonl [v0 rescore.json]
"""
import json
import os
import statistics
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    path = sys.argv[1]
    v0 = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
    ev = {f"{t['repo']}@{t['sha'][:8]}": t for t in (json.loads(l) for l in open(os.path.join(HERE, "data", "go_swe_bench_v0_eval.jsonl")))}
    rows = [json.loads(l) for l in open(path)]
    n = len(rows); K = len(rows[0]["ladder"]) - 1
    print(f"{path}: {n} rows, K={K}")
    lad = [sum(r["ladder"][i] for r in rows) for i in range(K + 1)]
    print("LADDER  " + " · ".join(f"r{i}={v}/{n}" for i, v in enumerate(lad)))
    for st in ("test_fail", "compile_error"):
        sel = [r for r in rows if r["parent_status"] == st]
        print(f"  {st:14} r0 {sum(r['ladder'][0] for r in sel)}/{len(sel)} · final {sum(r['ladder'][-1] for r in sel)}/{len(sel)}")
    sz = lambda i: sum(len(v) for v in ev[i]["before"].values())
    ids = sorted(ev, key=sz); ter = [ids[:17], ids[17:34], ids[34:]]
    have = {r["id"]: r for r in rows}
    print("  by before-size tertile (r0 / final / v0-registered):")
    for i, tt in enumerate(ter):
        tt = [x for x in tt if x in have]
        print(f"    t{i+1} {sz(tt[0]) if tt else 0:>6}..{sz(tt[-1]) if tt else 0:>6}: {sum(have[x]['ladder'][0] for x in tt)}/{len(tt)} / "
              f"{sum(have[x]['ladder'][-1] for x in tt)}/{len(tt)} / {sum(v0.get(x, {}).get('registered', False) for x in tt)}/{len(tt)}")
    for nf in (1, 2, 3, 4):
        tt = [x for x in have if len(ev[x]["src_files"]) == nf]
        if tt:
            print(f"  {nf} file(s): final {sum(have[x]['ladder'][-1] for x in tt)}/{len(tt)}")
    # rounds
    fired = [r for r in rows if len(r["rounds"]) > 1]
    conv = [r for r in fired if r["ladder"][-1] and not r["ladder"][0]]
    print(f"REPAIR ROUNDS fired on {len(fired)}/{n} tasks; converted {len(conv)}: {[r['id'].split('@')[0] for r in conv]}")
    silent = [r for r in rows if len(r["rounds"]) == 1 and not r["ladder"][0]]
    kinds = Counter(r["rounds"][0]["toolchain"] for r in silent)
    print(f"  stopped after r0 WITHOUT a pass (toolchain had nothing to say): {len(silent)}  by r0 toolchain kind {dict(kinds)}")
    fb_kinds = Counter()
    for r in fired:
        r0 = r["rounds"][0]; fb = r0["feedback"] or ""
        k = ("no-apply" if r0["applied"] == 0 else r0["toolchain"])
        fb_kinds[k] += 1
    print(f"  what fired them (r0 state): {dict(fb_kinds)}")
    r0_noapply = sum(1 for r in rows if r["rounds"][0]["applied"] == 0)
    print(f"  r0 outputs with NO applicable declaration: {r0_noapply}/{n}")
    frag_sizes = [len(r["rounds"][0]["output"]) for r in rows]
    print(f"  r0 output size median {statistics.median(frag_sizes):.0f} chars (v0 file-level median was ~11k)")
    # vs v0
    if v0:
        p_loop = {r["id"] for r in rows if r["ladder"][-1]}; p0 = {r["id"] for r in rows if r["ladder"][0]}
        p_v0 = {k for k in have if v0.get(k, {}).get("registered")}
        print(f"VS v0 file-level (registered {len(p_v0)}): r0 edit-form {len(p0)} · final {len(p_loop)} · both(final,v0) {len(p_loop & p_v0)} · "
              f"gained {sorted(k.split('@')[0] for k in p_loop - p_v0)} · lost {sorted(k.split('@')[0] for k in p_v0 - p_loop)} · union {len(p_loop | p_v0)}")
    # failure classes at the final state
    cls = Counter()
    for r in rows:
        if r["ladder"][-1]:
            cls["PASS"] += 1; continue
        last = r["rounds"][-1]; tail = last["hidden_tail"]
        if last["applied"] == 0 and len(r["rounds"]) == 1: cls["no declaration applied at r0"] += 1
        elif "undefined:" in tail: cls["compile: undefined symbol"] += 1
        elif "redeclared" in tail: cls["compile: redeclared"] += 1
        elif ".go:" in tail and "--- FAIL" not in tail: cls["compile: other"] += 1
        elif "--- FAIL" in tail or "FAIL" in tail: cls["test: failed/panic"] += 1
        else: cls["other"] += 1
    print("FINAL STATE CLASSES:", dict(cls))


if __name__ == "__main__":
    main()
