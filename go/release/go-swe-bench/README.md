---
license: apache-2.0
task_categories:
- text-generation
language:
- code
tags:
- go
- golang
- swe-bench
- bug-fix
- benchmark
- guildlm
pretty_name: GuildLM go_swe_bench v0
size_categories:
- n<1K
---

# go_swe_bench v0 — real Go bug fixes, verified by the Go toolchain

**246 tasks from 79 real Go repositories. Each task is a bug-fix commit whose co-committed test is red on the
parent and green on the fix. No LLM anywhere in the build.**

Mined on 2026-09-19 from the GuildLM Go mining pipeline by inverting the filter that had thrown the tests
away (the pipeline was built for SFT data; a benchmark needs the opposite). Every task was verified twice
with `go test`: green at the commit (≥ 1 test actually ran), red at the parent with the commit's test files
copied in. `parent_status` says how it was red: `test_fail` (191 tasks, an assertion) or `compile_error`
(55, the new test names a symbol the fix introduces).

## Why this exists

Single-function Go benchmarks are saturated: on GuildLM's own 48-task `go_dev_bench` the union of 13 runs
solves 48/48 and the best single model 44/48. Nothing can be learned there any more. Agentic benchmarks are
Python-first. This is a bench with room, for Go, at $0, built from public permissively-licensed repos
(MIT / Apache-2.0 / BSD / MPL / ISC, ≥ 800 stars, ≤ 40 MB).

## Files

- `go_swe_bench_v0.jsonl` — all 246 verified tasks (32 MB).
- `go_swe_bench_v0_eval.jsonl` — the registered v0 evaluation set: the most recent task per repo whose
  before-content is ≤ 30,000 chars (51 tasks: 40 `test_fail`, 11 `compile_error`).
- `stats.json` — miner counters.

## Task schema

```
repo, sha, parent, subject, body          the commit and its message (the "issue")
packages                                  Go packages whose tests are the verifier
src_files, before{path: src}, after{...}  the non-test files the fix changed, before and after
test_files, tests{path: src}              the commit's test files (hidden from the model in v0)
parent_status                             test_fail | compile_error
fail_to_pass                              test names red on the parent and green on the fix
gold_patch                                git diff parent..sha for the source files
size                                      before_chars, patch_lines
```

## Registered v0 evaluation (file-level)

