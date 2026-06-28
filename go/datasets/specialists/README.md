# Go specialists — per-role datasets & training

Dedicated single-purpose Go models, each 7–14B, each trained on its own
compile-verified slice of the teacher dataset. The GuildLM thesis: a *narrow*
Go model beats a general LLM on Go, because no general model ships Go-specific
training at this size — so clean, role-focused, compile-verified data wins.

These splits are produced from the teacher-authored batches by
`../teacher/export_role_splits.py` (which compile-verifies every `go_generator`
example with the real Go toolchain, dedupes, and emits one dataset per role).
Regenerate after adding a `teach_examples_*.py` batch:

```bash
cd ../teacher && python export_role_splits.py
```

| Specialist | Dataset | Role | Records | Trains it to… |
|-----------|---------|------|---------|---------------|
| **go-dev** | `code_guild_go_dev` | `go_generator` | 190 | turn a spec into idiomatic, compilable Go |
| **go-review** | `code_guild_go_review` | `go_reviewer` | 59 | find real Go bugs + give the idiomatic fix |
| **go-test** | `code_guild_go_test` | `go_tester` | 37 | write table-driven tests that compile & pass |
| go-explain | `code_guild_go_explain` | `go_explainer` | 20 | explain Go code (bonus split) |

Each dataset is `*.train.jsonl` + `*.validation.jsonl` in OpenAI `messages`
format (system/user/assistant), ready for anvil unchanged.

## Train (free Kaggle GPU, $0)

Recipes live in `../../anvil/{go_dev,go_test,go_review}.yaml` — base
`qwen2.5_coder_14b` (swap to `qwen2.5_coder_7b` for less VRAM), QLoRA, 3 epochs.

```bash
# from guild-code/go/anvil, with the anvil repo importable
anvil-train --config go_dev.yaml --configs-root ../../../anvil/configs
```

## Prove it beats a general LLM

Objective, Docker-free, pure `go test` scoring on a held-out benchmark of 12
spec→code tasks with hidden tests (`../../crucible/data/go_dev_bench.jsonl`,
self-verified by `build_go_dev_bench.py`):

```bash
cd ../../crucible
python bench_compare.py --models guildlm-go-dev,qwen2.5-coder:7b
# first model is the specialist; exit 0 iff specialist pass@1 >= baseline
```

A task counts only if the model's *own* generated code compiles and passes the
hidden test — pass@1, no judge.

Two benchmarks (same runner, `--bench`):

| Benchmark | Measures | File |
|-----------|----------|------|
| `go_dev_bench.jsonl` | from-scratch spec→code | 12 tasks, hidden tests |
| `go_edit_bench.jsonl` | **editing** flawed code on request | 8 tasks, hidden tests |

```bash
python bench_compare.py --models guildlm-go-dev,qwen2.5-coder:7b --bench data/go_edit_bench.jsonl
```
