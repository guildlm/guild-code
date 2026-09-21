# -*- coding: utf-8 -*-
"""The WRITER EXEMPLAR arm, scored against its prereg (PREREG-testwriter-exemplar-show-it-a-neighbour.txt).
Compares against the form-retry draw, restricted to the 36 tasks that have an exemplar."""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "data", "go_swe_bench_v0_selftests_30b_formretry.jsonl")
A = os.path.join(HERE, "data", "go_swe_bench_v0_selftests_30b_exemplar.jsonl")
IDS = os.path.join(HERE, "data", "_exemplar_ids.json")
KEYS = ["USEFUL", "FALSE-ALARM", "toothless", "nocompile", "no-test"]


def load(p):
    return {r["id"]: r for r in (json.loads(l) for l in open(p))}


def main():
    b, a, ex = load(B), load(A), set(json.load(open(IDS)))
    pend = [i for i in ex if i not in a]
    if pend:
        print(f"INCOMPLETE: {len(ex)-len(pend)}/{len(ex)} exemplar rows drawn", file=sys.stderr)
    ex = sorted(i for i in ex if i in a)

    cb = collections.Counter(b[i]["verdict"] for i in ex)
    ca = collections.Counter(a[i]["verdict"] for i in ex)
    kb = sum(b[i]["kept"] for i in ex); ka = sum(a[i]["kept"] for i in ex)
    print(f"THE {len(ex)} TASKS WITH AN EXEMPLAR (the other 15 are byte-identical controls)\n")
    print(f"  {'verdict':14}{'no exemplar':>13}{'with exemplar':>15}")
    for k in KEYS:
        print(f"  {k:14}{cb.get(k,0):>13}{ca.get(k,0):>15}")
    print(f"  {'KEPT':14}{kb:>13}{ka:>15}")
    rb = cb.get("USEFUL", 0) / kb if kb else 0
    ra = ca.get("USEFUL", 0) / ka if ka else 0
    print(f"  {'useful/kept':14}{rb:>12.0%}{ra:>15.0%}")

    print("\n  every row whose verdict changed:")
    for i in ex:
        if b[i]["verdict"] != a[i]["verdict"]:
            print(f"    {i[:40]:42} {b[i]['verdict']:>12}  ->  {a[i]['verdict']}")

    u_a, u_b = ca.get("USEFUL", 0), cb.get("USEFUL", 0)
    print("\nREGISTERED PREDICTIONS -> OUTCOMES")
    for txt, p, hit in [
        ("P(nocompile falls below 16)", 0.70, ca.get("nocompile", 0) < 16),
        ("P(nocompile <= 10)", 0.35, ca.get("nocompile", 0) <= 10),
        ("P(USEFUL >= 3, at least one new)", 0.45, u_a >= 3),
        ("P(USEFUL >= 5)", 0.20, u_a >= 5),
        ("P(USEFUL < 2, the arm loses a test)", 0.15, u_a < 2),
        ("P(KEPT rises above 12)", 0.60, ka > 12),
        ("P(useful/kept beats 17%)", 0.35, ra > rb),
        ("P(toothless rises above 8)", 0.45, ca.get("toothless", 0) > 8),
    ]:
        print(f"  {txt:44} = {p:.2f} ... {'HIT' if hit else 'miss'}")
    print(f"\n  USEFUL {u_b} -> {u_a} · KEPT {kb} -> {ka} · nocompile {cb.get('nocompile',0)} -> {ca.get('nocompile',0)}")
    wb = collections.Counter(a[i]["verdict"] for i in a)
    print(f"  whole bench after: " + " · ".join(f"{k} {wb.get(k,0)}" for k in KEYS) + f" · KEPT {sum(r['kept'] for r in a.values())}")


if __name__ == "__main__":
    sys.exit(main())
