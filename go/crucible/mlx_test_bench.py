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
import subprocess
import tempfile

MODULE = "sandbox"
_FENCE = re.compile(r"```(?:go|golang)?\s*\n(.*?)```", re.DOTALL)
SYSTEM = (
    "You are a Go test-writing specialist. Output one complete Go test file in a "
    "single ```go block, package sandbox, standard library testing only, no "
    "commentary. Do not redefine the function under test."
)


def extract_code(text: str) -> str:
    m = _FENCE.search(text)
    return (m.group(1) if m else text).strip() + "\n"


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


def _self_test() -> int:
    """Model-free truth table for _verdict — the selector is the whole experiment."""
    cases = [
        # (cands, oracle, valid)
        ([], False, False),
        ([(False, False)], False, False),
        ([(True, False)], False, False),
        ([(True, True)], True, True),
        # first valid candidate misses; a later one catches -> oracle sees it, valid ships the miss
        ([(True, False), (True, True)], True, False),
        # invalid candidates are skipped by both, then a catcher
        ([(False, False), (True, True)], True, True),
    ]
    for cands, want_oracle, want_valid in cases:
        got_o, got_v = _verdict(cands, "oracle"), _verdict(cands, "valid")
        assert got_o == want_oracle, f"oracle{cands}: {got_o} != {want_oracle}"
        assert got_v == want_valid, f"valid{cands}: {got_v} != {want_valid}"
    print(f"_verdict self-test: {len(cases)} cases OK (oracle >= valid on all)")
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
    tag = f"best-of-{args.best_of}@t{temp}/{args.select}" if args.best_of > 1 else "greedy"
    tasks = [json.loads(l) for l in open(args.bench)]
    print(f"mlx test-bench (mutation): {len(tasks)} tasks · model={label}\n")

    passed, detail = 0, []
    for t in tasks:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": t["prompt"]}]
        prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        try:
            cands = []
            for _ in range(args.best_of):
                gkw = {"max_tokens": args.max_tokens, "verbose": False}
                if sampler is not None:
                    gkw["sampler"] = sampler
                test = extract_code(generate(model, tokenizer, prompt=prompt, **gkw))
                # Catches the bug iff it passes on correct AND fails on the mutant.
                passes = _go_test(t["metadata"]["correct"], test)
                cands.append((passes, passes and not _go_test(t["metadata"]["mutant"], test)))
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
        detail.append(f"{'+' if ok else '-'}{t['id']}")

    print(f"{label} [{tag}]: bug-catch@{args.best_of} = {passed}/{len(tasks)}  [{' '.join(detail)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