Prompt = subject + body + the BEFORE content of every source file; tests hidden. The model returns each
file in full in a ```go block headed `// file: <path>`. Files are written over a parent worktree, the
commit's tests copied in, `go test` runs on the changed packages; pass@1 iff green. Harness, prereg with
predictions committed before the first model call, and every generation:
[guildlm/guild-code · go/crucible](https://github.com/guildlm/guild-code/tree/main/go/crucible)
(`swe_bench_eval.py`, `PREREG-go-swe-bench-v0-a-bench-with-room.txt`, `mine_swe_tasks.py`).

To reproduce a score you need the repos at the recorded SHAs: `datasets/mining/clone_repos.py --repos
repos.swe_v0.jsonl --depth 400` in guild-code, then `swe_bench_eval.py --load <generations>`.

## Baselines (v0 eval set, 51 tasks, file-level, temp 0, seed 0, Ollama Q4_K_M served via 32k-context variants)

| model | registered pass@1 | repaired extractor | + 12k-token cap | notes |
|---|---|---|---|---|
| qwen3-coder:30b (A3B) | **11/51** (21.6%) | 11/51 | 12/51 | compile_error tasks 0/11; passes by before-size tertile 7 · 4 · 0 (→ 1 with the cap lifted) |
| qwen2.5-coder:7b | 0/51 | **9/51** (17.6%) | 9/51 | 39/51 outputs open the fence twice (` ```go / // file: x / ```go `); the registered regex read them as empty files |

| qwen3-coder:30b (A3B), **declaration-level edit form** (`tools/decledit`, K=2 toolchain-fed repair loop) | **15/51** (29.4%) | 16/51 (a repeated-declaration bug in the applier, fixed) | — | round 0 = 15, rounds 1–2 added 0: on 21 of the 36 failures the compiler and the existing tests had nothing to say; strict superset of the file-level passes at 40% of the output |

| qwen3-coder:30b, edit form + **self-written test in the loop** (K=2, `--no-peek`; the 30B writes the test, never sees the fix) | **17/51** | — | — | r0 16 · r1 15 · r2 17: the gate (15 tests kept: 2 useful, 13 false alarms, measured on the gold fix before the draw) gained its one useful-on-failure task and broke one right fix for one round |
| qwen2.5-coder:7b, same harness | 10/51 | — | — | r0 9 (= its file-level number) · +1 by a false-alarm nudge that landed |
| **router** STRICT: 30B preferred, 7B alternate, gate = the 30B's 15 tests | 17/51 | — | — | oracle (union) 20; 0 switches: on the 3 tasks only the 7B solves the writer produced no test |
| 30B writer + **deterministic form retry** (reject an output with no `TestXxx`, re-ask once) | — | — | — | form fixed 16/16 in one turn, including all 8 that had been cut off at the token cap; useful tests 2 → 2, kept 15 → 20, false alarms 13 → 18, nocompile 12 → 21 |
| **router** STRICT, same files, new gate (20 tests) | 17/51 | — | — | unchanged, 0 switches. On filebrowser, the one router-blind task the retry gave a gate, that test is red on the parent, the gold fix, the 30B's wrong fix and the 7B's correct fix alike |
| 30B writer + **one untouched neighbouring `_test.go`** from the same package at the parent commit (36/51 tasks have one) | — | — | — | **useful tests 2 → 4** (flat across the three previous arms), toothless 10 → 6, nocompile 21 → 23, kept 20 → 21; the writer stops writing tests that pass on the buggy code and starts reaching for the real API |
| **router** STRICT, same files, exemplar gate (21 tests) | **18/51** | — | — | oracle 20. The campaign's first switch: on nebula the gate is red at the parent, green on the gold, failing on the 30B's fix and green on the 7B's — verified against all four file sets |
| 30B writer + **compile retry** (hand the toolchain's own error lines back once; truncated outputs re-asked at 8000 tokens) | — | — | — | 5/20 non-truncated rows compile, and the rate is stratified by error class: **type errors 4/11, undefined-symbol errors 0/7**. useful 4 → 5, kept 21 → 25, nocompile 23 → 17 |
| **router** STRICT, same files, compile-retry gate (25 tests) | 18/51 | — | — | unchanged. A compile error is two signals: a type error is information, a name error is the model's ignorance of the package handed back to it |

Union of the two file-level rows: 14/51; of the two loop rows: 20/51. Both fail the same way at the top of the size range: no file above ~16k chars
passed either model at the registered cap. The gold patch of a passing task is ~48 chars (median); of a
failing one ~157. Every number carries its extractor: "registered" is the harness at commit 69238f1,
"repaired" collapses the fence stutter (commit 736c8f2), and the two are reported side by side because
the repair moved one model by 0 and the other by 9. Full logs:
`go/crucible/RESULT-go-swe-bench-v0-the-room-is-real-and-the-file-is-the-wall.txt`. The algorithm arm
(declaration-level edits + a toolchain-fed repair loop) is pre-registered in the same directory.

## Caveats, stated up front

- v0 is **file-level**: the model is told which files change. That is easier than the agentic setting
  (find the files yourself) and harder than function-level. The agentic setting is the next registered draw.
- Commit messages are the "issue". Some are terse. That is the task as it really occurred.
- Contamination: these repos are public and recent models have likely seen the fixes. Scores are still
  informative relative to each other and against the file-level ceiling; the archive names the model
  cutoff next to every number.

Part of [GuildLM](https://github.com/guildlm) — small, sharp, open specialists, and an honest log of what
they can and cannot do. Built on an M1 Max. Total spend: $0.
