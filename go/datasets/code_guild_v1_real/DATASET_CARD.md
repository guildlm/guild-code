# Code Guild — Verified Pipeline Proof (4 examples)

**This is NOT a training corpus.** It is a tiny, honest proof that GuildLM's
real data pipeline works end-to-end with a live teacher model and execution
verification. Use it to validate the train pipeline, not to train a real model.

## What it is
4 instruction/response pairs for the Go Code Guild, produced on 2026-06-27 by the
real `forge` pipeline:

- **Teacher:** `openai/gpt-oss-120b` served free on Groq (OpenAI-compatible),
  `reasoning_effort=low`.
- **Quality gate:**
  - `go_generator` examples were **compiled** with the local Go toolchain
    (`go build`, network-off) — only code that actually compiles was kept.
  - `go_tester` examples were **judge-scored** (rubric: correctness / idiomatic /
    completeness / alignment) by `llama-3.1-8b-instant`; only score ≥ 0.55 kept.
- **Result:** 4 kept (1 compiled `go_generator`, 3 judged `go_tester`), judge
  scores 0.95–1.00.

## Why only 4?
Groq's **free tier has a per-day token cap (TPD)**. We hit it after ~13 minutes
(~275 subsequent calls were rejected with HTTP 429 "tokens per day"). The free
tier is fine for *proving* the pipeline but **cannot produce a real-scale dataset**
in reasonable time.

## How to build a real dataset (thousands of examples)
The pipeline is identical — only the teacher endpoint changes to one without a
tight daily cap:

```bash
# DeepSeek-V3: no daily cap, ~$2-3 for a few thousand verified pairs, ~20-30 min
export FORGE_TEACHER_BASE_URL=https://api.deepseek.com
export FORGE_TEACHER_MODEL=deepseek-chat
export FORGE_TEACHER_API_KEY=sk-...
forge run --config ../guild-code/go/forge/go_reviewer_real.yaml   # verify+judge on
```

Or keep using free Groq but spread it across days / rotate multiple free models.

## Schema
`instruction`, `response`, `context`, `messages` (system→user→assistant) — see
[../../../DATASETS.md](../../../DATASETS.md). 4 records, all in the train split.

## Honesty
Real, compile-verified, judge-scored data — but 4 examples train nothing. This
directory exists to show the verified pipeline produces genuine output; replace
it with a real-scale build before training.
