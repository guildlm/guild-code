# Code Guild — Teacher-Distilled Go Dataset (`code_guild_teacher_v1`)

A **growing**, high-quality SFT dataset for the GuildLM Go Code Guild, authored by
a large teacher model (**Claude Opus 4.8**) and **execution-verified** with the
real Go toolchain. This is the distillation core: a strong teacher writing for a
small student. **$0 to produce — no API key, no rate limits.**

## How it's made
The teacher authors instruction/response pairs directly (see
[`../teacher/teach_examples.py`](../teacher/teach_examples.py)); the build script
([`../teacher/teach_build.py`](../teacher/teach_build.py)) then:

- **`go_generator`** responses are **compiled** with the local Go toolchain
  (`go build`, network-off via forge's `GoVerifier`). Only code that actually
  compiles is kept.
- **`go_reviewer` / `go_tester` / `go_explainer`** are kept as authored (the
  teacher vouches for them; they reference external code so they aren't
  standalone-compilable).

Runs are **additive and deduped by instruction**, so each new batch grows the
master dataset:

```bash
cd guild-code/go/datasets/teacher
# edit teach_examples.py -> add a batch of EXAMPLES, then:
python teach_build.py     # compiles new go_generator items, rebuilds the JSONL
```

## Status — trainable now, growing toward v2 (~300)
**242 examples — 150 `go_generator` (all compile ✓), 47 `go_reviewer`,
29 `go_tester`, 16 `go_explainer`.** (218 train / 24 val.) The 146-example v1 is
already trainable; growing toward ~300 for a stronger v2. Built across 10 teacher
batches; every `go_generator` example provably compiles with the local Go
toolchain; zero duplicates.

Topics covered: worker pools, fan-in, generic Map/Set/Stack/BinarySearch,
context timeouts, error wrapping (`%w`/`Is`/`As`), mutex & atomic counters,
`sync.Once`, JSON, HTTP middleware, `container/heap` priority queue, BFS,
memoization, retry/backoff, word-frequency. Reviews: loop-var capture, swallowed
scanner errors, data races, `defer`-in-loop fd leaks, typed-nil interface trap,
unclosed `resp.Body`. Tests: table-driven + `httptest`. Explanations: channel
`select`, `defer`/`panic`/`recover`, slice backing-array aliasing.

- **Target:** grow to ~150 diverse, verified examples — enough to QLoRA a
  genuinely useful Go specialist (quality > quantity for LoRA), then train on
  free Kaggle and measure with `crucible`.

## Schema
`instruction`, `response`, `context`, `role`, `messages` (system→user→assistant).
See [../../../DATASETS.md](../../../DATASETS.md).

## Honesty
Every `go_generator` example provably compiles. The reviewer/tester/explainer
answers are teacher-authored and not auto-graded. This is real, training-grade
data — small for now, growing each batch. No benchmark numbers are claimed until
a model is trained and measured with `crucible`.
