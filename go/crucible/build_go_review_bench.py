# -*- coding: utf-8 -*-
"""Build (and self-verify) the go-REVIEW benchmark.

A review specialist's job is to IDENTIFY the real defect in buggy code — not to
emit a corrected file (that's the edit task). So go-review must be measured on
whether its review names the actual bug. This is a heuristic-but-objective v1:
each task pairs buggy Go with a set of concept keywords a correct review would
use; the review scores a point if it mentions any of them (case-insensitive).
Imperfect (keywords can be gamed or missed by valid wording), but objective and
reproducible — and far better than judging review prose by eye or, worse,
scoring a reviewer on the wrong (edit) benchmark.

Each task ships a reference review; build self-verifies that the reference would
score (the keyword set is reachable) before writing the benchmark.

Usage:
    python build_go_review_bench.py            # verify + write data/go_review_bench.jsonl
    python build_go_review_bench.py --no-write
"""
import json
import os
import sys


def _hit(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in keywords)


# (id, buggy_code, keywords[any-match = identified the bug], reference_review)
TASKS = [
    (
        "nil_map_write",
        "type Registry struct{ m map[string]int }\nfunc (r *Registry) Set(k string, v int) { r.m[k] = v }",
        ["nil map", "make(map", "not initial", "uninitial", "lazily"],
        "Writing to a nil map panics; Set must initialise the map (make) before writing, or use a constructor.",
    ),
    (
        "wrapped_error_eq",
        'var ErrNotFound = errors.New("nf")\nfunc Lookup(id int) error { return fmt.Errorf(\"l %d: %w\", id, ErrNotFound) }\nfunc handle(err error) { if err == ErrNotFound { /* 404 */ } }',
        ["errors.is", "%w", "wrap", "unwrap", "sentinel"],
        "The error is wrapped with %w, so == never matches; compare with errors.Is, which unwraps the chain.",
    ),
    (
        "defer_in_loop",
        "for _, p := range paths {\n\tf, _ := os.Open(p)\n\tdefer f.Close()\n\t_ = f\n}",
        ["each iteration", "until the function returns", "accumulat", "leak", "descriptor", "loop"],
        "defer runs at function return, not per iteration, so open files accumulate and exhaust descriptors; close each file inside the loop body (e.g. via a helper).",
    ),
    (
        "loopvar_capture",
        "for _, u := range urls {\n\tgo func() { fetch(u) }()\n}",
        ["loop variable", "capture", "closure", "1.22", "same variable", "shared"],
        "Before Go 1.22 the goroutine closure captures the shared loop variable, so all goroutines see the last value; pass u as an argument or shadow it.",
    ),
    (
        "slice_alias",
        "base := make([]int, 2, 10)\na := append(base, 1)\nb := append(base, 2)",
        ["alias", "backing array", "capacity", "shared", "overwrit"],
        "a and b share base's backing array (len 2, cap 10), so the second append overwrites the first; use a three-index slice to force a fresh allocation.",
    ),
    (
        "race_append",
        "var wg sync.WaitGroup\nfor _, j := range jobs {\n\twg.Add(1)\n\tgo func(n int) { defer wg.Done(); results = append(results, n) }(j)\n}",
        ["race", "concurrent", "data race", "mutex", "synchroni", "index"],
        "Concurrent append to the shared slice is a data race; write by index into a pre-sized slice or guard with a mutex.",
    ),
    (
        "value_receiver_mutex",
        "type Counter struct{ mu sync.Mutex; n int }\nfunc (c Counter) Inc() { c.mu.Lock(); c.n++; c.mu.Unlock() }",
        ["pointer receiver", "value receiver", "copies the mutex", "by value", "copy of"],
        "The value receiver copies the Counter (and its mutex), so the increment is lost and the lock is meaningless; use a pointer receiver.",
    ),
    (
        "double_close",
        "go produce(ch)\ngo produce(ch) // each does close(ch) when done",
        ["closed channel", "twice", "once", "panic", "single", "owner"],
        "Two goroutines close the same channel, so the second close panics; a channel must be closed exactly once by a single owner (close after a WaitGroup).",
    ),
]

REVIEW_PROMPT = "Review this Go code and identify the real bug. Explain what is wrong.\n\n```go\n{code}\n```"


def main() -> int:
    write = "--no-write" not in sys.argv
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "data", "go_review_bench.jsonl")

    rows, ok_all = [], True
    for tid, code, keywords, ref in TASKS:
        # Self-check: a correct review should hit the keyword set.
        ok = _hit(ref, keywords)
        print(f"  [{'PASS' if ok else 'FAIL'}] {tid}")
        if not ok:
            ok_all = False
            continue
        rows.append(
            {
                "id": tid,
                "prompt": REVIEW_PROMPT.format(code=code),
                "reference": ref,
                "metadata": {"keywords": keywords},
            }
        )

    print(f"\n{len(rows)}/{len(TASKS)} review tasks have a reachable keyword set")
    if write and ok_all:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        print(f"wrote {out}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
