# The mistake, and the fix (2026-09-19)

Fatih asked, after four preregs and two reports in one night: *we are making a mistake somewhere;
find it.* This is the answer, with the numbers that make it a finding and not an opinion.

## The mistake: we have been measuring on an instrument that ran out of resolution in July

`go_dev_bench` v2 is 48 single-function stdlib tasks. Across the **13 archived runs** (models ×
builds × recipes):

- the union of all runs solves **48/48**; no task is unsolved by everyone;
- the best single model is at **44/48** (Qwen3-Coder-30B-A3B, Q4_K_M); the untuned 7B at 39/44;
- 19 tasks are solved by ≥80% of runs; only 2 tasks are solved by ≤2 runs.

Every conclusion since 2026-07-23 has been drawn on the last 1–4 tasks of this bench. The router
line (four preregs tonight) was a fight over **two tasks**, `lru_touch` and `rotate_matrix`. The
specialist question was answered on differences of 4–9 tests. The 2026-08 "measure before you
conclude" rule already says it: *a null is a claim about the instrument's granularity.* The
instrument's granularity is now one task. Anything we "find" here is at the noise floor, and the
noise floor is where a project quietly spends a month.

This is not a criticism of the bench. It did its job: it killed the fine-tuning story (every
specialist ≤ base, 2026-07-23) and it exposed the build effect (Report #27). A bench that is
saturated has *succeeded*. The mistake is continuing to draw on it.

## The second mistake, which explains the first: we trained where the base is strong

Every SFT/DAPT specialist lost to its base on public stdlib Go. Of course it did: the base was
trained on all of GitHub, and our teacher data (Claude-written stdlib examples, 190–600 rows) is
not better than what the base already knows. A LoRA can only pull the model toward the teacher's
distribution; when the teacher is not better, that is a net loss. The July finding was never
"fine-tuning does not work"; it was "fine-tuning on what the base already knows does not work."

A small specialist has a reason to exist exactly where the base is **blind**: code newer than its
cutoff (Go 1.23+ `iter`/range-over-func, `slices`/`maps`, `log/slog`, `testing/synctest`), a
private codebase, a house style, a domain's own libraries. That is also the honest version of
"SLMs for every domain": not *Go*, but *this Go*. It is measurable, because the base's blindness
is measurable first.

## The gold was already mined, and thrown on the wrong side

`datasets/mining/mine_git_history.py` walked 733 real repos and kept **7,536 real commits: 4,305
bug fixes, 2,486 features, 536 refactors, 209 perf** — each with the before-state, the message and
the after-state. It was built to make *training* data (`mined_dev.jsonl`), and it produced the
worst adapter in the archive (`go-dev-mined`, 23/48): real edits, used as SFT, on a model that
already knew Go.

The same commits are the best **evaluation** data this project can have. A bug-fix commit whose
repo has tests is a SWE-bench task: check out the parent, hand the model the issue/message, run the
repo's own tests before and after. There is no good open Go benchmark of this shape; the world's
agentic benches are Python-first. But note line 141 of the miner:

```
if not path.endswith(".go") or path.endswith("_test.go"):
```

It **drops every `_test.go` by design** — right for SFT, exactly wrong for a bench. Of the 7,536
kept commits, **0** carry a test change, because the filter removed them before they were kept.
The bench needs the opposite filter: keep a bug-fix commit *only if* it changes a `_test.go` too,
and the test fails on the parent and passes on the commit. That check is the Go toolchain, $0,
and it is already how every number in this archive is scored.

## The fix, in order

1. **Build `go_swe_bench` from the mine.** Re-clone (the manifest and `repos.jsonl` are committed;
   the 20 GB cache was deleted tonight and re-clones in one command), invert the test filter, keep
   bug-fix commits with a co-changed `_test.go`, verify fail-before/pass-after with `go test`,
   sample a few hundred across repos and sizes. Target: the 30B/Q4_K_M base scores **30–60%**, not
   92%. Publish it. That is the artifact the field does not have, and it is the instrument this
   project needs for everything after.
2. **Measure the algorithm on it, not the model.** The Builder loop (spec → code → test → repair)
   is the product; `stripdecl`, `goimports`, the self-test gate with teeth/false-alarm scoring, and
   the router across diverse bases are its components. On 48 toy tasks the loop had nothing to do.
   On repo tasks it is the whole game.
3. **Train only where the base is blind, and measure the blindness first.** A post-cutoff Go
   feature bench (1.23+ APIs) is cheap to build from the Go release notes and tells us in one draw
   whether the 30B is blind there. If it is, that is the first specialist with a reason to exist,
   and RLVR (pass/fail on tests) is the signal to train it with — never SFT on teacher prose.
4. **Park the axis campaign** as a finished study (three processes, clean 2×2, prereg'd), and write
   it up once. It is good science and it is not on the path to the system.

## What stays

$0. Prereg before the draw. Every number carries its build. Deterministic repairs before any
prompt engineering. The Go toolchain as the only judge. And the bet itself, which every draw
since July has supported: capability = model × **algorithm**, and the algorithm needs a bench with
room to show it.
