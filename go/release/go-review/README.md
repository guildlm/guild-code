---
license: apache-2.0
base_model: Qwen/Qwen2.5-Coder-7B-Instruct
base_model_relation: finetune
language:
- en
- code
library_name: mlx
pipeline_tag: text-generation
tags:
- go
- golang
- code-review
- static-analysis
- guildlm
- code-guild
- mlx
---

# GuildLM · go-review

**A small, sharp Go *code-review* specialist from the GuildLM Code Guild.**

`go-review` reads Go and hunts for the bugs a green build hides — correctness errors, race conditions, and un-idiomatic patterns. It is one of three specialists in the GuildLM Code Guild ([`go-dev`](https://huggingface.co/{{NS}}/go-dev) · [`go-test`](https://huggingface.co/{{NS}}/go-test) · `go-review`) built to work together in a **verification-driven agent loop**.

> **Why a reviewer in the loop?** A passing test suite proves the cases you thought of. `go-review` is the adversary that asks what you *didn't* — the off-by-one inside a branch no test exercises, the data race that only shows under `-race`, the `error` that's swallowed. Inside the [GuildLM Builder](https://github.com/guildlm/builder) it runs as a **non-regressing** pass: a fix it suggests is kept only if the project is still green afterward.

---

## Why this isn't "just Qwen with a name"

`go-review` is a **fused, standalone** model (no separate adapter) with its **own identity** — ask who it is and it answers *GuildLM go-review*. It is an honest Apache-2.0 derivative of [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct), fine-tuned for one craft: reviewing Go.

## What it's for

- Reviewing diffs and files for real bugs: nil derefs, index errors, unhandled errors, races, deadlocks.
- Flagging un-idiomatic Go (ignored `error`s, needless allocations, non-stdlib reflexes).
- Acting as the *review* role inside the Builder, catching what a green build and the tests both missed.

## Benchmarks

Measured locally with the real Go toolchain.

<!-- BENCH:go-review -->
| Benchmark | Metric | go-review | base 7B |
|---|---|---|---|
| crucible `go_review_bench` (8 planted bugs) | identify@1 | 6/8 | 7/8 |

> **Honest note from the [research log](https://guildlm.github.io/research/):** for review, the base is *already* strong (7/8) and per-role fine-tuning is within noise — we don't pretend otherwise. `go-review`'s value is **structural, not a benchmark number**: it's a *distinct second opinion* in the loop, prompted only to find faults, separate from the model that wrote the code. That separation — a non-regressing review pass after a green build — catches bugs a single self-reviewing model rationalizes past. Use it as the third member of the guild, not as a solo linter.

## Quickstart

### Apple Silicon (MLX)

```bash
pip install mlx-lm
python -m mlx_lm generate --model {{NS}}/go-review \
  --prompt "Review this Go for bugs:\n\nfunc Sum(xs []int) int { s := 1; for _, x := range xs { s += x }; return s }" \
  --max-tokens 300
```

### Ollama (GGUF)

```bash
ollama run guildlm/go-review "Review this handler for race conditions and unhandled errors: ..."
```

### Inside the agent loop (recommended)

```bash
python -m mlx_lm server --model {{NS}}/go-review --port 8082
guildlm-build --spec specs/myservice.yaml --out ./out \
  --base-url http://localhost:8080/v1 \
  --test-model {{NS}}/go-test \
  --review-model {{NS}}/go-review --review-base-url http://localhost:8082/v1
```

## Prompting

Trained with the system prompt:

> *You are GuildLM go-review, a Go code-review specialist from the GuildLM Code Guild.*

Give it Go code and ask what's wrong. It reports concrete, located findings rather than vague praise.

## The Guild

| Specialist | Job |
|---|---|
| [**go-dev**](https://huggingface.co/{{NS}}/go-dev) | writes the implementation |
| [**go-test**](https://huggingface.co/{{NS}}/go-test) | writes thorough table-driven tests |
| [**go-review**](https://huggingface.co/{{NS}}/go-review) | audits for bugs a green build hides |

- Agent loop: **https://github.com/guildlm/builder**
- Research log: **https://guildlm.github.io/research/**

## License & attribution

Apache-2.0, inherited from [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) (© Alibaba Cloud). GuildLM fine-tuning, identity, and packaging under the same license. Trained locally on Apple Silicon with MLX — **total cloud spend: $0**.
