# -*- coding: utf-8 -*-
"""Score an MLX go-test specialist on the mutation benchmark, locally, $0.

For each task the model is asked to write a test for a function; the test scores
a point only if it PASSES against the correct implementation AND FAILS against
the planted buggy mutant — i.e. it genuinely catches the bug. Same local-MLX
approach as mlx_bench.py; no GGUF/Ollama needed.

Usage (with the mlx venv's python):
    python mlx_test_bench.py --adapter ~/Desktop/Personal/Dev/guildlm/.mlx-adapters/go-test
    python mlx_test_bench.py            # base (no adapter)
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile

MODULE = "sandbox"
_FENCE = re.compile(r"```(?:go|golang)?\s*\n(.*?)```", re.DOTALL)
_FENCE_OPEN = re.compile(r"```(?:go|golang)?\s*\n")
SYSTEM = (
    "You are a Go test-writing specialist. Output one complete Go test file in a "
    "single ```go block, package sandbox, standard library testing only, no "
    "commentary. Do not redefine the function under test."
)


def extract_code(text: str) -> str:
    m = _FENCE.search(text)
    if m:
        return m.group(1).strip() + "\n"
    # Unterminated fence: the model hit max_tokens before closing it. The old fallback
    # returned the raw text, keeping the ```go line, which guarantees "expected 'package'"
    # and scores a HARNESS truncation as "the model cannot write Go". Strip the opener so
    # the salvageable prefix is judged on its merits (still truncated, but honestly so).
    m = _FENCE_OPEN.search(text)
    if m:
        return text[m.end():].strip() + "\n"
    return text.strip() + "\n"


def _truncated(text: str) -> bool:
    """A fence that opens and never closes means generation ran out of tokens. Silent
    truncation biases the bench against verbose models, so it must be reported."""
    return _FENCE.search(text) is None and _FENCE_OPEN.search(text) is not None


def _go_test(impl: str, test: str) -> bool:
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "go.mod"), "w").write(f"module {MODULE}\n\ngo 1.23\n")
        open(os.path.join(d, "impl.go"), "w").write(impl)
        open(os.path.join(d, "impl_test.go"), "w").write(test)
        env = dict(os.environ, GOPROXY="off", GOFLAGS="-mod=mod")
        try:
            p = subprocess.run(
                ["go", "test", "./..."], cwd=d, capture_output=True, text=True, timeout=60, env=env
            )
        except subprocess.TimeoutExpired:
            return False
        return p.returncode == 0


def _goimports() -> str:
    """Locate goimports (commonly installed to GOPATH/bin, which is often off PATH)."""
    exe = shutil.which("goimports")
    if exe:
        return exe
    gopath = os.environ.get("GOPATH") or os.path.expanduser("~/go")
    cand = os.path.join(gopath, "bin", "goimports")
    return cand if os.path.exists(cand) else ""


def _repair_imports(src: str, exe: str) -> str:
    """Deterministic import repair — the CHEAPEST component of the algorithm term.

    A model that writes a semantically perfect table test but forgets `import "fmt"`
    scores zero on a bench that only runs the code. That miss is mechanical, and the
    real Builder loop already repairs it with a gate, so scoring the raw model without
    it measures the model's typing, not its testing. Returns src unchanged on failure.
    """
    try:
        p = subprocess.run([exe], input=src, capture_output=True, text=True, timeout=20)
    except (subprocess.TimeoutExpired, OSError):
        return src
    return p.stdout if p.returncode == 0 and p.stdout.strip() else src


def _verdict(cands, select: str) -> bool:
    """Score one task from its candidate tests. cands: [(passes_correct, catches_mutant)].

    oracle — count a catch if ANY candidate catches the planted bug. The selector peeks
             at the mutant, which a real loop cannot do, so this is an UPPER BOUND on
             the algorithm term, not a shippable number.
    valid  — REALIZABLE selector: ship the FIRST candidate that passes against the code
             under test (all a real loop can check without knowing the bug), and score
             only that one. This is what best-of-N actually buys in production.
    """
    if select == "oracle":
        return any(catches for _, catches in cands)
    for passes_correct, catches in cands:
        if passes_correct:
            return catches
    return False


def _has_valid(cands) -> bool:
    """Did the model produce ANY test that passes against the code under test?

    Splits the two failure modes a single score hides: an INVALID miss (nothing compiled
    or passed — the model failed at writing Go) versus a BLIND miss (a valid test that
    does not notice the bug — the model failed at testing). They need opposite fixes, so
    a bare 7/18 is not actionable on its own.
    """
    return any(passes_correct for passes_correct, _ in cands)


def _tag(best_of: int, temp: float, select: str, repair: str = "none") -> str:
    """Label a run's decoding regime. Must never claim 'greedy' while a sampler is
    attached: best-of-1 at t>0 is the single-sample CONTROL that separates 'temperature
    helped' from 'retrying helped'. Repair is part of the regime, so it is in the label."""
    if best_of > 1:
        base = f"best-of-{best_of}@t{temp}/{select}"
    else:
        base = "greedy" if temp == 0 else f"single-sample@t{temp}"
    return base if repair == "none" else f"{base}+{repair}"


