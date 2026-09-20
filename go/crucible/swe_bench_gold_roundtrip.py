# -*- coding: utf-8 -*-
"""Instrument test for tools/decledit with NO model: for every task, turn the gold patch into a
declaration-level fragment (decledit -changed before after), apply it back onto BEFORE
(decledit -apply, then goimports), and run the hidden tests. Green everywhere = the edit form can
carry every gold fix; a red row is a limit of the tool, recorded before any model draws in it.
    python swe_bench_gold_roundtrip.py [--bench data/go_swe_bench_v0_eval.jsonl]
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DECLEDIT = os.path.join(HERE, "tools", "decledit", "decledit")
GOIMPORTS = os.path.expanduser("~/go/bin/goimports")
spec = importlib.util.spec_from_file_location("h", os.path.join(HERE, "swe_bench_eval.py"))
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)


def run(args, inp=None):
    p = subprocess.run(args, input=inp, capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout, p.stderr


def gold_fragment(before, after, tmp):
    b, a = os.path.join(tmp, "before.go"), os.path.join(tmp, "after.go")
    open(b, "w").write(before); open(a, "w").write(after)
    rc, out, err = run([DECLEDIT, "-changed", "-before", b, "-after", a])
    return (out if rc == 0 else None), err


def apply_fragment(target_src, fragment, tmp):
    """decledit -apply then goimports; returns (source or None, message)"""
    t, f = os.path.join(tmp, "target.go"), os.path.join(tmp, "fragment.go")
    open(t, "w").write(target_src); open(f, "w").write(fragment)
    rc, out, err = run([DECLEDIT, "-apply", "-target", t, "-fragment", f])
    if rc != 0:
        return None, err.strip()
    rc2, out2, err2 = run([GOIMPORTS], inp=out)
    return (out2 if rc2 == 0 else out), (err.strip() + ("\n" + err2.strip() if rc2 else "")).strip()


def gofmt(src):
    rc, out, _ = run(["gofmt"], inp=src)
    return out if rc == 0 else src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default=os.path.join(HERE, "data", "go_swe_bench_v0_eval.jsonl"))
    ap.add_argument("--cache", default=os.path.join(HERE, "..", "datasets", "mining", "repos"))
    a = ap.parse_args()
    tasks = [json.loads(l) for l in open(a.bench)]
    env = dict(os.environ, GOFLAGS="-mod=mod", GOTOOLCHAIN="auto", CGO_ENABLED="0")
    workroot = tempfile.mkdtemp(prefix="goswe-gold-")
    tmp = tempfile.mkdtemp(prefix="decledit-")
    green, exact, nfiles, t0 = 0, 0, 0, time.time()
    frag_sizes, gold_sizes = [], []
    for t in tasks:
        tid = f"{t['repo']}@{t['sha'][:8]}"
        files, notes = {}, []
        for p in t["src_files"]:
            before, after = t["before"][p], t["after"][p]
            frag, err = gold_fragment(before, after, tmp)
            if frag is None:
                notes.append(f"{p}: -changed failed: {err.strip()[:80]}"); files[p] = before; continue
            frag_sizes.append(len(frag)); gold_sizes.append(len(after))
            src, msg = apply_fragment(before, frag, tmp)
            if src is None:
                notes.append(f"{p}: -apply failed: {msg[:80]}"); files[p] = before; continue
            if msg:
                notes.append(f"{p}: {msg[:80]}")
            nfiles += 1
            if gofmt(src) == gofmt(after):
                exact += 1
            files[p] = src
        ok, tail = h.score(t, files, a.cache, env, workroot)
        green += ok
        print(f"{'+' if ok else '-'} {tid:40} {'' if ok else tail.strip().splitlines()[-1][:80] if tail.strip() else ''} {' | '.join(notes)}", flush=True)
    n = len(tasks)
    import statistics
    print(f"\ngold round-trip: hidden tests GREEN {green}/{n} · files exact after gofmt {exact}/{nfiles} · "
          f"fragment/after size median {statistics.median(frag_sizes):.0f}/{statistics.median(gold_sizes):.0f} chars "
          f"(ratio {statistics.median(f/g for f, g in zip(frag_sizes, gold_sizes)):.2f}) · wall {time.time()-t0:.0f}s", flush=True)
    shutil.rmtree(workroot, ignore_errors=True); shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
