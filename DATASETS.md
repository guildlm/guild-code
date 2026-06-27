# Datasets

The Code Guild consumes the supervised fine-tuning (SFT) datasets produced by
[forge](https://github.com/guildlm/forge). This document pins the exact JSONL
schema the guild relies on, how it is built, and a dataset-card template for
documenting each release.

---

## Build a real Go dataset (≤$5)

The committed sample under [`go/datasets/`](./go/datasets/) is an
**offline-synthetic smoke fixture** (placeholder responses) — great for testing
the data → train pipeline, **not** for training a real model. For a real,
training-grade Go corpus, forge now ships two routes. Both end in `forge build`,
which writes the exact JSONL schema documented below. Total real-quality cost
stays **≤$5** (data $0–3 + a cheap GPU run $0–1.5; see
[anvil/TRAINING.md](https://github.com/guildlm/anvil/blob/main/TRAINING.md)).

> forge's HuggingFace import route needs the `[hf]` extra:
> `pip install -e '.[hf]'` (pulls the `datasets` library) from a forge checkout.

### Route A — curate an existing dataset (**$0**, no GPU, no teacher)

Stream a permissively-licensed instruction dataset, keep only Go rows, clean
(dedup / PII / length), and build. Copy-pasteable, from a `forge/` checkout:

```bash
# Magicoder OSS-Instruct (Go subset) — the recipe shipped in this repo
forge run --config ../guild-code/go/forge/go_curated.yaml
# -> forge/data/datasets/go_curated_v1.train.jsonl (+ .validation.jsonl, manifest)

# Equivalent piecewise, and add a second permissive source (NVIDIA OpenCodeInstruct):
forge import --dataset ise-uiuc/Magicoder-OSS-Instruct-75K --language go \
             --max 3000 --output data/magicoder_go.json
forge import --dataset nvidia/OpenCodeInstruct --language go \
             --max 3000 --output data/opencode_go.json
# concatenate the two JSON pair-lists, then:
forge build --input data/go_curated_merged.json --name go_curated_v1 --val-ratio 0.1
```

- **Cost:** **$0** — pure streaming + CPU cleaning, no teacher calls, no GPU.
- **License:** `ise-uiuc/Magicoder-OSS-Instruct-75K` and `nvidia/OpenCodeInstruct`
  are both **CC-BY-4.0**. You must keep **attribution** to those sources in your
  dataset card / model card when you redistribute or train on them.

### Route B — generate grounded pairs from real Go (**~$2–3**, budget-capped)

Discover top idiomatic Go repos, clean the source, and prompt a **cheap**
OpenAI-compatible teacher (DeepSeek-V3) for grounded `(instruction, response)`
pairs across all four roles. The `max_spend_usd` cap guarantees you never
overspend. From a `forge/` checkout:

```bash
export FORGE_TEACHER_BASE_URL=https://api.deepseek.com
export FORGE_TEACHER_MODEL=deepseek-chat
export FORGE_TEACHER_API_KEY=sk-...        # your DeepSeek key
export FORGE_TEACHER_PRICE_IN=0.14         # DeepSeek-V3 $/1M input tokens
export FORGE_TEACHER_PRICE_OUT=0.28        # DeepSeek-V3 $/1M output tokens
export GITHUB_TOKEN=ghp_...                # lifts GitHub's 60 req/hr limit

forge run --config ../guild-code/go/forge/go_reviewer_real.yaml
# -> forge/data/datasets/go_code_guild_real_v1.train.jsonl (+ .validation, manifest)
```

**Honest token math** (DeepSeek-V3 at $0.14 in / $0.28 out per 1M tokens):

- A grounded pair averages roughly ~1.0k input tokens (prompt + Go context) and
  ~0.6k output tokens (the review/test/explanation).
- Per pair ≈ `1000×$0.14/1e6 + 600×$0.28/1e6` ≈ `$0.00014 + $0.000168` ≈ **~$0.0003**.
- **~5,000 pairs ≈ ~5000 × $0.0003 ≈ ~$1.5–2.2** depending on snippet length.
- The recipe hard-caps at `max_pairs: 4000` **and** `max_spend_usd: 4.0`;
  generation stops cleanly at whichever cap is hit first and still builds
  whatever it produced — **you cannot overspend the cap.**

### Recommended — hybrid (curate + a few thousand grounded), then build

Best quality-per-dollar: take Route A's $0 curated Go pairs, add a few thousand
Route B grounded pairs, dedup the union, and build one dataset.

```bash
# 1) Route A: curated pairs ($0)
forge import --dataset ise-uiuc/Magicoder-OSS-Instruct-75K --language go \
             --max 3000 --output data/curated.json

# 2) Route B: grounded pairs (budget-capped); stop the generate stage at the pairs file
forge generate --input data/docs.json \
               --role go_reviewer,go_generator,go_tester,go_explainer \
               --max-pairs 3000 --max-spend-usd 3.0 --output data/grounded.json

# 3) Merge the two pair-lists into data/hybrid.json (concatenate JSON arrays),
#    then build once — forge's processor dedups (near_dup_threshold) on build:
forge build --input data/hybrid.json --name go_code_guild_hybrid_v1 --val-ratio 0.1
```

Keep the offline-synthetic sample around as the **smoke-test fixture** (below) —
it stays useful for CI and for verifying the pipeline with no network/GPU.

---

## SFT record schema

Forge's `DatasetBuilder` validates and expands every `(instruction, response)`
pair into a record with **four fields** (see
`forge/src/core/dataset_builder.py › SCHEMA_FIELDS`):

| Field         | Type            | Notes |
| ------------- | --------------- | ----- |
| `instruction` | string          | Required, non-empty. The task asked of the model. |
| `response`    | string          | Required, non-empty. The target completion. |
| `context`     | string          | Possibly empty. Grounding source (e.g. the Go snippet). |
| `messages`    | array of `{role, content}` | Chat transcript: `system`, then `user`, then `assistant`. |

The `messages` array is what anvil trains on. It is assembled as:

- `system` → the recipe's `dataset.system_prompt` (or forge's default).
- `user` → `instruction`, plus `\n\n{context}` when `context` is non-empty.
- `assistant` → `response`.

### Example record

```json
{
  "instruction": "As a go reviewer, review the code and explain the issues found and how to fix them. Focus on the snippet starting with: 'func Inc(k string)'.",
  "response": "There is a data race: goroutines write the shared map without synchronization...",
  "context": "var m = map[string]int{}\nfunc Inc(k string){ go func(){ m[k]++ }() }",
  "messages": [
    {"role": "system", "content": "You are a meticulous senior Go engineer performing code review."},
    {"role": "user", "content": "As a go reviewer, review the code...\n\nvar m = map[string]int{}\nfunc Inc(k string){ go func(){ m[k]++ }() }"},
    {"role": "assistant", "content": "There is a data race: ..."}
  ]
}
```

### Files & splits

`forge run` writes, into `build.output_dir` (default `data/datasets/`):

```
<name>.train.jsonl
<name>.validation.jsonl      # omitted when val_ratio == 0
<name>.manifest.json         # name, created_at, splits, per-file sha256 + stats
```

where `<name>` is `build.name` (e.g. `go_generator_v1`). The guild's anvil
recipes point `dataset.path` / `dataset.eval_path` at the `.train.jsonl` /
`.validation.jsonl` files respectively.

> **Parquet** is optional and identical in columns (with `messages` JSON-encoded
> as a string). It is only emitted when `"parquet"` is in `build.formats` and
> `pyarrow` is installed.

---

## How the guild builds data

Each specialist has a forge recipe under `go/forge/<id>.yaml`. Roles passed in
`generate.roles` must be registered in forge's `ROLE_REGISTRY`
(`forge/src/core/instruction_gen.py`).

| Specialist     | Forge role     | Registered in forge today? |
| -------------- | -------------- | -------------------------- |
| `go_generator` | `go_generator` | ✅ yes |
| `go_reviewer`  | `go_reviewer`  | ✅ yes |
| `go_explainer` | `go_explainer` | ✅ yes |
| `go_tester`    | `go_tester`    | ❌ **no — must be added** |

### Adding the `go_tester` teacher role

Forge does not ship a `go_tester` role yet, so `go/forge/go_tester.yaml` will
fail until one is registered. Add this alongside the existing roles in
`forge/src/core/instruction_gen.py`:

```python
Role(
    "go_tester",
    "You are an expert Go test engineer. Given code, write thorough, "
    "table-driven tests using the standard testing package, covering edge "
    "cases, error paths and concurrency.",
    "write runnable, table-driven Go tests that exercise the given code",
)
```

(register it in the same `for _role in (...)` loop). This is the one upstream
change the guild requires; everything else uses forge as-is.

---

## Committed sample dataset (`go/datasets/`)

A small, **deterministic** sample dataset is committed under
[`go/datasets/`](./go/datasets/) as a runnable fixture, built by actually
running forge's pipeline offline over a handful of curated Go snippets:

```
go/datasets/
├── build_sample.py                 # drives forge: process -> generate -> build
├── sources/                        # 5 curated, Apache-2.0, idiomatic .go snippets
└── code_guild_sample_v1/
    ├── code_guild_sample_v1.train.jsonl        # 18 records
    ├── code_guild_sample_v1.validation.jsonl   #  2 records
    ├── code_guild_sample_v1.manifest.json
    └── DATASET_CARD.md
```

It uses all four Go roles (`go_explainer`, `go_reviewer`, `go_generator`,
`go_tester`) — `5 snippets × 4 roles = 20` records, split 18/2 at `seed=42`.

> ⚠️ **Honest provenance:** this is built in forge's **offline** mode, so every
> `response` is a deterministic *synthetic placeholder*
> (`[offline:<role>:<seed>] ...`), **not** a teacher- or human-grade label. It
> exists to **smoke-test** the data → train pipeline end-to-end with no network,
> GPU, or teacher endpoint — it is **not** a benchmark-quality corpus. See
> [`go/datasets/code_guild_sample_v1/DATASET_CARD.md`](./go/datasets/code_guild_sample_v1/DATASET_CARD.md)
> for full provenance, checksums, and limitations.

Regenerate it (deterministic) with forge's virtualenv:

```bash
cd go/datasets
/path/to/forge/.venv/bin/python build_sample.py   # or: python build_sample.py in an activated forge venv
```

---

## Evaluation datasets

Crucible suites read a different, evaluation-time schema (see
`crucible/src/core/runner.py`). Each line is:

```json
{"id": "...", "prompt": "...", "reference": "...", "prediction": "...", "metadata": {}}
```

- `go_functional` suites (`go_generator`, `go_tester`) require
  `metadata.module` and `metadata.tests` (the Go test source); `prediction` is
  the Go code to build and run.
- `llm_judge` / `safety` suites (`go_reviewer`, `go_explainer`) compare
  `prediction` against `reference`; `metadata` may set `expect_refusal`,
  `require_citation`, or extra `banned_patterns`.

Small runnable samples live in `go/crucible/data/`. Replace them with your
model's real predictions to measure pass@1 / rubric scores.

---

## Dataset card template

Copy this into a `cards/<name>.md` when you publish a dataset release.

```markdown
# Dataset card — <name> (e.g. go_generator_v1)

- **Specialist:** go_generator
- **Forge recipe:** go/forge/go_generator.yaml
- **Forge role(s):** go_generator
- **Built with:** forge <version/commit>
- **Teacher model:** <model id, or "offline synthetic">
- **Created:** <ISO date>  ·  **Records:** <train> / <val>

## Source
- **Discovery query:** `language:go stars:>2000 NOT awesome NOT tutorial`
- **max_results:** 40
- **License filter:** allow_unknown_license = false

## Processing
- include_extensions: [".go"]  ·  min/max length: 200 / 50000
- near_dup_threshold: 0.85

## Intended use
What the specialist learns from this data and where it should NOT be used.

## Known limitations & risks
Synthetic-teacher artefacts, domain gaps, licensing caveats, leakage checks vs.
the matching crucible suite.

## Provenance & checksums
Paste the `*.manifest.json` `files[].sha256` entries here.
```
