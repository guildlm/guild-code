# -*- coding: utf-8 -*-
"""Re-score a saved go_swe_bench draw with the CURRENT extractor, touching only the rows the registered
extractor read differently, and report registered / strict / lenient (missing file = unchanged) side by side.
Nothing is redrawn; verdicts of rows the extractor reads the same are copied from the file, not recomputed.
    python swe_bench_rescore.py data/go_swe_bench_v0_qwen3-coder_30b-32k.jsonl
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("h", os.path.join(HERE, "swe_bench_eval.py"))
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)


def registered_extract(out, wanted):
    """the v0 extractor as registered (commit 69238f1): no stutter normalisation"""
    got, untagged = {}, []
    for before, inside, body in h.FILE_RE.findall(out):
        path = before or inside
        if path in wanted:
            got[path] = body
        elif path and os.path.basename(path) in {os.path.basename(w) for w in wanted}:
            got[next(w for w in wanted if os.path.basename(w) == os.path.basename(path))] = body
        elif not path:
            untagged.append(body)
    if len(wanted) == 1 and not got and len(untagged) == 1:
        got[next(iter(wanted))] = untagged[0]
    return got


def main():
    path = sys.argv[1]
    bench = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "data", "go_swe_bench_v0_eval.jsonl")
    ev = {f"{t['repo']}@{t['sha'][:8]}": t for t in (json.loads(l) for l in open(bench))}
    rows = [json.loads(l) for l in open(path)]
    env = dict(os.environ, GOFLAGS="-mod=mod", GOTOOLCHAIN="auto", CGO_ENABLED="0")
    cache = os.path.join(HERE, "..", "datasets", "mining", "repos")
    workroot = tempfile.mkdtemp(prefix="goswe-rescore-")
    res, reg = {}, 0
    for r in rows:
        t = ev[r["id"]]; wanted = set(t["src_files"])
        old = registered_extract(r["output"], wanted)
        new = h.extract_files(r["output"], wanted)
        complete = len(new) == len(wanted)
        reg += r["verdict"]
        note = ""
        if new == old:
            strict = r["verdict"]; tail = r["tail"]
        elif complete:
            strict, tail = h.score(t, new, cache, env, workroot); note = "re-extracted"
        else:
            strict, tail = False, "incomplete: missing files"; note = "re-extracted"
        if complete or not new:
            lenient, ltail = strict, tail
        else:
            filled = dict(new)
            for p in t["src_files"]:
                filled.setdefault(p, t["before"][p])
            lenient, ltail = h.score(t, filled, cache, env, workroot); note += " lenient-filled"
        res[r["id"]] = {"registered": r["verdict"], "strict": strict, "lenient": lenient, "truncated": h.truncated(r["output"]),
                        "complete": complete, "note": note.strip(), "tail": (ltail if lenient != strict else tail)[-400:]}
        if note or strict != r["verdict"] or lenient != r["verdict"]:
            print(f"{r['id']:40} registered={int(r['verdict'])} strict={int(strict)} lenient={int(lenient)} "
                  f"trunc={int(h.truncated(r['output']))} {note}  | {(ltail if lenient != strict else tail).strip().splitlines()[-1][:90] if (ltail if lenient != strict else tail).strip() else ''}", flush=True)
    n = len(rows)
    print(f"\n{path}: registered {reg}/{n} · fixed-extractor strict {sum(v['strict'] for v in res.values())}/{n} · "
          f"lenient {sum(v['lenient'] for v in res.values())}/{n} · truncated {sum(v['truncated'] for v in res.values())}/{n}")
    out = path.replace(".jsonl", ".rescore.json")
    json.dump(res, open(out, "w"), indent=1)
    print("->", out)
    shutil.rmtree(workroot, ignore_errors=True)


if __name__ == "__main__":
    main()
