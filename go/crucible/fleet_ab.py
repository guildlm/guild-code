#!/usr/bin/env python3
"""Project-scale A/B: base-only Builder vs base-first fleet routing, on the same spec.

This is the harness behind RESULT-fleet-ab.txt. It exists so the headline routing result is
REPRODUCIBLE rather than a one-off shell invocation.

WHAT MAKES IT CAUSAL: both arms use the same spec, the same fix-round budget, and the same
base model on the same port. The ONLY intervention is whether --fleet is passed. The Builder's
coder is deterministic per (prompt, temperature), so the arms are BYTE-IDENTICAL until the
first escalation fires — every file that ends up differing is the routing's own footprint.

BEFORE RUNNING, verify the fleet ports really hold different models:
    python check_serving.py URL=MODEL URL=MODEL ...
`mlx_lm.server --adapter-path` silently serves the base (FINDING-serving-adapter-noop.txt),
which would make both arms the same model and report "routing does nothing".

    python fleet_ab.py --spec ../../../builder/specs/shortener.yaml \
        --base-url http://localhost:8080/v1 --model M7 \
        --fleet 'M7@http://localhost:8081/v1,M14@http://localhost:8082/v1' --out /tmp/ab
    python fleet_ab.py --report /tmp/ab/shortener        # score + divergence, no model calls
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILDER = HERE.parent.parent.parent / "builder"


def verdict(base: int | None, fleet: int | None) -> str:
    """The pure core: what a (base, fleet) score pair means. Separated so --self-test can
    exercise the real interpretation without running a model (the crucible convention)."""
    if base is None or fleet is None:
        return "INCOMPLETE"
    if fleet > base:
        return "ROUTING WINS"
    if fleet < base:
        return "ROUTING REGRESSES"
    return "NO DIFFERENCE"


def score_of(project: Path) -> dict:
    if not project.is_dir():
        return {}
    p = subprocess.run([str(BUILDER / ".venv/bin/python"), str(BUILDER / "score_backend.py"),
                        str(project), "--json"], capture_output=True, text=True, timeout=900)
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {}


def run_arm(spec: Path, out: Path, base_url: str, model: str,
            rounds: int, fleet: str | None) -> dict:
    log = out.with_suffix(".log")
    cmd = [str(BUILDER / ".venv/bin/guildlm-build"), "main", "--spec", str(spec),
           "--out", str(out), "--base-url", base_url, "--model", model,
           "--max-fix-rounds", str(rounds)]
    if fleet:
        cmd += ["--fleet", fleet]
    started = time.time()
    with open(log, "w") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode
    text = log.read_text(errors="replace")
    return {
        "rc": rc,
        "secs": round(time.time() - started),
        "escalations": text.count("escalating"),
        "fix_rounds": text.count("fix round"),
        "score": score_of(out),
    }


def report(pair_dir: Path) -> int:
    base, fleet = pair_dir.with_name(pair_dir.name + "-base"), pair_dir.with_name(pair_dir.name + "-fleet")
    sb, sf = score_of(base), score_of(fleet)
    b, f = sb.get("score"), sf.get("score")
    print(f"base : {b}/{sb.get('max')}  { {k: v['ok'] for k, v in sb.get('stages', {}).items()} }")
    print(f"fleet: {f}/{sf.get('max')}  { {k: v['ok'] for k, v in sf.get('stages', {}).items()} }")
    if base.is_dir() and fleet.is_dir():
        d = subprocess.run(["diff", "-rq", str(base), str(fleet)], capture_output=True, text=True)
        changed = [ln for ln in d.stdout.splitlines() if ln.strip()]
        print(f"diverged files: {len(changed)}  (the routing's causal footprint)")
        for ln in changed:
            print("  " + ln)
    print(f"VERDICT: {verdict(b, f)}")
    return 0


def self_test() -> int:
    failures = []
    if verdict(2, 3) != "ROUTING WINS":
        failures.append("did not call a red->green improvement a win")
    if verdict(3, 2) != "ROUTING REGRESSES":
        failures.append("did not call a green->red change a regression")
    if verdict(3, 3) != "NO DIFFERENCE":
        failures.append("did not call equal scores a tie")
    if verdict(None, 3) != "INCOMPLETE":
        failures.append("scored a missing arm instead of reporting INCOMPLETE")
    for f in failures:
        print(f"FAIL  {f}")
    print("OK — fleet_ab verdict logic is correct on all four outcomes"
          if not failures else f"{len(failures)} self-test failure(s)")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec")
    ap.add_argument("--out", default="/tmp/fleet-ab")
    ap.add_argument("--base-url", default="http://localhost:8080/v1")
    ap.add_argument("--model")
    ap.add_argument("--fleet", help="'model@url,model@url' — the escalation members")
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--report", help="score an already-run pair: <out>/<specname>")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.report:
        return report(Path(args.report))
    if not (args.spec and args.model and args.fleet):
        ap.error("need --spec, --model and --fleet (or --report / --self-test)")

    spec = Path(args.spec).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    stem = out / spec.stem
    results = {}
    for arm, fleet in (("base", None), ("fleet", args.fleet)):
        target = stem.with_name(stem.name + f"-{arm}")
        print(f"=== {spec.stem}/{arm} ...", flush=True)
        results[arm] = run_arm(spec, target, args.base_url, args.model, args.rounds, fleet)
        r = results[arm]
        print(f"    rc={r['rc']} secs={r['secs']} escalations={r['escalations']} "
              f"score={r['score'].get('score')}/{r['score'].get('max')}", flush=True)
    print()
    return report(stem)


if __name__ == "__main__":
    sys.exit(main())
