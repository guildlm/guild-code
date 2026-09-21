# -*- coding: utf-8 -*-
"""The WRITER COMPILE-RETRY arm, scored against
PREREG-testwriter-compile-retry-hand-back-the-compilers-own-words.txt."""
import collections, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "data", "go_swe_bench_v0_selftests_30b_exemplar.jsonl")
A = os.path.join(HERE, "data", "go_swe_bench_v0_selftests_30b_compileretry.jsonl")
IDS = os.path.join(HERE, "data", "_compileretry_ids.json")
KEYS = ["USEFUL", "FALSE-ALARM", "toothless", "nocompile", "no-test", "error"]
# the registered classification of the 23, fixed before the draw
CLASS = {"livekit__livekit": "TRUNCATED", "go-playground__validator": "TRUNCATED", "stretchr__testify": "TRUNCATED",
         "labstack__echo": "PARSE", "gorilla__mux": "UNUSED VAR",
         "bluenviron__mediamtx": "INVENTED", "gitleaks__gitleaks": "INVENTED", "go-kit__kit": "INVENTED",
         "henrygd__beszel": "INVENTED", "junegunn__fzf": "INVENTED", "micro__go-micro": "INVENTED",
         "rqlite__rqlite": "INVENTED"}


def load(p): return {r["id"]: r for r in (json.loads(l) for l in open(p))}


def main():
    b, a, ids = load(B), load(A), json.load(open(IDS))
    pend = [i for i in ids if i not in a]
    if pend: print(f"INCOMPLETE: {len(ids)-len(pend)}/{len(ids)} redrawn", file=sys.stderr)
    ids = [i for i in ids if i in a]
    comp = collections.Counter(); tot = collections.Counter()
    print(f"THE {len(ids)} NON-COMPILING ROWS (the other 28 are byte-identical)\n")
    print(f"  {'class':12}{'task':30}{'retry':9}{'compiles now':>13}  verdict")
    for i in sorted(ids, key=lambda x: (CLASS.get(x.split('@')[0], 'TYPE/SEM'), x)):
        r = a[i]; k = CLASS.get(i.split('@')[0], "TYPE/SEM")
        ok = r["parent"] in ("red", "green", "error")
        tot[k] += 1; comp[k] += ok
        print(f"  {k:12}{i.split('@')[0][:28]:30}{r.get('compile_retry','-'):9}{'YES' if ok else 'no':>13}  {r['verdict']}")
    print(f"\n  {'class':12}{'compiled / n':>14}")
    for k in ["TRUNCATED", "PARSE", "UNUSED VAR", "INVENTED", "TYPE/SEM"]:
        if tot[k]: print(f"  {k:12}{f'{comp[k]}/{tot[k]}':>14}")
    nont = [i for i in ids if CLASS.get(i.split('@')[0]) != "TRUNCATED"]
    trc = [i for i in ids if CLASS.get(i.split('@')[0]) == "TRUNCATED"]
    cn = sum(a[i]["parent"] in ("red", "green", "error") for i in nont)
    ct = sum(a[i]["parent"] in ("red", "green", "error") for i in trc)
    ri = comp["INVENTED"] / tot["INVENTED"] if tot["INVENTED"] else 0
    rt = comp["TYPE/SEM"] / tot["TYPE/SEM"] if tot["TYPE/SEM"] else 0
    pair = all(a[i]["parent"] in ("red", "green", "error") for i in ids
               if CLASS.get(i.split('@')[0]) in ("PARSE", "UNUSED VAR"))
    wb, wa = collections.Counter(r["verdict"] for r in b.values()), collections.Counter(r["verdict"] for r in a.values())
    print(f"\nWHOLE BENCH\n  {'verdict':14}{'before':>8}{'after':>8}")
    for k in KEYS: print(f"  {k:14}{wb.get(k,0):>8}{wa.get(k,0):>8}")
    print(f"  {'KEPT':14}{sum(r['kept'] for r in b.values()):>8}{sum(r['kept'] for r in a.values()):>8}")
    nu = wa.get("USEFUL", 0) - wb.get("USEFUL", 0); nf = wa.get("FALSE-ALARM", 0) - wb.get("FALSE-ALARM", 0)
    print("\nREGISTERED PREDICTIONS -> OUTCOMES")
    for txt, p, hit in [
        ("P(>= 10 of the 20 non-truncated compile)", 0.45, cn >= 10),
        ("P(>= 15 of 20)", 0.20, cn >= 15),
        ("P(PARSE + UNUSED VAR both compile)", 0.60, pair),
        ("P(INVENTED converts lower than TYPE/SEMANTIC)", 0.55, ri < rt),
        ("P(all 3 TRUNCATED compile at 8000 tokens)", 0.40, ct == 3),
        ("P(USEFUL rises above 4)", 0.40, wa.get("USEFUL", 0) > 4),
        ("P(new FALSE ALARMS > new USEFUL)", 0.75, nf > nu),
    ]:
        print(f"  {txt:48} = {p:.2f} ... {'HIT' if hit else 'miss'}")
    print(f"\n  non-truncated compiled {cn}/20 · truncated {ct}/3 · INVENTED {ri:.0%} vs TYPE/SEM {rt:.0%}")
    print(f"  USEFUL {wb.get('USEFUL',0)} -> {wa.get('USEFUL',0)} · new false alarms {nf:+d}")
    print(f"  delve (the only router-blind task this arm can reach): {a.get('go-delve__delve@1f83848a',{}).get('verdict','?')}")


if __name__ == "__main__":
    sys.exit(main())
