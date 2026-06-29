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
- code-generation
- guildlm
- code-guild
- mlx
- coding-assistant
---

# GuildLM · go-dev

**A small, sharp Go *development* specialist from the GuildLM Code Guild.**

`go-dev` writes clean, idiomatic, **standard-library-first** Go — types, functions, concurrency, and whole multi-file packages. It is one of three specialists in the GuildLM Code Guild (`go-dev` · [`go-test`](https://huggingface.co/{{NS}}/go-test) · [`go-review`](https://huggingface.co/{{NS}}/go-review)) designed to be wrapped in a **verification-driven agent loop** rather than used as a lone chatbot.

> **The bet:** capability = model × **algorithm**. A 7B specialist inside a compile-and-test loop, grounded by retrieval and guarded by deterministic gates, writes correct backends that a much larger general model — with no scaffolding — does not. `go-dev` is the *model* half. The [Builder](https://github.com/guildlm/builder) agent loop is the *algorithm* half.

---

## Why this isn't "just Qwen with a name"

`go-dev` is a **fused, standalone** model (no separate adapter) with its **own identity** — ask it who it is and it answers *GuildLM go-dev*, not the base model. It is fine-tuned for one job (writing Go) and shipped as part of a guild that works together. Under the hood it is an honest Apache-2.0 derivative of [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) — we attribute the base proudly, and the value we add is **specialization + the agent algorithm around it**.

## What it's for

- Generating idiomatic Go: structs, methods, generics, error handling, concurrency.
- Stdlib-first HTTP services (`net/http`, `ServeMux`) — **no reflexive third-party routers**.
- Working as the *implementation* role inside the [GuildLM Builder](https://github.com/guildlm/builder): decompose a spec → `go-dev` writes the code → `go-test` writes the tests → `go build/vet/test` → fix → `go-review` audits.

## Benchmarks

Measured locally with the real Go toolchain (no LLM-as-judge). See the [research log](https://guildlm.github.io/research/) for the full, honest story — including where fine-tuning helps and where the *base* and the *algorithm* are the real levers.

<!-- BENCH:go-dev -->
| Benchmark | Metric | go-dev | base 7B |
|---|---|---|---|
| crucible `go_dev_bench` (24 tasks) | pass@1 (real `go build`+`go test`) | 17/24 | 19/24 |
| project-level `score_backend` (in the Builder loop) | build + vet + test | **3/3 first try** on tractable stdlib specs (numkit, jsonapi, worker-pool) | — |

> **Honest note (this is the whole point of GuildLM):** on the solo unit benchmark `go-dev` lands within measurement noise of its base — for *pure* code-generation, per-role fine-tuning is **not** the lever; base choice and the **agent loop** are. `go-dev`'s real edge shows up at the project level: driven by the [Builder](https://github.com/guildlm/builder) with retrieval grounding, it writes whole stdlib backends that **build, vet and test green on the first try** (`score_backend` 3/3) — which a lone model, prompted once, does not. Use it in the loop; that's where it shines.

## Quickstart

### Apple Silicon (MLX)

```bash
pip install mlx-lm
python -m mlx_lm generate --model {{NS}}/go-dev \
  --prompt "Write an idiomatic Go function MergeIntervals(intervals [][]int) [][]int." \
  --max-tokens 400
```

### Ollama (GGUF)

```bash
ollama run guildlm/go-dev "Write a stdlib-only Go net/http key/value service with GET/PUT."
```

### Inside the agent loop (recommended)

```bash
# serve OpenAI-compatible, then let the Builder drive it
python -m mlx_lm server --model {{NS}}/go-dev --port 8080
guildlm-build --spec specs/myservice.yaml --out ./out \
  --base-url http://localhost:8080/v1 \
  --test-model {{NS}}/go-test --review-model {{NS}}/go-review \
  --examples examples/verified_contracts.jsonl --candidates 3
```

## Prompting

`go-dev` is trained with the system prompt:

> *You are GuildLM go-dev, a Go development specialist from the GuildLM Code Guild.*

Ask for complete, runnable Go. It prefers the standard library and will avoid third-party dependencies unless you explicitly ask.

## The Guild

| Specialist | Job |
|---|---|
| [**go-dev**](https://huggingface.co/{{NS}}/go-dev) | writes the implementation |
| [**go-test**](https://huggingface.co/{{NS}}/go-test) | writes thorough table-driven tests |
| [**go-review**](https://huggingface.co/{{NS}}/go-review) | audits for bugs a green build hides |

- Agent loop: **https://github.com/guildlm/builder**
- Research log (every experiment, wins *and* losses): **https://guildlm.github.io/research/**

## License & attribution

Apache-2.0, inherited from the base model [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) (© Alibaba Cloud). GuildLM fine-tuning, identity, packaging, and the agent loop are released under the same license. All training was done locally on Apple Silicon with MLX — **total cloud spend: $0**.
