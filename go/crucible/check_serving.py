#!/usr/bin/env python3
"""Pre-flight control for any SERVED A/B: prove the ports are actually different models.

WHY (FINDING-serving-adapter-noop.txt): `mlx_lm.server --adapter-path X` silently serves
the plain base — no error, no warning, HTTP 200 in the base's voice. A "specialist" port
that is really the base is invisible downstream: both arms answer, both look served, and
the A/B reports "no difference between base and specialist" — which happens to be this
project's expected headline. A measurement bug that CONFIRMS your hypothesis is the most
expensive kind, so the control runs BEFORE the experiment, not after.

The check is deliberately dumb and therefore hard to fool: send ONE prompt to every port
at temperature 0 and require the answers to be pairwise distinct. Two ports that are meant
to hold different models and return byte-identical text are not two models.

    python check_serving.py http://localhost:8080/v1=MODEL_ID http://localhost:8081/v1=MODEL_ID
    python check_serving.py --self-test      # no servers needed; proves the checker fires

Exit 0 iff every pair differs (or the self-test passes).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

PROBE = "Write a Go function ReverseRunes(s string) string. Code only."


def identical_pairs(outputs: dict[str, str]) -> list[tuple[str, str]]:
    """The pure core: which labelled outputs are byte-identical.

    Kept separate from the HTTP so the self-test can exercise the REAL comparison
    without a server — the same split verify_bench/check_contamination use.
    """
    labels = list(outputs)
    dupes = []
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            if outputs[a] == outputs[b]:
                dupes.append((a, b))
    return dupes


def ask(url: str, model: str, prompt: str = PROBE, max_tokens: int = 120) -> str:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        url.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=900) as resp:
        return json.load(resp)["choices"][0]["message"]["content"]


def self_test() -> int:
    """Plant the exact defect this checker exists to catch, plus a clean control."""
    failures = []

    # 1. The real bug shape: a "specialist" port echoing the base byte-for-byte.
    served = {":8080 base": "Certainly! Below is...", ":8081 specialist": "Certainly! Below is..."}
    if not identical_pairs(served):
        failures.append("MISSED the planted duplicate (adapter-noop shape)")

    # 2. Genuinely different models must NOT be flagged.
    ok = {":8080 base": "Certainly! Below is...", ":8081 specialist": "```go\npackage main"}
    if identical_pairs(ok):
        failures.append("FLAGGED two genuinely different models")

    # 3. Three ports, one duplicate pair — reports exactly that pair.
    three = {"a": "X", "b": "Y", "c": "X"}
    if identical_pairs(three) != [("a", "c")]:
        failures.append(f"wrong pair reported for 3 ports: {identical_pairs(three)}")

    # 4. Whitespace difference is a real difference (no normalising away evidence).
    if identical_pairs({"a": "X", "b": "X "}):
        failures.append("treated a whitespace-differing pair as identical")

    for f in failures:
        print(f"FAIL  {f}")
    print("OK — check_serving fires on a planted duplicate and stays quiet on real ones"
          if not failures else f"{len(failures)} self-test failure(s)")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ports", nargs="*", metavar="URL=MODEL",
                    help="one per fleet member, e.g. http://localhost:8081/v1=mlx-community/...")
    ap.add_argument("--self-test", action="store_true",
                    help="prove the checker fires, with no servers running")
    ap.add_argument("--prompt", default=PROBE)
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if len(args.ports) < 2:
        ap.error("need at least two URL=MODEL ports to compare (or --self-test)")

    outputs: dict[str, str] = {}
    for spec in args.ports:
        url, _, model = spec.partition("=")
        if not model:
            ap.error(f"expected URL=MODEL, got {spec!r}")
        print(f"probing {url} ({model}) ...", flush=True)
        outputs[url] = ask(url, model, args.prompt)

    dupes = identical_pairs(outputs)
    for a, b in dupes:
        print(f"FAIL  {a} and {b} returned BYTE-IDENTICAL text — same model on both ports.")
        print("      If one was meant to carry a LoRA adapter, it is not applied; serve it")
        print("      with serve_adapter.py (see FINDING-serving-adapter-noop.txt).")
    if dupes:
        return 1
    print(f"OK — all {len(outputs)} ports returned distinct text; they are different models.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
