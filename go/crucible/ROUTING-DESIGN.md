# Test-gated model routing — design spec (grounded in the go_dev_bench evidence)

> STATUS: IMPLEMENTED in builder/ (commits 56a868d FleetCoder · 3ded2c1 _fix_loop
> escalation · 126a063 RoleRoutingCoder composition · a36a445 --fleet CLI). Suite 333 -> 351
> green, backward-compatible (no --fleet = unchanged). Activate:
> `builder ... --fleet go-dev-final,go-dev-14b@<14b-url>`. Only live serving of the members
> (D2/D3 below) remains — the logic is done and offline-tested. Sections below are the
> rationale that shaped it.

This is the concrete next build the measurement work points to. It is written to be
decision-forcing: the empirical case is settled below; what remains are the choices in
§4 that only the project owner should make, after which implementation is mechanical.
(§4 grew a D4 that the owner does NOT get to make — it was answered by measurement.)

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

## 4. THE DECISIONS (owner's call — implementation is mechanical after)

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

D4. WHICH FILES ARE ESCALATION-ELIGIBLE. **SETTLED 2026-07-25 — every fix target is, and
    this is not a knob to turn down.** The obvious cost saving is to escalate only files
    the toolchain NAMES, leaving the ones root-cause widening pulled in to be repaired by
    whichever member already owns them. It was implemented, measured and reverted
    (builder 3095b7f; write-up in builder logs/FINDING-escalation-granularity.txt):

      - BOTH green fleet arms in 5d, each re-run against its own recorded control:
            shortener  widened 12 esc 1174s 3/3 GREEN | blamed-only 2 esc 1080s 2/3 RED
            workapi    widened 17 esc 4778s 3/3 GREEN | blamed-only 5 esc 4654s 2/3 RED
        Cheaper on both axes and worse where it counts, twice. workapi shows the
        mechanism directly: all five escalations were _test.go files, while the handler
        that actually fails (200 where the spec requires 201) was repaired seven times
        and escalated zero times.
      - across 32 archived failing artifacts: where implementation files are being
        repaired and NOT ONE is blamed — compile failures 0/13, test failures 18/19.

    THE REASON, which is a property of the Go toolchain and will not change: a compiler
    error names an implementation file; a failing assertion names the TEST. So an
    implementation defect that only a test can reveal enters the fix targets ONLY through
    widening, and escalating only blamed files makes it permanently unreachable by a
    stronger member. The breadth that looks like waste in the 5d cost table is the sole
    route to a whole class of defect.

    Corollary for anyone tuning cost later: escalation breadth is the wrong place to cut.
    The 5d cost analysis already points at the right one — cost scales with UNRESOLVED
    escalations, so the lever is stopping early on files that are not converging (D3), not
    narrowing which files may escalate at all.

## 5. How to validate the build (reuse what exists)

- Offline first: the fleet's generations are already committed (data/go_dev_bench_*_greedy.jsonl).
  A test-gated router simulation that selects by the HIDDEN test is the oracle (= 48, already
  have it via ensemble_ceiling.py); a version that selects by a HELD-OUT subset of the tests
  approximates the realizable gain without any model call. Build that simulator first to size
  the expected gain before wiring live generation.
- Live: run the routed loop on a few builder specs, score with score_backend.py, compare
  fix-rounds and green-rate to single-model (the builder A/B already established base≈spec
  single-model; routing should show base < routed).

## 5b. ACTIVATION RUNBOOK (verified commands — the D2 last mile)

All three fleet pieces exist locally. Recommended serving = one persistent server per
member (D2 option b), three ports.

⚠️ ADAPTER MEMBERS MUST BE SERVED WITH `serve_adapter.py`, NOT `mlx_lm.server`.
`mlx_lm.server --adapter-path X` (mlx_lm 0.31.3) SILENTLY serves the plain base model —
it registers the adapter under the key 'default_model' but looks it up by the resolved
model id, so the lookup misses and the flag becomes a no-op with no error and a 200
response. A "specialist" port then answers in the base's voice and every downstream A/B
silently compares base against base. `serve_adapter.py` is a drop-in fix with the same
CLI. Full evidence + what it retroactively corrects: FINDING-serving-adapter-noop.txt.

    # from the repo root, with the mlx venv's python (.mlx-venv/bin/python)
    # member 0 (base 7B — no adapter, plain mlx_lm.server is fine):
    python -m mlx_lm.server --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit --port 8080
    # member 1 (go-dev-final = 7B base + adapter):
    python go/crucible/serve_adapter.py --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
                  --adapter-path .mlx-adapters/go-dev-final            --port 8081
    # member 2 (go-dev-14b = 14B base + adapter):
    python go/crucible/serve_adapter.py --model mlx-community/Qwen2.5-Coder-14B-Instruct-4bit \
                  --adapter-path .mlx-adapters/go-dev-14b              --port 8082

    # MANDATORY CONTROL before trusting any served A/B — the specialist port must NOT
    # echo the base. One prompt, two ports, assert the outputs differ:
    #   curl -s :8080/v1/chat/completions -d "$P" ; curl -s :8081/v1/chat/completions -d "$P"
    # Identical output means the adapter is not applied (see the FINDING).

