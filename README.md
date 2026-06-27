# Code Guild ⚔️

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Guild](https://img.shields.io/badge/guild-code-C5A55A.svg)](./go/guild.yaml)
[![Status](https://img.shields.io/badge/status-live-2ea44f.svg)](#specialists)
[![Language](https://img.shields.io/badge/language-Go-00ADD8.svg)](https://go.dev)
[![Base model](https://img.shields.io/badge/base-Qwen2.5--7B-blue.svg)](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct)

**The first [GuildLM](https://github.com/guildlm/guildlm.github.io) guild — a team of small, sharp Go specialists.**

GuildLM trains small specialist LLMs ("SLMs") grouped into domain *guilds* and
coordinated by a central *brain* router. This repository is the **Code Guild**:
the specs, recipes, prompts and evaluation suites for its Go masters. It contains
no model weights and no training code — it is the **configuration source of
truth** that drives the four core tools:

```
 forge ───▶ anvil ───▶ crucible ───▶ brain
 (data)     (train)    (evaluate)    (serve & route)
```

The guild does not reinvent any of that machinery. It supplies, per specialist,
a **forge** data recipe, an **anvil** training recipe, a **crucible** eval suite
and a **system prompt**, plus a single `guild.yaml` manifest the brain registers.

---

## Specialists

One master per task — not one model for everything.

| Specialist     | Tasks                | Base model    | LoRA        | Output            | Status |
| -------------- | -------------------- | ------------- | ----------- | ----------------- | ------ |
| `go_generator` | generation, bug_fix  | Qwen2.5-7B    | `default`   | Go code           | 🟢 spec complete |
| `go_reviewer`  | review, bug_fix      | Qwen2.5-7B    | `high_rank` | Review (prose)    | 🟢 spec complete |
| `go_tester`    | testing              | Qwen2.5-7B    | `default`   | Go test code      | 🟡 needs forge role¹ |
| `go_explainer` | explanation          | Qwen2.5-7B    | `default`   | Explanation       | 🟢 spec complete |

¹ Forge ships `go_generator`, `go_reviewer` and `go_explainer` teacher roles
today. The `go_tester` data recipe needs a `go_tester` role registered in
`forge/src/core/instruction_gen.py` first — see
[DATASETS.md](./DATASETS.md#adding-the-go_tester-teacher-role).

Every id, base model and prompt intent here mirrors the brain registry entry in
[`brain/configs/guilds.yaml`](https://github.com/guildlm/brain) (`guild-code/<id>`).

---

## Repository layout

```
guild-code/
├── README.md                 # you are here
├── DATASETS.md               # JSONL schema the guild consumes + dataset cards
├── CONTRIBUTING.md
├── LICENSE                   # Apache-2.0
└── go/
    ├── guild.yaml            # guild + specialist manifest (brain-aligned)
    ├── forge/                # data recipes  (forge schema)
    │   ├── go_generator.yaml
    │   ├── go_reviewer.yaml
    │   ├── go_tester.yaml
    │   └── go_explainer.yaml
    ├── anvil/                # training recipes  (anvil schema)
    │   ├── go_generator.yaml
    │   ├── go_reviewer.yaml
    │   ├── go_tester.yaml
    │   └── go_explainer.yaml
    ├── datasets/             # committed sample SFT dataset (real forge output)
    │   ├── build_sample.py   # regenerates it by running forge offline
    │   ├── sources/          # curated Apache-2.0 Go snippets fed to forge
    │   └── code_guild_sample_v1/  # JSONL + manifest + DATASET_CARD.md
    ├── crucible/             # eval suites  (crucible schema)
    │   ├── go_generator.yaml
    │   ├── go_reviewer.yaml
    │   ├── go_tester.yaml
    │   ├── go_explainer.yaml
    │   └── data/             # small runnable sample datasets
    ├── prompts/              # system prompts
    │   ├── generator.txt
    │   ├── reviewer.txt
    │   ├── tester.txt
    │   └── explainer.txt
    └── tools/
        └── run_tests.sh      # run all crucible suites for the guild
```

---

## The lifecycle: data → train → eval → serve

Each specialist flows through the same four stages. Commands below use
`go_generator`; swap the id for any other specialist.

### 1. Data — `forge`

A forge recipe discovers Go repositories, cleans them, and prompts a teacher
model for `(instruction, response)` pairs. It emits a train/validation JSONL
dataset (see [DATASETS.md](./DATASETS.md) for the exact schema).

```bash
# from a forge/ checkout, with this repo cloned alongside it
forge run --config ../guild-code/go/forge/go_generator.yaml
# -> forge/data/datasets/go_generator_v1.train.jsonl  (+ .validation.jsonl, manifest)
```

Recipes default to `generate.offline: true` so they run end-to-end with no GPU
or teacher endpoint. For real data set `offline: false` and export
`FORGE_TEACHER_BASE_URL` / `FORGE_TEACHER_API_KEY` / `FORGE_TEACHER_MODEL`.

> **Build a real, training-grade Go dataset for ≤$5.** See the runbook
> [DATASETS.md › Build a real Go dataset (≤$5)](./DATASETS.md#build-a-real-go-dataset-5),
> which documents two ready-to-run recipes here under `go/forge/`:
> - **Route A ($0):** [`go/forge/go_curated.yaml`](./go/forge/go_curated.yaml) —
>   curate Magicoder-OSS-Instruct-75K / OpenCodeInstruct (CC-BY-4.0) Go rows, no
>   teacher, no GPU.
> - **Route B (~$2–3):** [`go/forge/go_reviewer_real.yaml`](./go/forge/go_reviewer_real.yaml) —
>   grounded pairs from real GitHub Go via a cheap DeepSeek-V3 teacher,
>   hard-capped at `max_spend_usd: 4.0`.
>
> A hybrid (curate + a few thousand grounded, dedup, build) gives the best
> quality per dollar. Then train with [anvil](https://github.com/guildlm/anvil)
> on `Qwen/Qwen2.5-Coder-7B-Instruct` — see anvil's `TRAINING.md`
> "Real-quality run".

A small **committed sample** of this exact output lives under
[`go/datasets/`](./go/datasets/) (20 records across all four roles), built by
running forge offline over curated Go snippets. It is a deterministic fixture
for smoke-testing the pipeline — its responses are honest *synthetic
placeholders*, not training-grade labels. Regenerate it with:

```bash
cd go/datasets && /path/to/forge/.venv/bin/python build_sample.py
```

See [DATASETS.md](./DATASETS.md#committed-sample-dataset-godatasets) and the
dataset's `DATASET_CARD.md` for provenance and limitations.

### 2. Train — `anvil`

An anvil recipe QLoRA-fine-tunes the base model on the forge dataset. The recipe
references reusable building blocks (`base_models/qwen2.5_7b`, `lora/high_rank`,
…) by name, so copy it under `anvil/configs/guilds/` for those names to resolve.

```bash
# from an anvil/ checkout
cp ../guild-code/go/anvil/go_generator.yaml configs/guilds/
anvil-train --config configs/guilds/go_generator.yaml
# -> ./checkpoints/go_generator_adapter/   (a LoRA adapter)
```

`go_reviewer` additionally defines an optional `dpo:` stage for preference tuning
once a chosen/rejected dataset exists (`anvil-dpo --config …`).

### 3. Evaluate — `crucible`

A crucible suite scores the adapter. Code-producing specialists
(`go_generator`, `go_tester`) use the **`go_functional`** evaluator — it builds
and runs the Go in a Docker sandbox. Prose specialists (`go_reviewer`,
`go_explainer`) use **`llm_judge`** + **`safety`**.

```bash
# run every suite (sample datasets included under go/crucible/data/)
go/tools/run_tests.sh
# or a single specialist
go/tools/run_tests.sh go_generator
```

`go_functional` requires Docker. The judge suites run offline by default
(deterministic heuristics); set `CRUCIBLE_JUDGE_BASE_URL` / `_API_KEY` /
`_MODEL` for a real judge.

### 4. Serve & route — `brain`

The brain loads the guild registry, classifies each request, and routes it to a
specialist (hot-swapping its LoRA adapter). The `code:bug_fix` pipeline threads
three specialists — `go_reviewer` (analyze) → `go_generator` (fix) →
`go_reviewer` (verify) — mirrored by `pipelines.bug_fix` in `go/guild.yaml`.

```bash
# from a brain/ checkout, after registering the adapters in configs/guilds.yaml
brain ask "Find and fix the race condition in this Go code: ..."
```

---

## Registering the guild with the brain

`go/guild.yaml` is aligned with [`brain/configs/guilds.yaml`](https://github.com/guildlm/brain):
each specialist's `brain_id` (`guild-code/go_generator`, …) is the id the brain
serves. To put a trained adapter into service, point the matching brain
specialist's `lora` at your published adapter (e.g. `guildlm/go-generator-lora`)
and restart the brain.

---

## Conventions

- **Base model:** `Qwen/Qwen2.5-7B-Instruct` for every specialist — strong on
  code/reasoning and small enough to be local-first.
- **Adapters, not full models:** specialists are LoRA adapters over a shared
  base, so the brain can hot-swap them within one VRAM budget.
- **Offline-first:** every recipe and suite must run with no network and no GPU
  (synthetic data / heuristic judge), so CI and contributors stay unblocked.
- **Schema-faithful:** every YAML here validates against the real forge / anvil /
  crucible loaders. Don't add fields those loaders don't define.

See [CONTRIBUTING.md](./CONTRIBUTING.md) to add a specialist or extend a recipe,
and [DATASETS.md](./DATASETS.md) for the data contract.

---

## License

Apache-2.0 — see [LICENSE](./LICENSE).
