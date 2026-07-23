# Test-gated model routing — design spec (grounded in the go_dev_bench evidence)

This is the concrete next build the measurement work points to. It is written to be
decision-forcing: the empirical case is settled below; what remains are three choices
(§4) that only the project owner should make, after which implementation is mechanical.

## 1. The evidence that motivates it (all in RESULT-go-dev-bench-v2.txt, offline-reproducible)

- No single model beats base on go_dev_bench: base = 44/48 (+goimports) is the best single
  model across every 7B recipe and 14B. Specialists are net-negative.
- But specialists rescue base's exact blind spots. Oracle union of base + all specialists =
  **48/48** (+4): `rune_at`, `title_case`, `chunk_reader` (7B specialists, rune/string) and
  `ctx_cancel_worker` (go-dev-14b alone, concurrency).
- The +4 is an ORACLE gain. A realizable **compile-gated** router captures **0** of it, because
  base's wrong answers on those 4 tasks all compile — compile/vet cannot tell a wrong-but-
  compiling answer from a right one (realizable_router.py).

CONCLUSION: routing pays off **iff the selector can run tests**, not just compile/vet. The
Builder already has a test gate (it runs the generated project's tests), so the gain is
capturable there — this is the one place the ensemble's +4 becomes real.

## 1b. Builder architecture check (read src/builder.py) — RESOLVES the key caveat

Two facts from the actual Builder code change the picture in the build's favour:
- The Builder gates on `GoToolchain.check` = build + vet + test, and PASSING that gate IS
  success. Unlike go_dev_bench (model scored on HIDDEN tests it cannot see), the Builder's
  selection signal and its success criterion are THE SAME tests. So the "compile captures 0"
  caveat is go_dev_bench-specific and does NOT apply here — routing selects on exactly what
  it is judged by, so more diverse attempts monotonically help.
- Clean integration points already exist: a pluggable `Coder` protocol (a `FleetCoder` drops
  in with no core-loop change), an existing role router (`_by_role`), and `_fix_loop` which
  already carries a `candidates` (best-of-N per file) budget and repairs via the coder against
  the gate. Fleet-routing is therefore NOT a rewrite: it is "on a file that keeps failing the
  gate across rounds, ESCALATE to a different fleet member" inside the existing fix loop.

So the build is smaller and safer than first assumed, and its payoff caveat is lifted for the
Builder setting specifically.

## 2. What to build (minimal, in builder/, NOT touching the scoring path)

Concretely, given §1b, the minimal build is:
1. `FleetCoder(Coder)`: holds an ordered fleet of Coders (each an OpenAICoder pointed at a
    different model/adapter) + tracks which member is "current". Its `generate` delegates to
    the current member. New file, ~40 lines.
2. In `_fix_loop`: track per-file failure rounds (the loop already widens targets on repeated
    runtime failure — same signal). When a file has failed the gate for K rounds under the
    current member, ADVANCE the FleetCoder to the next member for that file's repairs. The
    gate/candidates machinery is unchanged; only the coder the repair calls escalates.

    # sketch of the escalation, inside the existing per-file repair path:
    if stubborn[path] >= ESCALATE_AFTER and fleet.has_next():
        fleet.advance()                      # base -> final -> 14b for THIS file
        stubborn[path] = 0

Base first means the fleet is only consulted when base's candidate keeps FAILING the gate —
so the cost is ~0 extra calls on the tasks base already solves (the majority) and grows only
on the hard tail. Passing the gate is success, so escalating to a model that gets a task base
misses (final: rune/string; 14b: concurrency) directly converts to a green build.

## 3. Why it should work where compile-gating failed

The realizable-router result is not a negative for THIS design — it is the reason for it.
Compile-gating failed because compile does not discriminate the rescue cases; the Builder's
gate includes `go test`, which does. The ceiling is bounded by how well the project's own
tests exercise the rescued behaviour: on go_dev_bench the hidden tests fully discriminate
(so the ceiling is the full +4); on a real project it is however much the project's tests
cover. So the expected gain is "real but project-dependent", not the flat +4/48.

## 4. THE THREE DECISIONS (owner's call — implementation is mechanical after)

D1. FLEET COMPOSITION. VALIDATED (ensemble_ceiling.py on the committed generations):
    the 3-member fleet {base-7B, go-dev-final, go-dev-14b} reaches 48/48 — IDENTICAL to
    the full 10-model fleet. Coverage: final -> chunk_reader, rune_at, title_case;
    go-dev-14b -> ctx_cancel_worker (only model that gets it) + rune_at, title_case. The
    other 7 specialists are redundant for the ceiling. So D1 is effectively decided: use
    {base, final, 14b} unless you want a different trade. This also bounds D2 to 3 models.

D2. SERVING. 7B-4bit (~4GB) and 14B-4bit (~8GB) do not comfortably co-reside for parallel
    calls on a typical Mac. Options: (a) SEQUENTIAL load-per-call (simple, slow: model
    load dominates); (b) a persistent mlx_lm.server per model (fast, ~12GB resident);
    (c) keep base resident, load 14b only on the tail where base fails the gate (a good
    middle — the 14b call is rare). -> pick the serving model + memory budget.

D3. COST CEILING. Base-first means N model calls only on gate-failing tasks. Set a cap:
    max fleet members tried per task, and whether to run them in parallel (latency) or
    sequentially (memory). -> pick the max-calls budget.

## 5. How to validate the build (reuse what exists)

- Offline first: the fleet's generations are already committed (data/go_dev_bench_*_greedy.jsonl).
  A test-gated router simulation that selects by the HIDDEN test is the oracle (= 48, already
  have it via ensemble_ceiling.py); a version that selects by a HELD-OUT subset of the tests
  approximates the realizable gain without any model call. Build that simulator first to size
  the expected gain before wiring live generation.
- Live: run the routed loop on a few builder specs, score with score_backend.py, compare
  fix-rounds and green-rate to single-model (the builder A/B already established base≈spec
  single-model; routing should show base < routed).

## 6. Explicit non-goals / risks
- Not a replacement for training better specialists — it is orthogonal (routing multiplies
  whatever members you have).
- Latency and memory are the real costs; the base-first + rare-14b policy is what keeps them
  bounded. If base passes the gate on most tasks, routing is nearly free; if not, it is N×.
- Do not route by compile/vet alone — realizable_router.py proves that buys nothing here.