Then run the Builder against the fleet. IMPORTANT (learned from a live smoke): the model
NAME must be the model ID each server loaded — mlx_lm.server treats the request's ``model``
field as a model to LOAD (a made-up label 404s against HuggingFace); the PORT is what
selects the adapter, so both 7B members use the SAME 7B id on different ports. The command
is ``guildlm-build main`` (a subcommand), not a bare ``builder``:

    M7=mlx-community/Qwen2.5-Coder-7B-Instruct-4bit
    M14=mlx-community/Qwen2.5-Coder-14B-Instruct-4bit
    guildlm-build main --spec <spec.yaml> --out <out-dir> \
        --base-url http://localhost:8080/v1 --model "$M7" \
        --fleet "$M7@http://localhost:8081/v1,$M14@http://localhost:8082/v1"

Verify it routed: the log prints ``impl fleet: <base> -> <members>`` at start, and
``escalating <file> to the next fleet member`` when a file is handed on. Memory: the three
servers co-resident are ~4+4+8 = 16GB; if that is too much, drop to {base, go-dev-14b} (2
ports, ~12GB — 14b alone still rescues ctx_cancel_worker) or use D2 option (c) and start
the 14b server only for a spec whose builds stall. Cheapest correct sizing, per D1/D2.

VALIDATED LIVE (2026-07-24): base :8080 + go-dev-final :8081, then the command above on
specs/demo-small.yaml (stringkit — rune Reverse + IsPalindrome, the rune/string niche).
The --fleet path constructed the fleet and generated a GREEN build (independent `go test`
ok, Unicode-safe rune reversal). Base greened it first-try so escalation did not fire —
expected: escalation is for the hard tail, and the offline test
(test_fleet_escalates_to_a_member_that_can_fix_it) proves that path with real go.

⚠️ CORRECTION (same day, after the serving bug above was found): that smoke was served by
the UNPATCHED mlx_lm.server, so :8081 was really the plain base — the run was base -> base.
What it validates therefore stands only for the PLUMBING (the --fleet path builds a fleet,
routes per file, and yields a green build end-to-end); it does NOT show a specialist member
was exercised. The 5c escalation demo below is unaffected (its members differ by --model,
not --adapter-path, so no adapter was needed). Re-validation with genuinely-adapted members
is what 5d records.

## 5c. LIVE escalation demo (2026-07-24) — the mechanism fires; rescue is target-bounded

To exercise an actual escalation live, a deliberately-weak fleet {1.5B base :8080, 7B :8081}
was run on stringkit. Result, verbatim from the log:
  - round 1: 1.5B's build fails (`undefined: Reverse` at the test's call site);
  - round 2: still failing -> `escalating stringkit_test.go to the next fleet member` — the
    ESCALATION FIRES LIVE with real model serving (the last unproven combination; the offline
    test already proves escalate->green with real go);
  - rounds 3-6: still `undefined: Reverse`; no convergence.
Diagnosis (CORRECTED after reading the generated files — the first pass mis-blamed a compile
cascade; the real cause is simpler and the targeting was RIGHT): 1.5B wrote stringkit_test.go
as `package stringkit_test` (an EXTERNAL test package) but called bare `Reverse(...)`. An
external test package can only reach exported identifiers via the qualifier `stringkit.Reverse`,
so bare `Reverse` is undefined. stringkit.go itself compiles standalone (`go build` exit 0) —
there is NO cascade; the impl is fine. So the failing file really IS the test, the fix loop
targeted it CORRECTLY, and escalating it to 7B was the right target. What did not happen is a
REPAIR: neither model's fix restructured the test (change to `package stringkit` OR qualify the
calls), each kept `package stringkit_test` + bare `Reverse`, so the error persisted.
CONCLUSION: this is a repair-quality limit on a specific structural error (external test
package + bare symbol), NOT a targeting problem — escalation put the file in front of the
stronger model, but the fix prompt did not steer either model to the structural rewrite.
It is a weak-model artefact: the healthy 7B-only smoke (5b) greened stringkit first try.
FIX SHIPPED: improvement (a) is now a deterministic gate — builder `_fix_external_test_package`
(commit 4bdbc6c) rewrites `package X_test` -> `package X` when a *_test.go references bare
symbols X declares. Verified end-to-end on this demo's ACTUAL files: the gate rewrites the
clause and `go test` goes green — the exact failure neither model could repair, now fixed
deterministically for ANY model (suite 351 -> 355). So the demo surfaced a real builder gap
and it is closed. NOTE: this corrects the earlier "escalate the definition file" suggestion,
which was based on the wrong (cascade) diagnosis.

