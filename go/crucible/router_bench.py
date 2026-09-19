# -*- coding: utf-8 -*-
"""Test-gated router over saved go_dev_bench candidates — does a SELF-WRITTEN test cash the union?
Candidates are prior runs' committed generations (as drawn; their hidden verdicts are the saved
`verdict` field). The go-test role writes a test from the task PROMPT ONLY, never seeing a
candidate. Each candidate is run against that self-test, and the arms registered in
PREREG-router-does-a-self-written-test-cash-the-union.txt pick. Reported: every arm, self-test
validity on the task's reference solution, and each route change with its hidden outcome.
    python router_bench.py --candidates 30b=data/...served_t0.jsonl 7b=data/...base7b_greedy.jsonl \
        --test-writer qwen3-coder:30b --save-tests data/router_selftests_30b.jsonl
    python router_bench.py --candidates ... --load-tests data/router_selftests_30b.jsonl   # offline
"""
import argparse
import json
import os
import sys
import time
import subprocess
import tempfile
import urllib.request

from mlx_bench import compiles, runs_green  # noqa: E402
from mlx_test_bench import SYSTEM as SYSTEM_TEST, _goimports, _repair_imports, extract_code  # noqa: E402


STRIPDECL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "stripdecl", "stripdecl")


def strip_redecl(impl: str, test: str) -> str:
    """POST-HOC deterministic repair (not in the prereg): drop from the test file every top-level
    declaration whose name the implementation under test already declares. The 2026-09-19 autopsy
    found 42/48 (30B) and 22/48 (7B) self-tests re-implemented the function under test, which
    made them uncompilable — a FORM defect the machine can fix, like goimports. Sees only the
    candidate being tested, never the reference."""
    if not test.strip():
        return test
    if not os.path.exists(STRIPDECL):
        subprocess.run(["go", "build", "-o", "stripdecl", "."], cwd=os.path.dirname(STRIPDECL), check=True)
    with tempfile.TemporaryDirectory() as d:
        ip, tp = os.path.join(d, "impl.go"), os.path.join(d, "impl_test.go")
        open(ip, "w").write(impl); open(tp, "w").write(test)
        p = subprocess.run([STRIPDECL, "-impl", ip, "-test", tp], capture_output=True, text=True, timeout=60)
    return p.stdout if p.returncode == 0 and p.stdout.strip() else test


def load(path):
    return {json.loads(l)["id"]: json.loads(l) for l in open(path)}


