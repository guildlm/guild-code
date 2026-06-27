# Datasets

The Code Guild consumes the supervised fine-tuning (SFT) datasets produced by
[forge](https://github.com/guildlm/forge). This document pins the exact JSONL
schema the guild relies on, how it is built, and a dataset-card template for
documenting each release.

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
