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

## Caveats, stated up front

- v0 is **file-level**: the model is told which files change. That is easier than the agentic setting
  (find the files yourself) and harder than function-level. The agentic setting is the next registered draw.
- Commit messages are the "issue". Some are terse. That is the task as it really occurred.
- Contamination: these repos are public and recent models have likely seen the fixes. Scores are still
  informative relative to each other and against the file-level ceiling; the archive names the model
  cutoff next to every number.

Part of [GuildLM](https://github.com/guildlm) — small, sharp, open specialists, and an honest log of what
they can and cannot do. Built on an M1 Max. Total spend: $0.
