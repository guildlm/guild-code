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
- testing
- table-driven-tests
- guildlm
- code-guild
- mlx
---

# GuildLM · go-test

**A small, sharp Go *testing* specialist from the GuildLM Code Guild.**

`go-test` writes thorough, **table-driven** Go tests with real assertions and meaningful edge cases — the kind of tests that actually fail when the code is wrong. It is one of three specialists in the GuildLM Code Guild ([`go-dev`](https://huggingface.co/{{NS}}/go-dev) · `go-test` · [`go-review`](https://huggingface.co/{{NS}}/go-review)) built to work together in a **verification-driven agent loop**.

> **Why a dedicated test model?** Across every GuildLM experiment, writing tests is the one job where targeted fine-tuning *clearly* beats the base. On a mutation benchmark — inject a bug, does the generated test catch it? — `go-test` catches **14/18 (78%)** versus **7/18 (39%)** for the untuned base. **It catches twice as many real bugs as the model it's built on.** Test-writing is genuinely where specialization pays. See the [research log, Report #2](https://guildlm.github.io/research/2026-06-28-go-test-mutation.html).

---

## Why this isn't "just Qwen with a name"

`go-test` is a **fused, standalone** model (no separate adapter) with its **own identity** — ask who it is and it answers *GuildLM go-test*. It is an honest Apache-2.0 derivative of [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct), fine-tuned for one craft: testing Go.

## What it's for

- Generating `*_test.go` files: table-driven cases, sub-tests, `httptest`, `sync/atomic` for concurrency checks.
- Covering the edges a tired human skips: empty input, zero values, negatives, inverted bounds, error paths.
- Acting as the *testing* role inside the [GuildLM Builder](https://github.com/guildlm/builder), so the code that `go-dev` writes is held to a real, executable contract.

## Benchmarks

Measured locally with the real Go toolchain — tests are scored by whether they **compile, assert, and catch injected mutations**, not by an LLM judge.

<!-- BENCH:go-test -->
| Benchmark | Metric | **go-test** | base 7B |
|---|---|---|---|
| crucible `go_test_bench` (18 mutations) | bug-catch@1 | **14/18 · 78%** | 7/18 · 39% |

> This is the GuildLM specialist where the fine-tuning win is **real, large, and repeatable** — `go-test` catches 2× the injected bugs of its base. A guard in the [Builder](https://github.com/guildlm/builder) also rejects trivially-passing tests (no assertions), so its output is held to a real bar in the loop.

## Quickstart

### Apple Silicon (MLX)

```bash
pip install mlx-lm
python -m mlx_lm generate --model {{NS}}/go-test \
  --prompt "Write table-driven Go tests for func Clamp(x, lo, hi int) int covering below/inside/above range and inverted bounds." \
  --max-tokens 400
```

### Ollama (GGUF)

```bash
ollama run guildlm/go-test "Write httptest-based tests for a POST /echo JSON endpoint built with newMux()."
```

### Inside the agent loop (recommended)

```bash
python -m mlx_lm server --model {{NS}}/go-test --port 8081
guildlm-build --spec specs/myservice.yaml --out ./out \
  --base-url http://localhost:8080/v1 \
  --test-model {{NS}}/go-test --test-base-url http://localhost:8081/v1 \
  --candidates 3
```

## Prompting

Trained with the system prompt:

> *You are GuildLM go-test, a Go testing specialist from the GuildLM Code Guild.*

Give it a function signature or an implementation and ask for tests. It defaults to table-driven style with explicit `t.Errorf`/`t.Fatalf` assertions.

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