def ask(base_url, model, prompt, temp, max_tokens, seed):
    body = json.dumps({"model": model, "temperature": temp, "max_tokens": max_tokens, "seed": seed,
                       "messages": [{"role": "system", "content": SYSTEM_TEST},
                                    {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"] or ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", nargs="+", required=True, help="NAME=path, preferred first")
    ap.add_argument("--bench", default=os.path.join(os.path.dirname(__file__), "data", "go_dev_bench.jsonl"))
    ap.add_argument("--test-writer", help="served model that writes the self-test")
    ap.add_argument("--base-url", default="http://localhost:11434/v1")
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=900)
    ap.add_argument("--save-tests", metavar="PATH")
    ap.add_argument("--load-tests", metavar="PATH", help="reuse saved self-tests (no model)")
    ap.add_argument("--repair-redecl", action="store_true",
                    help="POST-HOC arm: strip test declarations that collide with the candidate under test")
    a = ap.parse_args()

    names, cands = [], {}
    for spec in a.candidates:
        n, p = spec.split("=", 1)
        names.append(n)
        cands[n] = load(p)
    pref, alt = names[0], names[1]
    tasks = [json.loads(l) for l in open(a.bench)]
    ids = [t["id"] for t in tasks]
    imports_exe = _goimports()

    # 1. self-tests: generate or load
    tests = {}
    if a.load_tests:
        tests = {r["id"]: r for r in (json.loads(l) for l in open(a.load_tests))}
        print(f"loaded {len(tests)} self-tests from {a.load_tests}")
    else:
        if not a.test_writer:
            sys.exit("--test-writer or --load-tests required")
        t0 = time.time()
        for t in tasks:
            try:
                out = ask(a.base_url, a.test_writer, t["prompt"], a.temp, a.max_tokens, a.seed)
                code = extract_code(out)
                if imports_exe:
                    code = _repair_imports(code, imports_exe)
            except Exception as e:  # noqa: BLE001
                code = ""
                print(f"  {t['id']}: ERR {type(e).__name__}", file=sys.stderr)
            tests[t["id"]] = {"id": t["id"], "writer": a.test_writer, "test": code}
        print(f"generated {len(tests)} self-tests with {a.test_writer} in {time.time()-t0:.0f}s")

    # 2. evaluate self-tests: validity on the reference, verdict per candidate
    for t in tasks:
        r = tests[t["id"]]
        test = r["test"]
        if a.repair_redecl:
            r["valid_on_reference_repaired"] = bool(test) and runs_green(t["reference"], strip_redecl(t["reference"], test))
            r["self_repaired"] = {n: bool(test) and runs_green(cands[n][t["id"]]["code"], strip_redecl(cands[n][t["id"]]["code"], test)) for n in names}
            r["valid_on_reference"], r["self"] = r["valid_on_reference_repaired"], r["self_repaired"]
        else:
            r["valid_on_reference"] = bool(test) and runs_green(t["reference"], test)
            r["self"] = {n: bool(test) and runs_green(cands[n][t["id"]]["code"], test) for n in names}
    if a.save_tests:
        with open(a.save_tests, "w") as f:
            for i in ids:
                f.write(json.dumps(tests[i]) + "\n")
        print(f"wrote self-tests + verdicts -> {a.save_tests}")

    # 3. arms
    hidden = {n: {i: bool(cands[n][i]["verdict"]) for i in ids} for n in names}
    builds = {n: {i: bool(cands[n][i]["compiles"]) for i in ids} for n in names}

    def score(choice):  # choice: id -> candidate name
        return sum(hidden[choice[i]][i] for i in ids)

    oracle = sum(any(hidden[n][i] for n in names) for i in ids)
    best = {i: pref for i in ids}
    compile_gate = {i: (pref if builds[pref][i] else alt) for i in ids}
    strict, loose, loose7, valid_only = {}, {}, {}, {}
    for i in ids:
        s = tests[i]["self"]
        strict[i] = alt if (not s[pref] and s[alt]) else pref
        loose[i] = pref if s[pref] else (alt if s[alt] else pref)
        loose7[i] = pref if s[pref] else alt
        valid_only[i] = strict[i] if tests[i]["valid_on_reference"] else pref

    valid = sum(tests[i]["valid_on_reference"] for i in ids)
    print(f"\n{'[POST-HOC redecl repair] ' if a.repair_redecl else ''}self-test validity on reference: {valid}/48   (tests present: {sum(bool(tests[i]['test']) for i in ids)}/48)")
    print(f"{'arm':14} {'pass@1':>7}  switches (id:from->to = hidden outcome)")
    for label, ch in [("oracle-union", None), (f"best-{pref}", best), ("compile-gate", compile_gate),
                      ("STRICT", strict), ("LOOSE", loose), (f"LOOSE-{alt}fb", loose7), ("VALID-ONLY", valid_only)]:
        if ch is None:
            print(f"{label:14} {oracle:>4}/48"); continue
        sw = [f"{i}:{pref}->{ch[i]}={'+' if hidden[ch[i]][i] else '-'}(was {'+' if hidden[pref][i] else '-'})"
              for i in ids if ch[i] != pref]
        print(f"{label:14} {score(ch):>4}/48  {len(sw)} switches  {' '.join(sw)}")
    # the two tasks the whole question rests on
    focus = [i for i in ids if builds[pref][i] and not hidden[pref][i] and hidden[alt][i]]
    print(f"\nfocus tasks ({pref} builds but wrong, {alt} right): {focus}")
    for i in focus:
        s = tests[i]["self"]
        print(f"  {i}: self-test valid_on_ref={tests[i]['valid_on_reference']}  fails {pref}={not s[pref]}  passes {alt}={s[alt]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
