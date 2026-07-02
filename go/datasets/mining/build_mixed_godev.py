# -*- coding: utf-8 -*-
"""Build the MIXED go-dev SFT dataset (greenfield generation + real mined edits).

Attempt #1 trained go-dev on PURE before->after edits -> it collapsed to the
"echo the whole file back" framing and REGRESSED greenfield generation
(unit bench 11/24 vs base 19). The user's #1 goal is go-dev writing large Go
backends *from scratch*, so greenfield capability must be protected.

Fix = MIX two prompt framings so the model keeps both skills:
  1. GREENFIELD  "Write a complete Go program that ..."   (verified teacher sets)
  2. EDIT        "Here is the file, apply this change ..." (real GitHub mined)

Both produce idiomatic Go as output; mixing the framings prevents the format
collapse while the mined edits inject real senior-Go feature/bugfix skill.

All rows are normalised to ONE unified system prompt and filtered to fit
mlx seq 2048 (<= MAX_CHARS combined). Greenfield is up-weighted (repeated) so
it stays a healthy fraction of what the ~1000-iter run actually samples.

Usage:
  python build_mixed_godev.py --out ../../../../.mlx-data-godev-mixed \
      --gf-reps 2 --gf-frac 0.45
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))

SYSTEM = ("You are GuildLM go-dev, an expert Go engineer. Write idiomatic, "
          "correct, complete Go. When code is requested, respond with Go code.")

# ~7800 chars total keeps a (system+user+assistant) example under seq 2048.
MAX_CHARS = 7800

# --- greenfield generation sources (write-from-spec, verified/teacher) ---
GREENFIELD = [
    os.path.join(_ROOT, ".mlx-data", "train.jsonl"),
    os.path.join(_ROOT, ".mlx-data", "valid.jsonl"),
    os.path.join(_HERE, "..", "specialists", "code_guild_go_dev",
                 "code_guild_go_dev.train.jsonl"),
    os.path.join(_HERE, "..", "code_guild_teacher_v1",
                 "code_guild_teacher_v1.train.jsonl"),
    os.path.join(_ROOT, "builder", "examples", "verified_contracts.jsonl"),
    os.path.join(_ROOT, "builder", "examples", "servemux_modern.jsonl"),
    os.path.join(_ROOT, "builder", "examples", "jsonapi_modern.jsonl"),
]

# --- edit sources (real GitHub git-history feature/bugfix/refactor) ---
# godev2048 = mined_dev+mined_bugfix already filtered to fit seq 2048.
EDITS = [
    os.path.join(_ROOT, ".mlx-data-mined", "godev2048", "train.jsonl"),
    os.path.join(_HERE, "..", "project_teacher",
                 "scaled_maintain_dev_examples.jsonl"),
    os.path.join(_HERE, "..", "project_teacher", "maintain_edit_pairs.jsonl"),
]


def to_messages(r: dict) -> list | None:
    """Normalise a row to [system,user,assistant] with the unified system prompt."""
    msgs = r.get("messages")
    if msgs:
        user = next((m["content"] for m in msgs if m["role"] == "user"), None)
        asst = next((m["content"] for m in msgs if m["role"] == "assistant"), None)
    else:
        user, asst = r.get("instruction"), r.get("response")
        ctx = r.get("context")
        if user and ctx:
            user = f"{user}\n\n{ctx}"
    if not user or not asst:
        return None
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": asst}]


def load(paths: list[str]) -> list[list]:
    out = []
    for p in paths:
        p = os.path.abspath(p)
        if not os.path.isfile(p):
            continue
        n = 0
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                m = to_messages(r)
                if not m:
                    continue
                total = sum(len(x["content"]) for x in m)
                if total > MAX_CHARS:
                    continue
                out.append(m)
                n += 1
        print(f"  loaded {n:>5}  {os.path.relpath(p, _ROOT)}")
    return out


def dedup(rows: list[list]) -> list[list]:
    seen, out = set(), []
    for m in rows:
        # key on user+assistant so differing system prompts don't defeat dedup
        payload = json.dumps([x for x in m if x["role"] != "system"],
                             sort_keys=True)
        h = hashlib.sha256(payload.encode("utf-8", "ignore")).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        out.append(m)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",
                    default=os.path.join(_ROOT, ".mlx-data-godev-mixed"))
    ap.add_argument("--gf-reps", type=int, default=2,
                    help="times to repeat the greenfield pool (up-weighting)")
    ap.add_argument("--gf-frac", type=float, default=0.45,
                    help="target greenfield fraction of the final train set")
    ap.add_argument("--valid-frac", type=float, default=0.03)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    rng = random.Random(args.seed)

    print("GREENFIELD sources:")
    gf = dedup(load(GREENFIELD))
    print("EDIT sources:")
    ed = dedup(load(EDITS))
    print(f"\nunique greenfield={len(gf)}  unique edits={len(ed)}")

    # hold out valid from each pool BEFORE repeating (no leakage)
    rng.shuffle(gf)
    rng.shuffle(ed)
    n_gf_val = max(2, int(len(gf) * args.valid_frac))
    n_ed_val = max(2, int(len(ed) * args.valid_frac))
    gf_val, gf_tr = gf[:n_gf_val], gf[n_gf_val:]
    ed_val, ed_tr = ed[:n_ed_val], ed[n_ed_val:]

    # up-weight greenfield, then size the edit pool to hit the target fraction
    gf_pool = gf_tr * args.gf_reps
    # gf_frac = |gf_pool| / (|gf_pool| + n_edits)  ->  n_edits
    n_edits = int(round(len(gf_pool) * (1 - args.gf_frac) / args.gf_frac))
    n_edits = min(n_edits, len(ed_tr))
    edits_used = ed_tr[:n_edits] if n_edits < len(ed_tr) else ed_tr

    train = gf_pool + edits_used
    rng.shuffle(train)
    valid = gf_val + ed_val
    rng.shuffle(valid)

    os.makedirs(args.out, exist_ok=True)
    for name, part in (("train", train), ("valid", valid)):
        with open(os.path.join(args.out, f"{name}.jsonl"), "w",
                  encoding="utf-8") as fh:
            for m in part:
                fh.write(json.dumps({"messages": m}) + "\n")

    frac = len(gf_pool) / len(train)
    print(f"\nWROTE {os.path.relpath(args.out, _ROOT)}:")
    print(f"  train={len(train)}  (greenfield {len(gf_pool)} @ {args.gf_reps}x "
          f"= {frac:.0%}, edits {len(edits_used)})")
    print(f"  valid={len(valid)}  (greenfield {len(gf_val)}, edits {len(ed_val)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
