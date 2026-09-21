# -*- coding: utf-8 -*-
"""The WRITER FORM-RETRY arm, scored against its prereg.
Compares the form-retry draw with the self-test arm's draw on the same 51 tasks, and reports
every registered prediction as HIT / MISS.
    python formretry_report.py
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BEFORE = os.path.join(HERE, "data", "go_swe_bench_v0_selftests_qwen3-coder_30b-32k.rescored.jsonl")
AFTER = os.path.join(HERE, "data", "go_swe_bench_v0_selftests_30b_formretry.jsonl")
ROUTER_BLIND = {"filebrowser__filebrowser@c05c6681", "slackhq__nebula@2a1cc620"}


def load(p):
    return {r["id"]: r for r in (json.loads(l) for l in open(p))}


def has_test(r):
    return bool(r.get("test")) and bool(re.search(r"^func (Test\w*)\s*\(", r["test"], re.M))


def cut_off(out):
    return out.count("```") % 2 == 1


def main():
    b, a = load(BEFORE), load(AFTER)
    touched = sorted(i for i, r in b.items() if r["verdict"] == "no-test")
    missing = [i for i in touched if i not in a or a[i].get("form_retries", 0) == 0]
    if len(a) < len(b) or missing:
        print(f"INCOMPLETE: {len(a)}/{len(b)} rows, {len(missing)} of the 16 not yet redrawn", file=sys.stderr)

    print(f"THE 16 TOUCHED TASKS (the form check fired on exactly these; the other 35 are byte-identical)\n")
    print(f"  {'task':40} {'first output':>13}   {'after one retry':<16} {'verdict':<12}")
    conv, conv_cut, conv_done, n_cut = [], 0, 0, 0
    for i in touched:
        r = a.get(i)
        if r is None:
            print(f"  {i[:38]:40} {'(pending)':>13}")
            continue
        first = (r.get("form_rejected") or [r["output"]])[0]
        was_cut = cut_off(first)
        n_cut += was_cut
        ok = has_test(r)
        conv.append(ok)
        if ok:
            conv_cut += was_cut
            conv_done += not was_cut
        print(f"  {i[:38]:40} {'CUT OFF' if was_cut else 'completed':>13}   "
              f"{'TEST WRITTEN' if ok else 'still no test':<16} {r['verdict']:<12}")
    n = len(conv); c = sum(conv)
    print(f"\n  converted {c}/{n}   ·   of the {n_cut} cut off: {conv_cut}   ·   of the {n - n_cut} completed: {conv_done}")

    def dist(d):
        cc = collections.Counter(r["verdict"] for r in d.values())
        return cc, sum(r["kept"] for r in d.values())
    cb, kb = dist(b); ca, ka = dist(a)
    print(f"\nWHOLE BENCH, 51 TASKS\n  {'':14}{'before':>8}{'after':>8}")
    for k in ["USEFUL", "FALSE-ALARM", "toothless", "nocompile", "no-test", "error"]:
        print(f"  {k:14}{cb.get(k,0):>8}{ca.get(k,0):>8}")
    print(f"  {'KEPT':14}{kb:>8}{ka:>8}")

    print("\nTHE ROUTER-BLIND TASKS (the only path by which this arm can move the router)")
    for i in sorted(ROUTER_BLIND):
        r = a.get(i)
        print(f"  {i[:40]:42} {'pending' if r is None else r['verdict']:<12} kept={'-' if r is None else r['kept']}")

    nu = ca.get("USEFUL", 0) - cb.get("USEFUL", 0)
    nf = ca.get("FALSE-ALARM", 0) - cb.get("FALSE-ALARM", 0)
    blind_kept = sum(1 for i in ROUTER_BLIND if a.get(i, {}).get("kept"))
    print("\nREGISTERED PREDICTIONS -> OUTCOMES")
    for txt, p, hit in [
        ("P(retry yields a TestXxx on >= 8 of 16)", 0.60, c >= 8),
        ("P(>= 13 of 16)", 0.25, c >= 13),
        ("P(0 of 16)", 0.05, c == 0),
        ("P(cut-off rows convert at a LOWER rate than completed rows)", 0.50,
         (conv_cut / n_cut if n_cut else 0) < (conv_done / (n - n_cut) if n - n_cut else 0)),
        ("P(kept total >= 20, up from 15)", 0.40, ka >= 20),
        ("P(at least 1 new USEFUL test)", 0.45, nu >= 1),
        ("P(new FALSE ALARMS > new USEFUL tests)", 0.80, nf > nu),
        ("P(filebrowser or nebula yields a KEPT test)", 0.30, blind_kept >= 1),
    ]:
        print(f"  {txt:60} = {p:.2f} ... {'HIT' if hit else 'miss'}")
    print(f"\n  new useful {nu:+d} · new false alarms {nf:+d} · kept {kb} -> {ka}")
    print("  (the router predictions are scored by swe_bench_router.py against the same gate)")


if __name__ == "__main__":
    sys.exit(main())
