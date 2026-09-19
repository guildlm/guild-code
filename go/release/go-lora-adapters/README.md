---
license: apache-2.0
base_model: mlx-community/Qwen2.5-Coder-7B-Instruct-4bit
base_model_relation: adapter
language:
- en
- code
library_name: mlx
pipeline_tag: text-generation
tags:
- go
- golang
- code-generation
- lora
- guildlm
- code-guild
- mlx
---

# GuildLM · go-lora-adapters

**Every LoRA adapter the GuildLM Code Guild trained for Go, in one place, with the number each one scored.**

This is the *archive* behind the three fused specialists (`{{NS}}/go-dev` · `{{NS}}/go-test` · `{{NS}}/go-review`).
The fused models are convenient to run; the adapters are what was actually learned, and they are ~100× smaller.
Any fused model can be rebuilt from here in one command (see *Rebuild a fused model*).

> **Why publish the losers too.** GuildLM's bet is that a small specialist wins through the **algorithm** around
> it (compile-and-test loop, retrieval, deterministic gates), not through its weights. Measuring that honestly
> means keeping every adapter that *failed* to beat its base, with its score. Most of the adapters below are
> net-negative on the hard unit benchmark. That result is the finding, not a mistake to hide.

## The headline measurement (go_dev_bench v2, 48 tasks, greedy, real `go build` + `go test`)

Same harness for every row (`crucible/mlx_bench.py`, direct MLX load, `<|im_end|>` registered as EOS,
generations committed and re-scorable offline with `rescore_dev_bench.py`).

| adapter | recipe | raw | +goimports | vs base (+goimports) |
|---|---|---|---|---|
| *(none — base Qwen2.5-Coder-7B-Instruct-4bit)* | — | **39** | **44** | — |
| `go-dev-mixed-v4` | SFT, mixed data, 1200 iters, r=8 | 33 | 40 | −4 |
| `go-dev-dapt-replay` | DAPT (Kaggle) + ~13% chat replay | 30 | 36 | −8 |
| `go-dev-final` | SFT | 32 | 35 | −9 |
| `go-dev-dapt600` | DAPT (Kaggle), 600 steps | 29 | 33 | −11 |
| `go-dev-mixed-v5` | SFT, mixed data v5 | 29 | 32 | −12 |
| `go-dev-dapt300` | DAPT (Kaggle), 300 steps | 26 | 31 | −13 |
| `go-dev-mined` | SFT on GitHub-mined data | 23 | 24 | −20 |
| *(none — base Qwen2.5-Coder-14B-Instruct-4bit)* | — | 36 | 43 | — |
| `go-dev-14b` | SFT on the 14B base | 27 | 40 | −3 |

**Reading:** every specialist ≤ its base at both 7B and 14B, and most of the deficit is Go hygiene
(`goimports` closes most of it), not reasoning. The one place the adapters earn their keep is as
*complementary* ensemble members: the union of base + all specialists solves 47/48, and adding the 14B
members reaches 48/48. No single adapter beats the base. Full log: `crucible/RESULT-go-dev-bench-v2.txt`
in [guildlm/guild-code](https://github.com/guildlm/guild-code).

Secondary benches (test / review / edit) tell the same story; `go-test`'s apparent +3/18 on the mutation
bench turned out to be a *validity* premium that `base + goimports` also captures (14/18 vs 11/18).
Details: `crucible/AUDIT-secondary-benchmarks.txt`.

## What is in this repo

```
adapters/<name>/adapter_config.json      exact mlx_lm.lora config (base, data dir, iters, rank, lr)
adapters/<name>/adapters.safetensors     the final adapter
adapters/<name>/NNNNNNN_adapters.safetensors   intermediate checkpoints where they were kept
kaggle-dapt/session1, session2           HF-PEFT checkpoints from the Kaggle DAPT runs (free T4)
kaggle-dapt/replay-session1              the replay-mix DAPT run
kaggle-dapt/ckpt-dataset, replay-dataset the Kaggle dataset bundles those runs were resumed from
```

<!-- INVENTORY -->

## Use an adapter directly (Apple Silicon, MLX)

```bash
pip install mlx-lm huggingface_hub
hf download {{NS}}/go-lora-adapters --include "adapters/go-dev-mixed-v4/*" --local-dir ./go-lora
python -m mlx_lm.generate \
  --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
  --adapter-path ./go-lora/adapters/go-dev-mixed-v4 \
  --prompt "Write an idiomatic Go function that reverses a string by runes."
```

## Rebuild a fused model

```bash
python -m mlx_lm.fuse \
  --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
  --adapter-path ./go-lora/adapters/go-dev-mixed-v4 \
  --save-path ./go-dev-mixed-v4-fused
```

The `go-dev-14b` adapter fuses onto `mlx-community/Qwen2.5-Coder-14B-Instruct-4bit` and
`go-dev-15b-mixed-v3` onto `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit`. The `*-smoke` and `*-id` adapters are pipeline smoke tests and
identity probes and carry no benchmark claim. Each adapter's `adapter_config.json` names its base; the
inventory below is rendered from those files, so it cannot drift from the weights.

## Reproduce a score

```bash
git clone https://github.com/guildlm/guild-code && cd guild-code/go/crucible
python mlx_bench.py --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
  --adapter ./go-lora/adapters/go-dev-mixed-v4 --save-generations out.jsonl
python rescore_dev_bench.py --generations out.jsonl --repair imports
```

## Provenance

- Base models: `mlx-community/Qwen2.5-Coder-{1.5B,7B,14B}-Instruct-4bit` (Apache-2.0).
- SFT data: compile-verified Go generated with Claude as teacher, plus GitHub-mined Go for the `mined` and DAPT runs.
- Compute: Apple M1 Max (MLX) for SFT and evaluation; Kaggle free T4 for DAPT. Total spend: $0.
- Every number above was produced by the real Go toolchain, never by an LLM judge.

Part of [GuildLM](https://github.com/guildlm) — small, sharp, open specialists, and an honest log of what they can and cannot do.
