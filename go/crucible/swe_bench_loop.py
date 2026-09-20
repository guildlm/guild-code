# -*- coding: utf-8 -*-
"""go_swe_bench — the ALGORITHM arm: declaration-level edits + a bounded repair loop fed by the Go
toolchain (compiler + the repository's EXISTING tests; the commit's hidden tests are never shown).
One draw yields a ladder: the verdict after round 0 is the single-shot edit-form number, the verdict
after the last round is the loop's. Every fragment, applied file set and feedback is saved.
    python swe_bench_loop.py --model qwen3-coder:30b-32k --rounds 2 --save data/go_swe_bench_v0_loop_<tag>.jsonl
    python swe_bench_loop.py --model gold --rounds 0          # instrument test: the gold fragment must pass 51/51
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
DECLEDIT = os.path.join(HERE, "tools", "decledit", "decledit")
GOIMPORTS = os.path.expanduser("~/go/bin/goimports")
spec = importlib.util.spec_from_file_location("h", os.path.join(HERE, "swe_bench_eval.py"))
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)

SYSTEM = ("You are a senior Go engineer fixing a bug in a real repository. You are given the commit message "
          "describing the bug and the current content of the files that may change. Reply with ONLY the "
          "top-level declarations you change or add (functions, methods, types, consts, vars), each inside a "
          "```go block whose first line is the comment `// file: <path>` exactly as given. A declaration you "
          "return replaces the existing declaration with the same name in that file; a new name is added. To "
          "remove a declaration write the line `// decledit: delete <Name>` (a method as `Type.Method`) inside "
          "the block. Put any new imports in an `import (...)` block inside the same file block. Do not repeat "
          "declarations you do not change. No commentary.")

FAIL_RE = re.compile(r"^--- FAIL: (\S+)", re.M)


def build_prompt(t, files, feedback=None):
    parts = [f"Commit message:\n{t['subject']}\n{t['body']}".rstrip(), ""]
    for p in t["src_files"]:
        parts.append(f"// file: {p}\n```go\n{files[p]}\n```")
    if feedback:
        parts.append("Your previous declarations were applied to the files above. The Go toolchain reports:\n"
                     f"```\n{feedback}\n```\nReturn only the declarations that fix this.")
    else:
        parts.append("Return only the declarations you change or add.")
    return "\n\n".join(parts)


def extract_fragments(out, wanted):
    """path -> concatenated fragment text; several blocks for one file are one fragment"""
    out = h.normalize(out)
    got, untagged, foreign = {}, [], []
    base = {os.path.basename(w): w for w in wanted}
    for before, inside, body in h.FILE_RE.findall(out):
        path = before or inside
        if path in wanted:
            got[path] = got.get(path, "") + "\n" + body
        elif path and os.path.basename(path) in base:
            got[base[os.path.basename(path)]] = got.get(base[os.path.basename(path)], "") + "\n" + body
        elif path:
            foreign.append(path)
        else:
            untagged.append(body)
    if len(wanted) == 1 and untagged:
        w = next(iter(wanted)); got[w] = got.get(w, "") + "\n" + "\n".join(untagged); untagged = []
    return got, untagged, foreign


def run(args, inp=None, cwd=None, env=None, timeout=600):
    p = subprocess.run(args, input=inp, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env)
    return p.returncode, p.stdout + p.stderr if inp is None else p.stdout, p.stderr


def apply_fragment(target_src, fragment, tmp):
    t, f = os.path.join(tmp, "target.go"), os.path.join(tmp, "fragment.go")
    open(t, "w").write(target_src); open(f, "w").write(fragment)
    p = subprocess.run([DECLEDIT, "-apply", "-target", t, "-fragment", f], capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        return None, p.stderr.strip()
    q = subprocess.run([GOIMPORTS], input=p.stdout, capture_output=True, text=True, timeout=120)
    return (q.stdout if q.returncode == 0 else p.stdout), (p.stderr.strip() + ("\n" + q.stderr.strip() if q.returncode else "")).strip()


def gold_fragment(before, after, tmp):
    b, a = os.path.join(tmp, "before.go"), os.path.join(tmp, "after.go")
    open(b, "w").write(before); open(a, "w").write(after)
    p = subprocess.run([DECLEDIT, "-changed", "-before", b, "-after", a], capture_output=True, text=True, timeout=120)
    return p.stdout


class Worktree:
    def __init__(self, cache, t, workroot):
        self.repo = os.path.join(cache, t["repo"]); self.t = t
        self.wt = os.path.join(workroot, "wt")
        h.sh(["git", "worktree", "remove", "--force", self.wt], self.repo); shutil.rmtree(self.wt, ignore_errors=True)
        if h.sh(["git", "worktree", "add", "--detach", self.wt, t["parent"]], self.repo)[0]:
            raise RuntimeError("worktree")

    def write(self, files):
        for p, src in files.items():
            with open(os.path.join(self.wt, p), "w", encoding="utf-8") as f:
                f.write(src)

    def pkgs(self):
        return [f"./{p}" if p != "." else "." for p in self.t["packages"]]

    def close(self):
        h.sh(["git", "worktree", "remove", "--force", self.wt], self.repo); shutil.rmtree(self.wt, ignore_errors=True)


def toolchain(t, files, cache, env, workroot):
    """(kind, output): build errors, else the EXISTING tests of the changed packages (hidden tests absent)"""
    wt = Worktree(cache, t, workroot)
    try:
        wt.write(files)
        # build = compile the packages AND their tests without running one; `go build` alone refuses
        # test-only packages ("no non-test Go files", a false alarm on the gold fix). No vet: not a judge.
        # The parent's STALE versions of the commit's test files stay in place (deleting them strips helpers
        # other tests use — 9 false alarms in gold run 2); their errors are filtered out in feedback_text.
        rc, out = h.sh(["go", "test", "-count=1", "-run", "^$"] + wt.pkgs(), wt.wt, env)
        if rc:
            return "build", out
        rc, out = h.sh(["go", "test", "-count=1", "-timeout", "180s"] + wt.pkgs(), wt.wt, env)
        return ("test" if rc else "ok"), out
    finally:
        wt.close()


ERR_LINE_RE = re.compile(r"^(?:vet: )?(\S+?\.go):\d+:\d+:")


def in_stale(line, hidden_paths):
    """an error line located in one of the commit's own test files (the parent's stale version)"""
    m = ERR_LINE_RE.match(line.strip())
    return bool(m) and os.path.basename(m.group(1)) in {os.path.basename(p) for p in hidden_paths}


def feedback_text(kind, out, baseline_fails, hidden_paths, stale_names, limit=3000):
    """what the loop is told; None = nothing actionable. Errors inside the commit's own test files (stale at
    the parent: a fix that changes an API breaks the old test the commit rewrote) and failures of the tests
    those files define are NOT feedback — the gold fix trips them (5/51 on 2026-09-20). The hidden judge
    is unchanged by this: filtering only removes false alarms, it cannot make a wrong fix pass."""
    if kind == "build":
        lines = [l for l in out.splitlines() if ERR_LINE_RE.match(l.strip()) and not in_stale(l, hidden_paths)]
        return "\n".join(lines)[:limit] or None
    fails = set(FAIL_RE.findall(out)) - baseline_fails - stale_names
    build_lines = [l for l in out.splitlines() if ERR_LINE_RE.match(l.strip()) and not in_stale(l, hidden_paths)]
    if not fails and not build_lines:
        return None
    keep, take = [], False
    for l in out.splitlines():
        m = FAIL_RE.match(l)
        if m:
            take = m.group(1) in fails
        if take or (ERR_LINE_RE.match(l.strip()) and not in_stale(l, hidden_paths)) or (take and "panic" in l):
            keep.append(l)
    return "\n".join(keep)[:limit] or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default=os.path.join(HERE, "data", "go_swe_bench_v0_eval.jsonl"))
    ap.add_argument("--cache", default=os.path.join(HERE, "..", "datasets", "mining", "repos"))
    ap.add_argument("--model", required=True, help="Ollama model name, or 'gold' for the instrument test")
    ap.add_argument("--base-url", default="http://localhost:11434/v1")
    ap.add_argument("--temp", type=float, default=0.0); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=6000)
    ap.add_argument("--rounds", type=int, default=2, help="repair rounds after the first edit")
    ap.add_argument("--save"); ap.add_argument("--ids"); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--selftests", help="self-test rows (swe_bench_selftest_writer.py); KEPT tests feed the loop and are never the judge")
    ap.add_argument("--no-peek", action="store_true",
                    help="stop only on the loop's OWN signals (toolchain + self-test silent) or K; never on the hidden verdict. "
                         "The ladder then records the state after each round, so a false alarm that breaks a right fix is COUNTED.")
    a = ap.parse_args()
    tasks = [json.loads(l) for l in open(a.bench)]
    if a.limit:
        tasks = tasks[:a.limit]
    if a.ids:
        keep = set(a.ids.split(",")); tasks = [t for t in tasks if f"{t['repo']}@{t['sha'][:8]}" in keep]
    env = dict(os.environ, GOFLAGS="-mod=mod", GOTOOLCHAIN="auto", CGO_ENABLED="0")
    workroot = tempfile.mkdtemp(prefix="goswe-loop-"); tmp = tempfile.mkdtemp(prefix="decledit-")
    selftests = {}
    if a.selftests:
        W = importlib.util.module_from_spec(importlib.util.spec_from_file_location("W", os.path.join(HERE, "swe_bench_selftest_writer.py")))
        W.__spec__.loader.exec_module(W)
        selftests = {r["id"]: r["test"] for r in (json.loads(l) for l in open(a.selftests)) if r.get("kept")}
        print(f"self-tests: {len(selftests)} kept tests loaded from {a.selftests}", flush=True)
    done = {}
    if a.save and os.path.exists(a.save):
        done = {r["id"]: r for r in (json.loads(l) for l in open(a.save))}
        print(f"resuming: {len(done)} rows already in {a.save}", flush=True)
    out_f = open(a.save, "a") if a.save else None
    ladder = [0] * (a.rounds + 1); rows = []; t0 = time.time()
    for t in tasks:
        tid = f"{t['repo']}@{t['sha'][:8]}"
        if tid in done:
            r = done[tid]; rows.append(r)
            for i, v in enumerate(r["ladder"]):
                ladder[i] += v
            continue
        files = dict(t["before"]); wanted = set(t["src_files"])
        # baseline: what the EXISTING tests say at the parent, so only NEW failures are fed back
        kind0, out0 = toolchain(t, files, a.cache, env, workroot)
        baseline_fails = set(FAIL_RE.findall(out0)) if kind0 == "test" else set()
        stale_names = set()  # tests defined by the parent's versions of the commit's own test files
        for p in t["tests"]:
            rc, src = h.sh(["git", "show", f"{t['parent']}:{p}"], os.path.join(a.cache, t["repo"]))
            if rc == 0:
                stale_names |= set(re.findall(r"^func (Test\w+)", src, re.M))
        rounds, verdicts, feedback = [], [], None
        for rnd in range(a.rounds + 1):
            if a.model == "gold":
                out = "\n".join(f"// file: {p}\n```go\n{gold_fragment(t['before'][p], t['after'][p], tmp)}\n```" for p in t["src_files"])
            else:
                try:
                    out = h.ask(a.base_url, a.model, build_prompt(t, files, feedback), a.temp, a.max_tokens, a.seed)
                except Exception as e:  # noqa: BLE001
                    out = f"ERR {type(e).__name__}"
            frags, untagged, foreign = extract_fragments(out, wanted)
            notes = []
            if foreign:
                notes.append("ignored blocks for files not in the task: " + ", ".join(foreign))
            if untagged:
                notes.append(f"ignored {len(untagged)} untagged block(s): every block must start with // file: <path>")
            new_files = dict(files); applied = 0
            for p, frag in frags.items():
                src, msg = apply_fragment(files[p], frag, tmp)
                if src is None:
                    notes.append(f"{p}: {msg}")
                else:
                    new_files[p] = src; applied += 1
                    if msg:
                        notes.append(f"{p}: {msg}")
            st_kind, st_fails = None, set()
            if applied:
                files = new_files
                kind, tout = toolchain(t, files, a.cache, env, workroot)
                fb = feedback_text(kind, tout, baseline_fails, t["tests"], stale_names)
                if tid in selftests:  # the self-test, in isolation, on the candidate files
                    st_kind, st_fails, st_out = W.run_selftest(t, files, selftests[tid], a.cache, env, workroot)
                    if st_kind != "green":
                        st_fb = W.selftest_feedback(st_kind, st_fails, st_out)
                        fb = (fb + "\n" if fb else "") + st_fb
            else:
                kind, tout, fb = "noop", "", "no declaration was applied"
            if notes:
                fb = ("\n".join(notes) + ("\n" + fb if fb else "")) if fb or notes else fb
            ok, tail = h.score(t, files, a.cache, env, workroot)
            verdicts.append(ok)
            rounds.append({"round": rnd, "output": out, "applied": applied, "toolchain": kind, "feedback": fb,
                           "selftest": st_kind, "selftest_fails": sorted(st_fails),
                           "hidden_verdict": ok, "hidden_tail": tail[-400:]})
            print(f"  r{rnd} {tid:36} applied={applied} toolchain={kind:5} selftest={st_kind or '-':9} hidden={'PASS' if ok else 'fail'}"
                  f"{'  fb: ' + fb.strip().splitlines()[0][:70] if fb else ''}", flush=True)
            if fb is None or (ok and not a.no_peek):  # nothing left for the loop to act on (or, registered v1: hidden pass)
                break
            feedback = fb
        if a.no_peek:  # the state after each round; the last state is carried when the loop stopped early on its own
            lad = [verdicts[i] if i < len(verdicts) else verdicts[-1] for i in range(a.rounds + 1)]
        else:  # ladder: the verdict at each round, carried forward once green (the loop stops there)
            lad = [any(verdicts[:i + 1]) if i < len(verdicts) else any(verdicts) for i in range(a.rounds + 1)]
        for i, v in enumerate(lad):
            ladder[i] += v
        r = {"id": tid, "model": a.model, "parent_status": t["parent_status"], "ladder": lad, "rounds": rounds,
             "baseline_toolchain": kind0, "selftest_used": tid in selftests, "no_peek": a.no_peek,
             "final_files": files if a.model != "gold" else None}
        rows.append(r)
        print(f"{'+' if lad[-1] else '-'} {tid:40} [{t['parent_status']}] ladder={''.join('1' if v else '0' for v in lad)} {t['subject'][:50]}", flush=True)
        if out_f:
            out_f.write(json.dumps(r) + "\n"); out_f.flush()
    n = len(rows)
    print(f"\n{a.model}: pass@1 ladder by round " + " · ".join(f"r{i}={v}/{n}" for i, v in enumerate(ladder)) +
          f" · wall {time.time()-t0:.0f}s", flush=True)
    shutil.rmtree(workroot, ignore_errors=True); shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
