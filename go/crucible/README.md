# crucible — held-out Go benchmarks + a model-free integrity pipeline

This directory answers one question for the GuildLM thesis — *does a small Go
specialist beat a general model, and if so, is it the model or the agentic
algorithm around it that wins?* — with held-out benchmarks that are scored the
same way every time.

Benchmark numbers are only worth as much as the harness that produced them. In
this directory a conclusion turned out to be a **harness artefact** more than
once (an unterminated ` ```go ` fence scored as invalid Go, in three harnesses
at once; a keyword rule a canned checklist could game; a silent EOS-registration
failure that made tuned adapters ramble). Every fix shipped with its own checker,
and **a checker nobody runs is not a gate** — so they all run from one command.

## One command

```
python3 verify_pipeline.py     # exit 0 = every integrity gate green (12 gates)
```

Model-free and deterministic: it needs only the Go toolchain, `goimports`, and
the Python stdlib — no model, no GPU — which is why it gates CI
(`.github/workflows/crucible-gates.yml`) where `builder/`'s mutation suite
cannot (that one needs generated model artefacts). The 12 gates:

1. harness helper self-tests (`extract_code` / `_repair_imports` / selector / tag)
2. `verify_bench` itself fires on a planted-bad bench (`--self-test`)
3. the contamination matcher fires on a planted leak (`--self-test`, corpora-free)
4. all harnesses share **one** copy of each valid-Go helper (a re-copied helper
   is how the fence bug reappears in a fourth harness)
5–8. `verify_bench` on each bench (dev / edit / test_hard green; the original
   test bench is pinned **UNVERIFIABLE** — it carries no witness/naive tests)
9–11. review scoring is still gameable under the recorded rule, **not** gameable
   under the strict one, and still credits genuine reviews
12. the review bench is **solvable** — every gold reference review passes the
   recorded rule (the "reference passes its own test" check, for the one bench
   `verify_bench` cannot execute)

Each gate is proven non-vacuous: injecting the defect it guards turns it red.

## Benchmarks (`data/*.jsonl` are authoritative; the `.yaml` are eval configs)

| bench | tasks | measures | integrity gate |
|---|---|---|---|
| `go_dev_bench` | 48 | spec → code, pass@1 | `verify_bench` (ref passes, empty impl fails) |
| `go_dev_bench_clean45` | 45 | dev bench minus 3 contaminated tasks | subset of the above |
| `go_edit_bench` | 8 | fix flawed code, pass@1 | `verify_bench` (+ echo-degenerate: original must fail) |
| `go_test_bench` | 18 | write a test that catches a mutant | **pinned UNVERIFIABLE** (16/18 mutants die to one happy-path assert) |
| `go_test_bench_hard` | 18 | same, edge-case mutants | `verify_bench` (witness isolates, mutant survives naive) |
| `go_review_bench` | 8 | name the real defect (keyword-scored) | solvability (gold review passes recorded rule) |

## Harnesses — which number each produces

- `mlx_bench.py` — dev-bench pass@1 for a local MLX model ± LoRA. **Headline
  generation number.** Splits a miss into compiles / passes-given-compiles.
- `mlx_test_bench.py` — test-writing mutation score (catch = passes-on-correct
  AND fails-on-mutant). Owns the shared valid-Go helpers.
- `mlx_review_bench.py` — review identify@1, keyword or strict `discriminative`.
- `bench_compare.py` — dev bench via an Ollama endpoint (served regime).
- `behavior_probe.py` — DAPT chat-integrity probe. **Needs a model** (not in CI).

All four MLX harnesses register the chat EOS explicitly and **warn loudly** if it
fails to encode — a silent skip makes tuned adapters ramble to `max_tokens` and
score ~0, silently corrupting the A/B.

## Model-free tooling

- `verify_bench.py` — bench data integrity (broken / degenerate / echo-degenerate
  / duplicate). `--self-test` proves it fires.
- `check_contamination.py` — is a reference verbatim in the training corpus? The
  full run needs the 170MB+ gitignored corpora; its matcher `--self-test` gates.
- `probe_review_scoring.py` — how gameable review keyword-scoring is + solvability.
- `rescore_{dev,test,review}_bench.py` — re-score saved `--save-generations`
  offline (a deterministic repair never needs the model again). The harnesses
  record a row for **every** task they scored, including errored ones, so an
  offline re-score divides by the same denominator as the live run.
- `build_go_*_bench.py` — regenerate a bench (each self-verifies its references).

## The finding (detail: `RESULT-go-dev-bench-v2.txt`, `AUDIT-secondary-benchmarks.txt`)

Once the measurement was repaired, every recorded specialist effect on the
secondary benches either reversed or evaporated, and the one real generation
effect shrank (−6 → −4) with a mechanism of **Go hygiene, not reasoning**: the
gap is almost entirely "does the file compile / import cleanly", which the real
Builder loop already gates with `goimports`. With the algorithm term on
(imports repair, best-of-N), base and specialist converge — capability reads as
**model × algorithm**, and on this project's tasks the algorithm dominates.

## Method notes

- **Measure before you conclude.** A single score usually squashes two opposite
  failures (invalid code vs blind test); split it before acting on it.
- **Never re-run the model for a deterministic post-hoc repair.** Greedy is
  deterministic — re-score the saved generations offline in seconds.
- **A gate that never fails isn't a gate.** Every gate here is proven to fire.