## 6. Explicit non-goals / risks
- Not a replacement for training better specialists — it is orthogonal (routing multiplies
  whatever members you have).
- Latency and memory are the real costs; the base-first + rare-14b policy is what keeps them
  bounded. If base passes the gate on most tasks, routing is nearly free; if not, it is N×.
- Do not route by compile/vet alone — realizable_router.py proves that buys nothing here.

## 5d. SCALED MEASUREMENT (2026-07-24) — routing turns a RED build GREEN

The first project-scale A/B with genuinely-adapted members (see the serving warning in 5b).
Same spec, same 8-round budget, same base; the only intervention is `--fleet`.

    specs/shortener.yaml     score          escalations   wall
      base-only              2/3  RED  (test fails)   0     719s
      base-first fleet       3/3  GREEN             12    1174s

Independently re-verified: `go test ./...` ok (fleet) vs FAIL (base). The base burned its
whole budget re-writing the SAME wrong test nine times — it JSON-decoded the body of a 301
redirect (`GET /r/{code}`), which the spec explicitly tells it not to do. An escalated member
returned the file structurally correct. That is exactly the model-shaped tail the gate
campaign refused to gate, absorbed by routing instead.

Honest other half: escalation is NOT monotone. Both arms hit the same `Encode(62)=="01"`
codec bug; the BASE fixed it unaided, while in the fleet arm that file had been escalated and
the bug survived two rounds before recovering. Routing is a trade whose net sign must be
measured. Cost: +63% wall clock. Granularity: when the fix loop widens to package-wide
repair, escalation goes fleet-wide rather than staying targeted — an open improvement.

Full write-up, caveats, and the discarded first attempt: RESULT-fleet-ab.txt.

### 5d (cont.) — second data point, and the cost

    specs/taskapipro.yaml (20 files)   score                      escalations   wall
      base-only                        0/3  does not even BUILD       0         3389s
      base-first fleet                 2/3  build ok, vet ok          27       10382s

Base died on a CROSS-FILE contract mismatch (`store.CreateTask` returns `error`, the service
caller wants `(models.Task, error)`) and never moved off that surface in 11 rounds. The fleet
resolved it — kept the store's signature, rewrote the caller — then advanced through new error
surfaces to extension round 10, ending on a semantic bug (ListProjects sort order).

So routing improved the score on BOTH specs (2/3 -> 3/3 green, 0/3 -> 2/3). It also cost
+63% and 3.1x wall clock respectively: near-free while the base carries most files, expensive
once the tail is long. On specs this size the fleet was still finding NEW error surfaces when
the round budget ran out — so raise the ROUND budget before enlarging the fleet.

This also corrected a prediction: per-file escalation DOES resolve cross-file contract
mismatches, because a contract has a right answer visible from either side, and picking that
side is a model-quality question. See RESULT-fleet-ab.txt.

### 5d (correction) — "raise the ROUND budget" was tested and FALSIFIED

The paragraph above recommended more rounds before a bigger fleet. Re-running the identical
taskapipro fleet arm with --max-fix-rounds 16 gave 2/3 again — same score, same two failing
tests, +4300s — and stopped on "error surface repeats". So DISREGARD that recommendation.
The remaining failure is a stable model fixed point (all three members rewrite the test the
same wrong way), not a budget shortfall. Neither rounds nor routing moves it; see
RESULT-fleet-ab.txt "CORRECTION".

### 5d (composition ablation) — the full 2x2, and a correction

Full composition matrix, every cell toolchain-verified:

                  shortener   workapi
  base              2/3         1/3
  {base, 7B-spec}   1/3         1/3
  {base, 14b}       1/3         2/3
  {base, 7B, 14b}   3/3         3/3

The full 3-member fleet is the ONLY config that greened both specs; no 2-member subset did.
On the clean spec (workapi) the members are complementary — dropping either costs a point.
CORRECTION: an earlier note here said the 7B specialist added nothing; that was from one
ablation direction and is wrong — {base,14b}=2/3 < {base,7B,14b}=3/3, so the 7B contributes.
Shortener is confounded (base emits a degenerate test generation; both 2-member fleets regress
below base on escalation timing), so weight workapi. D1 "keep all three" stands, now for a
project-scale reason. Full detail + costs: RESULT-fleet-ab.txt.
