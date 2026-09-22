# -*- coding: utf-8 -*-
"""The SELF-TEST ISOLATION repair, scored against
PREREG-selftest-isolation-the-harness-deleted-the-fixtures.txt.

Two tables. The first is the ACCEPTANCE GATE: the commit's own test, played through the harness
(--model hidden, no model call). The gate asks whether the instrument can accept the truth.
The second is the writer's rescore under the repaired instrument, same outputs, no model call.
"""
import collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
GOLD_OLD = os.path.join(D, "go_swe_bench_v0_selftests_hidden.jsonl")
GOLD_NEW = os.path.join(D, "go_swe_bench_v0_selftests_hidden_keeptests.jsonl")
W_OLD = os.path.join(D, "go_swe_bench_v0_selftests_30b_compileretry.jsonl")
W_NEW = os.path.join(D, "go_swe_bench_v0_selftests_30b_keeptests.jsonl")
KEYS = ["USEFUL", "FALSE-ALARM", "toothless", "nocompile", "no-test", "error", "?"]


def load(p):
    return {r["id"]: r for r in (json.loads(l) for l in open(p))} if os.path.exists(p) else {}


def table(a, b, an, bn):
    ca = collections.Counter(r["verdict"] for r in a.values())
    cb = collections.Counter(r["verdict"] for r in b.values())
    print(f"  {'verdict':14}{an:>14}{bn:>18}")
    for k in KEYS:
        if ca.get(k) or cb.get(k):
            print(f"  {k:14}{ca.get(k, 0):>14}{cb.get(k, 0):>18}")
    if a and "kept" in next(iter(a.values())):
        print(f"  {'KEPT':14}{sum(r['kept'] for r in a.values()):>14}{sum(r['kept'] for r in b.values()):>18}")
    return ca, cb


def moved(a, b, verdict="nocompile"):
    out = [i for i in a if a[i]["verdict"] == verdict and i in b and b[i]["verdict"] != verdict]
    inn = [i for i in a if a[i]["verdict"] != verdict and i in b and b[i]["verdict"] == verdict]
    return out, inn


def main():
    go, gn = load(GOLD_OLD), load(GOLD_NEW)
    print("ACCEPTANCE GATE — the commit's own test, played through the harness\n")
    ca, cb = table(go, gn, "delete all", "keep pkg tests")
    rec, brk = moved(go, gn)
    print(f"\n  recovered ({len(rec)}): " + (", ".join(i.split('@')[0] for i in rec) or "none"))
    print(f"  newly broken ({len(brk)}): " + (", ".join(i.split('@')[0] for i in brk) or "none"))
    gate = cb.get("nocompile", 99) < ca.get("nocompile", 0)
    print(f"\n  GATE: gold nocompile {ca.get('nocompile',0)} -> {cb.get('nocompile',0)}  "
          f"{'PASS' if gate else 'FAIL — the repair is wrong; nothing below is scored'}")
    unreach = sorted(i for i in gn if gn[i]["verdict"] == "nocompile" and gn[i].get("gold") == "green")
    print(f"\n  UNREACHABLE CLASS ({len(unreach)}): the gold test compiles against the FIX and not the\n"
          f"  parent — it names a symbol the fix adds. No red-at-parent self-test can exist for these.")
    for i in unreach:
        print(f"    {i.split('@')[0]}")
    if not gate:
        sys.exit(1)

    wo, wn = load(W_OLD), load(W_NEW)
    if not wn:
        print("\n(the writer rescore has not been run yet)")
        return
    print("\n\nTHE WRITER'S 30B DRAW, RESCORED — same outputs, no model call\n")
    wa, wb = table(wo, wn, "old harness", "repaired")
    rec, brk = moved(wo, wn)
    print(f"\n  now compiles ({len(rec)}): " + (", ".join(i.split('@')[0] for i in rec) or "none"))
    print(f"  newly nocompile ({len(brk)}): " + (", ".join(i.split('@')[0] for i in brk) or "none"))
    print("\n  EVERY ROW THAT CHANGED VERDICT (named, never netted out):")
    for i in sorted(wo):
        if i in wn and wo[i]["verdict"] != wn[i]["verdict"]:
            print(f"    {i.split('@')[0][:30]:32} {wo[i]['verdict']:14} -> {wn[i]['verdict']}")
    print("\n  REGISTERED PREDICTIONS -> OUTCOMES")
    n_nc = wb.get("nocompile", 0)
    u = wb.get("USEFUL", 0)
    hit = lambda b: "HIT " if b else "MISS"
    print(f"    P(gold nocompile <= 8 of 51)      = 0.60  {hit(cb.get('nocompile',99) <= 8)}  ({cb.get('nocompile',0)})")
    print(f"    P(gold nocompile == 0)            = 0.10  {hit(cb.get('nocompile',99) == 0)}")
    print(f"    P(USEFUL > 5)                     = 0.55  {hit(u > 5)}  ({u})")
    print(f"    P(USEFUL > 7)                     = 0.25  {hit(u > 7)}")
    print(f"    P(nocompile < 17)                 = 0.70  {hit(n_nc < 17)}  ({n_nc})")
    rq = [i for i in wn if i.split('@')[0] in ("rqlite__rqlite", "go-kit__kit")
          and wn[i]["verdict"] != "nocompile"]
    print(f"    P(rqlite OR go-kit compiles)      = 0.50  {hit(bool(rq))}  ({', '.join(i.split('@')[0] for i in rq) or 'neither'})")
    worse = [i for i in wo if i in wn and wo[i]["verdict"] in ("USEFUL", "FALSE-ALARM", "toothless")
             and wn[i]["verdict"] in ("nocompile", "error")]
    print(f"    P(>= 1 row gets WORSE)            = 0.45  {hit(bool(worse))}  ({', '.join(i.split('@')[0] for i in worse) or 'none'})")


if __name__ == "__main__":
    main()
