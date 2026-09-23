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


FORM_RETRY = ("Your previous answer contained no test function. It is not usable: the package already "
              "contains the implementation, and repeating it is an error. Return ONLY a Go test file: "
              "a package clause, imports, and one or more `func TestXxx(t *testing.T)` functions that "
              "call the existing API and fail on the buggy code above. Do not output the implementation.")


EXEMPLAR_CAP = 6000
EXEMPLAR_NOTE = ("// An existing test file from the same package, at this commit. It shows the package's real API "
                 "and test conventions.\n// It is NOT about this bug: do not copy its cases or its assertions.")


def exemplar_for(t, cache):
    """The registered selection rule (PREREG-testwriter-exemplar-show-it-a-neighbour.txt): among the
    _test.go files in the package directory of src_files[0], at the PARENT commit, excluding every path
    the fix commit touches, take the LARGEST at most EXEMPLAR_CAP bytes; if none fits, the smallest,
    truncated at a line boundary. Returns (path, source) or None. Cannot leak: the parent predates the
    fix and the commit's own test files are excluded by path."""
    repo = os.path.join(cache, t["repo"].replace("/", "__"))
    pkgdir = os.path.dirname(t["src_files"][0])
    try:
        listing = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "--name-only", t["parent"]],
                                 capture_output=True, text=True, timeout=120)
    except Exception:  # noqa: BLE001
        return None
    if listing.returncode != 0:
        return None
    sib = [p for p in listing.stdout.split("\n")
           if p.endswith("_test.go") and os.path.dirname(p) == pkgdir and p not in t["tests"]]
    if not sib:
        return None
    sized = []
    for p in sib:
        q = subprocess.run(["git", "-C", repo, "cat-file", "-s", f"{t['parent']}:{p}"],
                           capture_output=True, text=True, timeout=60)
        sized.append(((int(q.stdout.strip()) if q.stdout.strip().isdigit() else 10 ** 9), p))
    under = [x for x in sized if x[0] <= EXEMPLAR_CAP]
    _, path = max(under) if under else min(sized)
    q = subprocess.run(["git", "-C", repo, "show", f"{t['parent']}:{path}"],
                       capture_output=True, text=True, timeout=60)
    if q.returncode != 0 or not q.stdout.strip():
        return None
    src = q.stdout
    if len(src) > EXEMPLAR_CAP:
        src = src[:EXEMPLAR_CAP].rsplit("\n", 1)[0] + "\n// ... (truncated)\n"
    return path, src


COMPILE_RETRY = ("The test file you wrote does not compile against the code above. The Go toolchain reports:\n"
                 "{errors}\n"
                 "Fix these. Use only symbols that exist in the files above. Return the complete test file.")
TRUNCATED_RETRY = "Your previous answer was cut off before the file was complete. Return the whole test file."


def compiler_errors(out, limit=1500):
    """the self-test's own error lines, verbatim, as the toolchain printed them"""
    lines = [l for l in out.splitlines()
             if (SELFTEST_NAME in l and re.search(r"\.go:\d+:\d+:", l)) or "no matching versions" in l]
    return "\n".join(lines)[:limit]


def was_truncated(out):
    """a generation cut off at max_tokens leaves an odd number of fences"""
    return out.count("```") % 2 == 1


def pkg_of(src):
    m = re.search(r"^package\s+(\w+)", src, re.M)
    return m.group(1) if m else "main"


def build_prompt(t, exemplar=None):
    parts = [f"Commit message:\n{t['subject']}\n{t['body']}".rstrip(), ""]
    for p, src in t["before"].items():
        parts.append(f"// file: {p}\n```go\n{src}\n```")
    if exemplar:
        ep, esrc = exemplar
        parts.append(f"{EXEMPLAR_NOTE}\n// file: {ep}\n```go\n{esrc}\n```")
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


def repair(test_src, t, tmp, cache=None, workroot=None):
    """stripdecl against every source file of the task's package, then goimports.
    With cache/workroot, goimports runs INSIDE the parent worktree (-srcdir = the package dir), so it can
    resolve the module's own packages. Until 2026-09-23 it ran on a file in tmp, outside any module, and
    could only add stdlib and module-cache imports: rqlite's self-test used cluster/servicetest by its
    correct name and was scored 'undefined: servicetest' for want of one import line. Measured on the
    keeptests draw: 1 row of 51 changes imports; 7 others are parse errors either way."""
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
    if cache is None:
        q = subprocess.run([GOIMPORTS, tpath], capture_output=True, text=True, timeout=60)
    else:
        wt = L.Worktree(cache, t, workroot)
        try:
            wt.write(dict(t["before"]))
            q = subprocess.run([GOIMPORTS, "-srcdir", os.path.join(wt.wt, pkgdir or "."), tpath],
                               capture_output=True, text=True, timeout=60, cwd=wt.wt)
        finally:
            wt.close()
    return q.stdout if q.returncode == 0 and q.stdout.strip() else open(tpath).read()


