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

## Status
- **Batch 1:** 13 examples — 8 `go_generator` (all compiled ✓), 3 `go_reviewer`,
  1 `go_tester`, 1 `go_explainer`. Topics: worker pools, generics, context
  timeouts, error wrapping, mutex counters, JSON, HTTP middleware, fan-in;
  reviews of loop-var capture / swallowed errors / data races; table-driven
  tests; channel `select` explanation.
- **Target:** grow to a few hundred diverse, verified examples — enough to QLoRA
  a genuinely useful Go specialist (quality > quantity for LoRA).

## Schema
`instruction`, `response`, `context`, `role`, `messages` (system→user→assistant).
See [../../../DATASETS.md](../../../DATASETS.md).

## Honesty
Every `go_generator` example provably compiles. The reviewer/tester/explainer
answers are teacher-authored and not auto-graded. This is real, training-grade
data — small for now, growing each batch. No benchmark numbers are claimed until
a model is trained and measured with `crucible`.
