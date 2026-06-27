# Dataset card — `code_guild_sample_v1`

A tiny, **deterministic** SFT dataset built by running [forge](https://github.com/guildlm/forge)'s
real pipeline (process → generate → build) over a handful of curated Go
snippets, in forge's **OFFLINE** mode.

> ⚠️ **Honesty note — these are synthetic placeholder responses, not training-grade labels.**
> Offline mode does not call any teacher model. Each `response` is a
> deterministic, content-seeded placeholder of the form
> `[offline:<role>:<seed>] This deterministic placeholder stands in for a
> teacher-generated answer that would <role task>. It references N characters of
> context.` This dataset exists to **smoke-test the data → train pipeline
> end-to-end** with no network, GPU, or teacher endpoint. It is **not** a
> benchmark- or production-quality training corpus and must not be used to
> actually fine-tune a shippable specialist.

## At a glance

- **Name:** `code_guild_sample_v1`
- **Guild / domain:** Code Guild (Go)
- **Built with:** `guildlm-forge` 0.1.0 (forge commit `e1f0eb8`), forge offline `InstructionGenerator`
- **Teacher model:** none — **offline synthetic** (deterministic placeholders)
- **Roles used:** `go_explainer`, `go_reviewer`, `go_generator`, `go_tester` (all four Code Guild specialists)
- **Created:** 2026-06-27
- **Records:** 20 total — **18 train / 2 validation**
- **Seed:** 42 (deterministic split) · **val_ratio:** 0.1

## What it is

5 small, self-contained, idiomatic Go source files (under `../sources/`) are
each turned into one `(instruction, response)` pair per teacher role, giving
`5 sources × 4 roles = 20` records. The pairs are then validated, split, and
exported by forge's `DatasetBuilder`.

### Source files (`../sources/`)

| File | What it demonstrates |
| --- | --- |
| `http_handler.go` | stdlib HTTP handlers (`ServeMux`, JSON, status codes) |
| `worker_pool.go` | bounded worker pool over channels + `sync.WaitGroup` |
| `error_wrap.go` | error wrapping with `%w`, `errors.Is`, sentinel errors |
| `lru_cache.go` | fixed-capacity LRU cache (`container/list` + map) |
| `stack_test.go` | generic LIFO stack with a table-driven test |

These are the repository authors' own simple examples, written for this fixture
and licensed under the repository's **Apache-2.0** license. No third-party code
was scraped or cloned.

## Schema

Each JSONL line is one record with exactly forge's four
`SCHEMA_FIELDS` (`forge/src/core/dataset_builder.py`):

| Field | Type | Notes |
| --- | --- | --- |
| `instruction` | string | Role-styled task, references the snippet's first line. |
| `response` | string | **Offline synthetic placeholder** (see honesty note). |
| `context` | string | The full Go source snippet. |
| `messages` | array of `{role, content}` | `system` → `user` (instruction + context) → `assistant` (response). |

The system message is `You are a GuildLM Go specialist.`

## Files & splits

```
code_guild_sample_v1.train.jsonl          18 records
code_guild_sample_v1.validation.jsonl      2 records
code_guild_sample_v1.manifest.json         name, created_at, splits, per-file sha256, stats
```

## Provenance & checksums

From `code_guild_sample_v1.manifest.json` (`files[].sha256`):

| File | Records | SHA-256 |
| --- | --- | --- |
| `code_guild_sample_v1.train.jsonl` | 18 | `9e5cdc762cff7c7eae94222ebbb132f8dbb2949ff36ddb51d8dcb9d41bee4e09` |
| `code_guild_sample_v1.validation.jsonl` | 2 | `f30a36b1959224c404c6ccd6a61c38a44686b5340e32877d2b115a6e4b2724ad` |

Cleaning stats: 5 in → 5 out (0 exact dups, 0 near dups, 0 license/length/encoding
filtered, 0 PII redactions).

> The exact `sha256` / `created_at` are regenerated on each run. The record
> count, splits, instructions, and synthetic responses are deterministic for a
> fixed forge version, source set, role set, and seed; the file hashes change
> only if forge's serialization or the inputs change (`created_at` lives in the
> manifest, not in the JSONL data files, so the data hashes are stable).

## How to regenerate

From this directory's parent (`guild-code/go/datasets/`), using forge's venv:

```bash
/path/to/forge/.venv/bin/python build_sample.py
# or, inside an activated forge venv:
python build_sample.py
```

The script adds the forge repo to `sys.path` (override its location with
`FORGE_ROOT`), processes `sources/`, runs the offline generator across the four
Go roles, and rewrites this directory.

## Intended use

- **Smoke-testing** the GuildLM data → train (anvil) handoff: a real, schema-valid
  forge dataset that loads with no network/GPU.
- A fixture/example of the exact JSONL contract documented in
  [`../../../DATASETS.md`](../../../DATASETS.md).

## Limitations & risks

- **Responses are synthetic placeholders** — training on them teaches nothing
  useful; any model fit to this data will just learn to emit the placeholder
  template. Do not benchmark or ship.
- **Tiny and non-representative** — 5 hand-written snippets, no coverage of real
  Go-codebase diversity.
- **No teacher signal** — the instructions are role-templated, not curated by a
  strong model or human.
- For a real dataset, set `offline=False` (or `generate.offline: false` in a
  forge recipe) and point forge at a teacher via `FORGE_TEACHER_BASE_URL` /
  `FORGE_TEACHER_API_KEY` / `FORGE_TEACHER_MODEL`, then discover real
  permissively-licensed repositories rather than these toy snippets.