UNUSED_RE = re.compile(r"zz_swe_selftest_test\.go:(\d+):\d+: declared and not used: (\w+)")


def silence_unused(test_src, out):
    """deterministic: for every 'declared and not used: x' the compiler reports in the self-test, add `_ = x`
    right after that line (the writer's tests set counters and flags it never asserts; stripdecl can also
    orphan a variable by dropping the re-implemented function that used it). One pass, nothing invented."""
    hits = UNUSED_RE.findall(out)
    if not hits:
        return None
    lines = test_src.split("\n")
    for ln, name in sorted({(int(l), n) for l, n in hits}, reverse=True):
        if 1 <= ln <= len(lines):
            indent = re.match(r"\s*", lines[ln - 1]).group(0)
            lines.insert(ln, f"{indent}_ = {name}")
    return "\n".join(lines)


TOPLEVEL_RE = re.compile(r"^(?:func\s+(\w+)\s*\(|type\s+(\w+)\b|var\s+(\w+)\b|const\s+(\w+)\b)", re.M)


def top_level_names(src):
    """package-level declarations, methods excluded (a method name cannot redeclare), and the blank
    identifier excluded (`var _ = x` in two files is legal; counting it deleted go-kit's instancer_test.go
    on a collision that could not happen)"""
    return {next(g for g in m.groups() if g) for m in TOPLEVEL_RE.finditer(src or "")} - {"_"}


def test_names(src):
    return set(re.findall(r"^func (Test\w+)\s*\(", src, re.M))


