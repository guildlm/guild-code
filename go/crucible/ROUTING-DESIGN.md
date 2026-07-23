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

## 2. What to build (minimal, in builder/, NOT touching the scoring path)

A `route` step that wraps generation: instead of one model producing one candidate, generate
from a small fleet and let the Builder's EXISTING gate pick.

    for model in fleet:                      # base first (best single model)
        cand = generate(model, prompt)
        if gate(cand) == PASS:               # gate = compile + vet + project tests
            return cand                      # first gate-passing candidate wins
    return best_by_gate_progress(cands)      # none fully pass -> the one that got furthest

Base first means the fleet is only consulted when base's candidate FAILS the gate — so the
cost is ~1 model call on the tasks base already solves (the majority) and grows only on the
hard tail. This is the realizable analogue of the oracle union, with the test gate standing
in for the oracle.

## 3. Why it should work where compile-gating failed

The realizable-router result is not a negative for THIS design — it is the reason for it.
Compile-gating failed because compile does not discriminate the rescue cases; the Builder's
gate includes `go test`, which does. The ceiling is bounded by how well the project's own
tests exercise the rescued behaviour: on go_dev_bench the hidden tests fully discriminate
(so the ceiling is the full +4); on a real project it is however much the project's tests
cover. So the expected gain is "real but project-dependent", not the flat +4/48.

## 4. THE THREE DECISIONS (owner's call — implementation is mechanical after)

D1. FLEET COMPOSITION. Minimum useful fleet from the evidence: `base-7B` (backbone) +
    `go-dev-final` (rune/string rescues: 3 tasks) + `go-dev-14b` (concurrency: the only
    model that gets ctx_cancel_worker). That is 3 members covering all 4 rescue niches.
    Bigger fleets add cost, little coverage (the other specialists overlap final/14b).
    -> pick {base, final, 14b} as the default, or a different set.

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
