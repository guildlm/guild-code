# -*- coding: utf-8 -*-
"""go_swe_bench — mine REAL bug-fix commits with a co-changed test into verified tasks.
The inverse of datasets/mining/mine_git_history.py (which drops _test.go by design, because it
made SFT data). A task is a commit where:
  * the subject classifies as a bug fix (same regex as the SFT miner — shared, not copied),
  * >= 1 non-test .go file is MODIFIED and >= 1 _test.go is modified/added, <= --max-files .go
    files in total, and no go.mod/go.sum change (dependency changes are a different task),
  * VERIFIED with the Go toolchain: at the commit, the changed packages' tests PASS; at the
    parent, with the commit's version of the test files copied in, they FAIL (a compile error
    counts as a failure and is labelled `compile_error`, a red test as `test_fail`).
Everything the task needs is stored: the message (the "issue"), the source files before and
after, the test files, the gold patch, the failing test names. No LLM anywhere in the build.
    python mine_swe_tasks.py --cache ../datasets/mining/repos --out data/go_swe_bench_v0.jsonl \
        --per-repo 6 --max-files 4
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datasets", "mining"))
from mine_git_history import _BUGFIX, _JUNK  # noqa: E402  shared classifier, never copied

DELIM = "\x02COMMIT\x02"


def sh(args, cwd, timeout=600, env=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode, p.stdout, p.stderr


def log_commits(repo, n):
    rc, out, _ = sh(["git", "log", "--no-merges", "--first-parent", f"-n{n}", "--name-status",
                     f"--format={DELIM}%H%x01%P%x01%s%x01%b"], repo)
    if rc:
        return []
    commits = []
    for block in out.split(DELIM)[1:]:
        head, _, rest = block.partition("\n")
        parts = head.split("\x01")
        if len(parts) < 4:
            continue
        sha, parents, subject, body = parts[0], parts[1].split(), parts[2], parts[3]
        files = []
        for line in rest.splitlines():
            if "\t" in line:
                st, path = line.split("\t", 1)
                files.append((st[0], path.split("\t")[-1]))
        commits.append({"sha": sha, "parent": parents[0] if parents else None, "subject": subject,
                        "body": body.strip(), "files": files})
    return commits


def candidate(c, max_files):
    if not c["parent"] or _JUNK.match(c["subject"]) or not _BUGFIX.search(c["subject"]):
        return None
    paths = [p for _, p in c["files"]]
    if any(p.endswith(("go.mod", "go.sum")) for p in paths):
        return None
    go = [(s, p) for s, p in c["files"] if p.endswith(".go")]
    if not go or len(go) > max_files or len(go) != len(c["files"]):
        return None  # .go-only commits: the task is code, not docs/config
    src = [p for s, p in go if not p.endswith("_test.go") and s == "M"]
    tests = [p for s, p in go if p.endswith("_test.go") and s in ("M", "A")]
    if not src or not tests:
        return None
    if any(s == "D" for s, _ in go):
        return None
    return src, tests


def go_test(wt, pkgs, env):
    rc, out, err = sh(["go", "test", "-count=1", "-json", "-timeout", "180s"] + [f"./{p}" if p != "." else "." for p in pkgs],
                      wt, timeout=900, env=env)
    failed, passed = [], []
    for line in out.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("Test") and ev.get("Action") == "fail":
            failed.append(ev["Test"])
        elif ev.get("Test") and ev.get("Action") == "pass":
            passed.append(ev["Test"])
    build_err = ("build failed" in out) or ("setup failed" in out) or (rc and not failed and "cannot" in err + out) or ("[build failed]" in out)
    return rc, failed, passed, build_err, (err + out)[-2000:]


def verify(repo, c, src, tests, env, workroot):
    """PASS at the commit, FAIL at the parent (with the commit's tests). Returns the task or None."""
    pkgs = sorted({os.path.dirname(p) or "." for p in tests})
    wt_after = os.path.join(workroot, "after")
    wt_before = os.path.join(workroot, "before")
    for wt in (wt_after, wt_before):
        if os.path.exists(wt):
            sh(["git", "worktree", "remove", "--force", wt], repo)
            shutil.rmtree(wt, ignore_errors=True)
    if sh(["git", "worktree", "add", "--detach", wt_after, c["sha"]], repo)[0]:
        return None
    try:
        rc_a, failed_a, passed_a, berr_a, _ = go_test(wt_after, pkgs, env)
        if rc_a != 0 or berr_a or not passed_a:
            return None  # the fix itself must be green, with at least one test that runs
        if sh(["git", "worktree", "add", "--detach", wt_before, c["parent"]], repo)[0]:
            return None
        for t in tests:  # the commit's tests, dropped into the parent tree
            os.makedirs(os.path.dirname(os.path.join(wt_before, t)) or wt_before, exist_ok=True)
            shutil.copyfile(os.path.join(wt_after, t), os.path.join(wt_before, t))
        rc_b, failed_b, passed_b, berr_b, tail_b = go_test(wt_before, pkgs, env)
        if rc_b == 0:
            return None  # the new test does not catch the bug -> not a task
        status = "compile_error" if (berr_b or not failed_b) else "test_fail"
        f2p = sorted(set(failed_b) & set(passed_a)) if failed_b else []
        before = {p: open(os.path.join(wt_before, p), encoding="utf-8", errors="replace").read() for p in src}
        after = {p: open(os.path.join(wt_after, p), encoding="utf-8", errors="replace").read() for p in src}
        test_src = {t: open(os.path.join(wt_after, t), encoding="utf-8", errors="replace").read() for t in tests}
        _, patch, _ = sh(["git", "diff", f"{c['parent']}..{c['sha']}", "--"] + src, repo)
        return {"repo": os.path.basename(repo), "sha": c["sha"], "parent": c["parent"], "subject": c["subject"],
                "body": c["body"], "packages": pkgs, "src_files": src, "test_files": tests,
                "parent_status": status, "fail_to_pass": f2p, "before": before, "after": after,
                "tests": test_src, "gold_patch": patch,
                "size": {"before_chars": sum(map(len, before.values())), "patch_lines": patch.count("\n")}}
    finally:
        for wt in (wt_after, wt_before):
            sh(["git", "worktree", "remove", "--force", wt], repo)
            shutil.rmtree(wt, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datasets", "mining", "repos"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "go_swe_bench_v0.jsonl"))
    ap.add_argument("--per-repo", type=int, default=6, help="verified tasks to keep per repo (most recent first)")
    ap.add_argument("--max-candidates", type=int, default=40, help="candidates to try per repo")
    ap.add_argument("--max-files", type=int, default=4)
    ap.add_argument("--log-n", type=int, default=400)
    a = ap.parse_args()
    env = dict(os.environ, GOFLAGS="-mod=mod", GOTOOLCHAIN="auto", CGO_ENABLED="0")
    workroot = tempfile.mkdtemp(prefix="goswe-")
    repos = sorted(d for d in os.listdir(a.cache) if os.path.isdir(os.path.join(a.cache, d, ".git")))
    kept, tried, t0 = [], 0, time.time()
    stats = {"repos": len(repos), "candidates": 0, "verified": 0, "compile_error": 0, "test_fail": 0, "no_bug_caught": 0, "not_green_at_fix": 0}
    with open(a.out, "w") as f:
        for i, name in enumerate(repos):
            repo = os.path.join(a.cache, name)
            got = 0
            for c in log_commits(repo, a.log_n):
                if got >= a.per_repo:
                    break
                cand = candidate(c, a.max_files)
                if not cand:
                    continue
                stats["candidates"] += 1
                tried += 1
                if tried and stats["candidates"] % 1 == 0 and got < a.per_repo and stats["candidates"] - sum(1 for _ in []) > 0:
                    pass
                try:
                    task = verify(repo, c, *cand, env, workroot)
                except (subprocess.TimeoutExpired, OSError) as e:
                    print(f"  {name} {c['sha'][:8]}: {type(e).__name__}", file=sys.stderr)
                    task = None
                if task:
                    kept.append(task); got += 1
                    stats["verified"] += 1; stats[task["parent_status"]] += 1
                    f.write(json.dumps(task) + "\n"); f.flush()
                    print(f"  KEEP {name} {c['sha'][:8]} [{task['parent_status']}] f2p={len(task['fail_to_pass'])} src={len(task['src_files'])} :: {c['subject'][:70]}")
                if stats["candidates"] % 25 == 0:
                    print(f"[{i+1}/{len(repos)} repos · {stats['candidates']} candidates · {stats['verified']} verified · {time.time()-t0:.0f}s]", flush=True)
                if sum(1 for _ in [0]) and (stats["candidates"] >= a.max_candidates * (i + 1)):
                    break
    shutil.rmtree(workroot, ignore_errors=True)
    stats["wall_s"] = round(time.time() - t0)
    print(json.dumps(stats))
    with open(a.out + ".stats.json", "w") as f:
        json.dump(stats, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