def _self_test() -> int:
    """Model-free truth table for _verdict — the selector is the whole experiment."""
    cases = [
        # (cands, oracle, valid, has_valid)
        ([], False, False, False),
        ([(False, False)], False, False, False),          # INVALID miss
        ([(True, False)], False, False, True),            # BLIND miss
        ([(True, True)], True, True, True),
        # first valid candidate misses; a later one catches -> oracle sees it, valid ships the miss
        ([(True, False), (True, True)], True, False, True),
        # invalid candidates are skipped by both, then a catcher
        ([(False, False), (True, True)], True, True, True),
    ]
    for cands, want_oracle, want_valid, want_has in cases:
        got_o, got_v = _verdict(cands, "oracle"), _verdict(cands, "valid")
        assert got_o == want_oracle, f"oracle{cands}: {got_o} != {want_oracle}"
        assert got_v == want_valid, f"valid{cands}: {got_v} != {want_valid}"
        assert _has_valid(cands) == want_has, f"has_valid{cands}: {_has_valid(cands)} != {want_has}"
        # A catch under either selector implies a valid test — the decomposition
        # catch/valid/total must never report more catches than valid tests.
        assert not (got_o or got_v) or _has_valid(cands), f"catch without a valid test: {cands}"
    tags = [
        ((1, 0.0, "oracle"), "greedy"),
        ((1, 0.6, "oracle"), "single-sample@t0.6"),  # the control — must NOT read "greedy"
        ((4, 0.6, "valid"), "best-of-4@t0.6/valid"),
        ((4, 0.6, "oracle"), "best-of-4@t0.6/oracle"),
        ((1, 0.0, "oracle", "imports"), "greedy+imports"),
        ((4, 0.6, "valid", "imports"), "best-of-4@t0.6/valid+imports"),
    ]
    for a, want in tags:
        got = _tag(*a)
        assert got == want, f"_tag{a}: {got!r} != {want!r}"
    print(f"_verdict self-test: {len(cases)} cases OK (oracle >= valid on all)")
    print(f"_tag self-test: {len(tags)} cases OK")

    # extract_code — the unterminated-fence case cost a real task (is_prime) a point.
    closed = "sure!\n```go\npackage sandbox\n\nfunc TestX(t *testing.T) {}\n```\ndone"
    assert extract_code(closed).startswith("package sandbox"), extract_code(closed)
    assert not _truncated(closed)
    cut = "```go\npackage sandbox\n\nfunc TestX(t *testing.T) {\n\tcases := []int{1,"
    assert extract_code(cut).startswith("package sandbox"), extract_code(cut)
    assert "```" not in extract_code(cut), "unterminated fence leaked into the source"
    assert _truncated(cut), "unterminated fence must be reported as truncated"
    bare = "package sandbox\n\nfunc TestX(t *testing.T) {}\n"
    assert extract_code(bare).startswith("package sandbox")
    assert not _truncated(bare)
    print("extract_code self-test: closed / unterminated / bare fences OK")

    # The repair arm, on the real defect that motivated it: a correct table test that
    # uses fmt.Sprintf without importing fmt (verbatim shape of the base's `add` miss).
    exe = _goimports()
    if not exe:
        print("_repair_imports self-test: SKIPPED (goimports not installed)")
        return 0
    broken = (
        'package sandbox\n\nimport (\n\t"testing"\n)\n\n'
        'func TestAdd(t *testing.T) {\n\tt.Run(fmt.Sprintf("%d", 1), func(t *testing.T) {\n'
        '\t\tif Add(1, 2) != 3 {\n\t\t\tt.Error("bad")\n\t\t}\n\t})\n}\n'
    )
    fixed = _repair_imports(broken, exe)
    assert '"fmt"' in fixed, f"repair did not add the missing import:\n{fixed}"
    assert "TestAdd" in fixed and "Add(1, 2)" in fixed, "repair altered the test body"
    # Must be a no-op on code that is already correct (never let the repair invent work).
    already = fixed
    assert _repair_imports(already, exe) == already, "repair is not idempotent"
    print("_repair_imports self-test: adds missing import, preserves body, idempotent OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")
    ap.add_argument("--adapter", default=None)
    ap.add_argument(
        "--bench", default=os.path.join(os.path.dirname(__file__), "data", "go_test_bench.jsonl")
    )
    ap.add_argument("--max-tokens", type=int, default=700)
    ap.add_argument("--best-of", type=int, default=1,
                    help="best-of-N (the ALGORITHM term): generate N candidates, CATCH if ANY "
                         "catches the bug. N>1 samples with temperature.")
    ap.add_argument("--temp", type=float, default=0.0,
                    help="sampling temperature (auto 0.6 when --best-of>1 and left at 0).")
    ap.add_argument("--select", choices=("oracle", "valid"), default="oracle",
                    help="candidate selector for --best-of: 'oracle' peeks at the planted "
                         "mutant (upper bound); 'valid' ships the first test that passes on "
                         "the code under test (realizable in a production loop).")
    ap.add_argument("--repair", choices=("none", "imports"), default="none",
                    help="deterministic repair applied to each candidate before scoring: "
                         "'imports' runs goimports, the cheapest ALGORITHM component and one "
                         "the real Builder loop already performs with a gate.")
    ap.add_argument("--save-generations", metavar="PATH",
                    help="write every candidate test + its two go-test outcomes to a JSONL, "
                         "so a later scoring change can be re-measured without a model run")
    ap.add_argument("--self-test", action="store_true",
                    help="run the model-free selector truth table and exit")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler

    model, tokenizer = load(args.model, adapter_path=args.adapter)
    # The mlx-community Qwen configs carry eos_token_id=<|endoftext|> only, so
    # generation never stops at <|im_end|> — tuned adapters (which stop emitting
    # <|endoftext|>) then ramble to max_tokens on every prompt. Register the
    # chat EOS explicitly so stopping works for base AND adapters.
    im_end = tokenizer.encode("<|im_end|>")
    if len(im_end) == 1:
        tokenizer.eos_token_ids.add(im_end[0])
    label = os.path.basename(args.adapter) if args.adapter else "BASE (untuned)"
    temp = args.temp if args.temp > 0 else (0.6 if args.best_of > 1 else 0.0)
    sampler = make_sampler(temp=temp) if temp > 0 else None
    tag = _tag(args.best_of, temp, args.select, args.repair)
    imports_exe = ""
    if args.repair == "imports":
        imports_exe = _goimports()
        if not imports_exe:
            # Silently skipping the repair would report a repair arm that never ran and
            # look like "the repair does not help" — the exact vacuous-green failure mode.
            raise SystemExit("--repair imports requested but goimports was not found")
    tasks = [json.loads(l) for l in open(args.bench)]
    print(f"mlx test-bench (mutation): {len(tasks)} tasks · model={label}\n")

    passed, valid_n, n_repaired, n_truncated, detail, saved = 0, 0, 0, 0, [], []
    for t in tasks:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": t["prompt"]}]
        prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        try:
            cands, texts = [], []
            for _ in range(args.best_of):
                gkw = {"max_tokens": args.max_tokens, "verbose": False}
                if sampler is not None:
                    gkw["sampler"] = sampler
                raw = generate(model, tokenizer, prompt=prompt, **gkw)
                n_truncated += _truncated(raw)
                test = extract_code(raw)
                if imports_exe:
                    repaired = _repair_imports(test, imports_exe)
                    n_repaired += repaired != test
                    test = repaired
                # Catches the bug iff it passes on correct AND fails on the mutant.
                passes = _go_test(t["metadata"]["correct"], test)
                cands.append((passes, passes and not _go_test(t["metadata"]["mutant"], test)))
                texts.append(test)
                # Stop as soon as this selector has its answer: a catch (oracle) or a
                # shippable test (valid). Anything after that can't change the verdict.
                if _verdict(cands, args.select) or (args.select == "valid" and cands[-1][0]):
                    break
            ok = _verdict(cands, args.select)
        except Exception as e:
            ok = False
            detail.append(f"{t['id']}:ERR({type(e).__name__})")
            continue
        passed += ok
        has_valid = _has_valid(cands)
        valid_n += has_valid
        # '+' caught · 'v' valid test but BLIND to the bug · '-' never produced a valid test
        detail.append(f"{'+' if ok else ('v' if has_valid else '-')}{t['id']}")
        if args.save_generations:
            saved.append({
                "id": t["id"], "label": label, "tag": tag, "verdict": ok, "has_valid": has_valid,
                "candidates": [
                    {"code": c, "passes_correct": p, "catches_mutant": k}
                    for c, (p, k) in zip(texts, cands)
                ],
            })

    n = len(tasks)
    rate = f"{passed}/{valid_n}" if valid_n else "n/a"
    print(f"{label} [{tag}]: bug-catch@{args.best_of} = {passed}/{n}  [{' '.join(detail)}]")
    print(f"  decomposition: valid-test {valid_n}/{n} · caught-given-valid {rate}"
          f"  (+caught v=blind -=invalid)")
    if imports_exe:
        # If the repair never fired, the arm is vacuous and its score means nothing.
        print(f"  repair: goimports changed {n_repaired} candidate(s)")
    if n_truncated:
        print(f"  WARNING: {n_truncated} candidate(s) hit --max-tokens ({args.max_tokens}) "
              f"mid-fence — raise it or this penalises verbose models")
    if args.save_generations:
        with open(args.save_generations, "w") as f:
            for row in saved:
                f.write(json.dumps(row) + "\n")
        print(f"  wrote {len(saved)} generations -> {args.save_generations} (re-scorable model-free)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