def run_selftest(t, files, test_src, cache, env, workroot, keep_pkg_tests=False):
    """-> (status, failing self-test names, output)
    status: 'nocompile' (the self-test itself does not build) | 'red' | 'green' | 'error' (the package/test binary broke elsewhere)

    ISOLATION, two settings:
      keep_pkg_tests=False (the rule until 2026-09-22): every _test.go in the package dir is removed.
        Safe against leakage and WRONG about the task: it also deletes the package's test FIXTURES, so
        a self-test may not use the helpers a human test author uses. Measured cost: the gold test
        itself does not compile under this rule on 16 of 51 tasks.
      keep_pkg_tests=True: the package's test files stay as they are AT THE PARENT, so the self-test
        has the fixtures a human test author has. Leakage is impossible by construction and not by
        deletion: the worktree is `git worktree add --detach <parent>`, and the gold test arrives
        with the FIX, so it is never on disk. The only file removed is one that would REDECLARE a
        name the self-test declares. Sibling tests are compiled but NOT RUN: -run is restricted to
        the self-test's own function names, so a sibling's red can never be read as the self-test's.
        Measured against the first form of this rule, which deleted the fix's test files by name:
        that form broke every sibling depending on a helper defined in them, 6 scored rows -> error."""
    pkgdir = os.path.dirname(t["src_files"][0]) or "."
    wt = L.Worktree(cache, t, workroot)
    try:
        wt.write(files)
        d = os.path.join(wt.wt, pkgdir)
        for f in os.listdir(d):
            if not f.endswith("_test.go"):
                continue
            if not keep_pkg_tests:
                os.remove(os.path.join(d, f)); continue
            # THE RULE (2026-09-22, second form). The worktree is at the PARENT, so the gold test --
            # which arrives with the fix -- is not on disk at all and there is nothing to delete for
            # leakage. Deleting the fix's test file BY NAME (the first form) was still wrong: every
            # sibling that uses a helper defined in it stopped compiling, and 6 scored rows turned
            # into 'error'. So delete nothing for safety and delete only for COLLISION: a file that
            # declares a top-level name the self-test also declares would be a redeclaration.
            with open(os.path.join(d, f), encoding="utf-8", errors="ignore") as fh:
                other = fh.read()
            if top_level_names(other) & top_level_names(test_src):
                os.remove(os.path.join(d, f))
        with open(os.path.join(d, SELFTEST_NAME), "w", encoding="utf-8") as f:
            f.write(test_src)
        names = test_names(test_src)
        run = f"^({'|'.join(sorted(names))})$" if (keep_pkg_tests and names) else "^Test"
        rc, out = h.sh(["go", "test", "-count=1", "-timeout", "120s", "-run", run, f"./{pkgdir}" if pkgdir != "." else "."], wt.wt, env)
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
    ap.add_argument("--no-exemplar", dest="exemplar", action="store_false",
                    help="do NOT show the writer an untouched sibling _test.go from the same package at "
                         "the parent commit. The exemplar is ON by default since 2026-09-21: it is the "
                         "only change in the campaign to move USEFUL (2 -> 4) and it bought the router "
                         "its first switch. Pass this to reproduce any draw made before that date.")
    ap.set_defaults(exemplar=True)
    ap.add_argument("--compile-retry", action="store_true",
                    help="when the self-test does not compile at the parent, re-ask ONCE: with the "
                         "toolchain's own error lines, or -- if the first output was cut off -- with the "
                         "original prompt at 8000 tokens. Registered in "
                         "PREREG-testwriter-compile-retry-hand-back-the-compilers-own-words.txt.")
    ap.add_argument("--form-retry", type=int, default=1,
                    help="if the extracted block has no TestXxx, re-ask the model this many times with "
                         "the registered FORM_RETRY turn appended. DEFAULT 1 since 2026-09-21: the arm "
                         "measured 16/16 conversion for one turn, so it is free and removes a whole "
                         "failure class. Pass 0 to reproduce any draw made before that date. The first "
                         "output is never scored: one retry, not best-of-two.")
    ap.add_argument("--keep-package-tests", action="store_true",
                    help="keep the package's OTHER _test.go files at compile time and delete only the fix "
                         "commit's own test files (the gold). The self-test is then written against what a "
                         "human test author actually has. Sibling tests are compiled, never run: -run is "
                         "restricted to the self-test's own names. Off by default so every draw before "
                         "2026-09-22 reproduces byte-identically.")
    ap.add_argument("--rescore", help="re-extract, re-repair and re-score the raw outputs of this earlier draw (no model call)")
    a = ap.parse_args()
    prior, prior_test = {}, {}
    if a.rescore:
        for r in (json.loads(l) for l in open(a.rescore)):
            prior[r["id"]] = r["output"]
            # An instrument A/B must replay the artifact that was SCORED, not the last text the
            # model happened to produce. Where the earlier row carries its post-repair test, that
            # is the artifact; re-extracting from "output" can yield a different program entirely.
            if r.get("test"):
                prior_test[r["id"]] = r["test"]
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
        ex = None
        if tid in prior:
            out = prior[tid]
        elif a.model == "hidden":  # instrument test: the commit's own test file plays the self-test (no model)
            pkgdir = os.path.dirname(t["src_files"][0])
            cands = [p for p in t["tests"] if os.path.dirname(p) == pkgdir]
            out = "```go\n" + (t["tests"][cands[0]] if cands else "") + "\n```"
        else:
            try:
                ex = exemplar_for(t, a.cache) if a.exemplar else None
                if a.exemplar:
                    print(f"{tid:40} exemplar: {ex[0] if ex else 'NONE in this package'}", flush=True)
                out = h.ask(a.base_url, a.model, build_prompt(t, ex), a.temp, a.max_tokens, a.seed)
            except Exception as e:  # noqa: BLE001
                out = f"ERR {type(e).__name__}"
        raw = extract_test(out)
        replay = prior_test.get(tid) if a.rescore else None
        # FORM CHECK (registered, deterministic): an output with no TestXxx is rejected and re-asked.
        # The rejected output is never scored -- one retry, not best-of-two.
        form_hist, tries = [], 0
        while (a.form_retry and tries < a.form_retry and not (a.rescore or a.model == "hidden")
               and (raw is None or not test_names(raw))):
            form_hist.append(out)
            tries += 1
            print(f"{tid:40} form failure (no TestXxx) -> re-asking {tries}/{a.form_retry}", flush=True)
            try:
                out = h.ask(a.base_url, a.model, build_prompt(t, ex) + "\n\n" + FORM_RETRY,
                            a.temp, a.max_tokens, a.seed)
            except Exception as e:  # noqa: BLE001
                out = f"ERR {type(e).__name__}"
            raw = extract_test(out)
        row = {"id": tid, "model": a.model, "parent_status": t["parent_status"], "output": out, "test": None,
               "parent": None, "gold": None, "parent_fails": [], "gold_fails": [], "kept": False,
               "form_retries": tries, "form_rejected": form_hist}
        if replay or raw:
            test_src = replay if replay else repair(raw, t, tmp, a.cache, workroot)
            row["test"] = test_src
            row["replayed"] = bool(replay)
            st_p, f_p, out_p = run_selftest(t, dict(t["before"]), test_src, a.cache, env, workroot, a.keep_package_tests)
            if st_p == "nocompile":
                fixed = silence_unused(test_src, out_p)
                if fixed:
                    silenced = {n for _, n in UNUSED_RE.findall(out_p)}
                    st2, f2, out2 = run_selftest(t, dict(t["before"]), fixed, a.cache, env, workroot, a.keep_package_tests)
                    # DO NO HARM (2026-09-21): the insertion can land outside the variable's scope and
                    # turn "declared and not used: x" into "undefined: x", which is worse than the
                    # error it was fixing. Measured on gorilla/mux: 1 injury in 6 firings. Keep the
                    # repair only when it introduces no new undefined among the names it silenced.
                    if silenced & set(re.findall(r"undefined: (\w+)", out2)):
                        row["unused_repair_reverted"] = True
                    else:
                        test_src = fixed; row["test"] = test_src; row["unused_repaired"] = True
                        st_p, f_p, out_p = st2, f2, out2
            # COMPILE RETRY (registered): the condition is the toolchain's, and so is the message.
            if (a.compile_retry and st_p == "nocompile" and not (a.rescore or a.model == "hidden")):
                cut = was_truncated(out)
                extra = TRUNCATED_RETRY if cut else COMPILE_RETRY.format(errors=compiler_errors(out_p))
                row["compile_retry"] = "tokens" if cut else "errors"
                row["compile_rejected"] = out
                print(f"{tid:40} does not compile -> re-asking ({row['compile_retry']})", flush=True)
                try:
                    out = h.ask(a.base_url, a.model, build_prompt(t, ex) + "\n\n" + extra, a.temp,
                                8000 if cut else a.max_tokens, a.seed)
                except Exception as e:  # noqa: BLE001
                    out = f"ERR {type(e).__name__}"
                raw2 = extract_test(out)
                if raw2 and test_names(raw2):
                    test_src = repair(raw2, t, tmp, a.cache, workroot); row["test"] = test_src
                    st_p, f_p, out_p = run_selftest(t, dict(t["before"]), test_src, a.cache, env, workroot, a.keep_package_tests)
                    if st_p == "nocompile":
                        fixed = silence_unused(test_src, out_p)
                        if fixed:
                            silenced = {n for _, n in UNUSED_RE.findall(out_p)}
                            st2, f2, out2 = run_selftest(t, dict(t["before"]), fixed, a.cache, env, workroot, a.keep_package_tests)
                            if not (silenced & set(re.findall(r"undefined: (\w+)", out2))):
                                test_src = fixed; row["test"] = test_src; row["unused_repaired"] = True
                                st_p, f_p, out_p = st2, f2, out2
                    row["output"] = out          # the retry was accepted: it is the answer now
                else:
                    # DISCARDED retry (2026-09-22): row["output"] used to be overwritten here
                    # unconditionally, so for every row whose retry had no TestXxx the record kept
                    # the DISCARDED text as "output" and filed the SCORED text under
                    # "compile_rejected" -- the two names inverted on exactly the rows that failed.
                    # Any later reader of "output" then re-derives a different program from the one
                    # that was scored; --rescore was the first consumer to hit it, on 3 rows.
                    row["compile_discarded"] = out
            row["parent"], row["parent_fails"] = st_p, sorted(f_p)
            row["kept"] = st_p == "red"
            st_g, f_g, out_g = run_selftest(t, dict(t["after"]), test_src, a.cache, env, workroot, a.keep_package_tests)
            row["gold"], row["gold_fails"] = st_g, sorted(f_g)
            row["parent_tail"], row["gold_tail"] = out_p[-400:], out_g[-400:]
        has_tests = bool(row["test"]) and bool(test_names(row["test"]))
        verdict = ("no-test" if not has_tests else
                   "USEFUL" if row["kept"] and row["gold"] == "green" else
                   "FALSE-ALARM" if row["kept"] and row["gold"] in ("red", "nocompile") else
                   "toothless" if row["parent"] == "green" else
                   "nocompile" if row["parent"] == "nocompile" else row["parent"] or "?")
        if not has_tests:
            row["kept"] = False
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
