# -*- coding: utf-8 -*-
"""Export per-specialist Go datasets from the teacher-authored batches.

The combined `code_guild_teacher_v1` dataset mixes all four roles. To train
*dedicated single-purpose* Go specialists (the GuildLM thesis: a narrow 7-14B
Go model beats a general LLM because no Go-specific model that size exists), we
need one clean dataset per role:

    go_generator -> code_guild_go_dev      (the Go *development* specialist)
    go_tester    -> code_guild_go_test     (the Go *test-writing* specialist)
    go_reviewer  -> code_guild_go_review   (the Go *code-review* specialist)
    go_explainer -> code_guild_go_explain  (bonus: the Go *explain* specialist)

Same loader + compile-verifier + DatasetBuilder as `teach_build.py`, so each
split is format-identical to the combined set and consumable by anvil unchanged.
Only `go_generator` responses are compile-verified (they are complete programs);
the other roles reference external code and are kept as authored (judged later by
crucible's llm_judge), per the quality-gate lesson.

Usage (from this directory, with a forge checkout available):
    python export_role_splits.py
"""
import glob
import hashlib
import importlib.util
import os
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
for cand in (
    os.environ.get("FORGE_DIR", ""),
    os.path.join(_HERE, "../../../../forge"),
    "/Users/fatihturker/Desktop/Personal/Dev/guildlm/forge",
):
    if cand and os.path.isdir(os.path.join(cand, "src", "core")):
        sys.path.insert(0, os.path.abspath(cand))
        break

from src.core.dataset_builder import DatasetBuilder  # noqa: E402
from src.core.verifier import GoVerifier  # noqa: E402

# role -> (dataset name, the specialist it trains)
SPLITS = {
    "go_generator": ("code_guild_go_dev", "Go development specialist"),
    "go_tester": ("code_guild_go_test", "Go test-writing specialist"),
    "go_reviewer": ("code_guild_go_review", "Go code-review specialist"),
    "go_explainer": ("code_guild_go_explain", "Go explanation specialist"),
}
OUT_ROOT = os.path.abspath(os.path.join(_HERE, "..", "specialists"))


def load_batches():
    examples = []
    for path in sorted(glob.glob(os.path.join(_HERE, "teach_examples*.py"))):
        spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        examples.extend(getattr(mod, "EXAMPLES", []))
    return examples


def main():
    ver = GoVerifier(strict=True)
    examples = load_batches()

    # Partition by role, compile-verifying generators and deduping per role.
    by_role: dict[str, list] = {r: [] for r in SPLITS}
    seen: set[str] = set()
    dropped = dups = 0
    for ex in examples:
        role = ex.get("role")
        if role not in SPLITS:
            continue
        h = hashlib.sha256(ex["instruction"].encode()).hexdigest()
        if h in seen:
            dups += 1
            continue
        if role == "go_generator":
            vr = ver.verify(ex["response"], role="go_generator")
            if not vr.passed:
                dropped += 1
                continue
        seen.add(h)
        by_role[role].append(
            {
                "instruction": ex["instruction"],
                "response": ex["response"],
                "context": ex.get("context", ""),
                "role": role,
            }
        )

    print(f"authored: {len(examples)} | compile-dropped: {dropped} | dups: {dups}")
    print("by role:", {r: len(v) for r, v in by_role.items()})

    for role, (name, who) in SPLITS.items():
        rows = by_role[role]
        if not rows:
            print(f"  SKIP {name}: no rows")
            continue
        out = os.path.join(OUT_ROOT, name)
        # Tiny splits can't spare 10% for validation; scale the ratio down.
        val_ratio = 0.1 if len(rows) >= 20 else 0.0
        b = DatasetBuilder(
            output_dir=out,
            system_prompt=f"You are a GuildLM {who}. Respond with Go only when code is requested.",
        )
        man = b.build(rows, name=name, val_ratio=val_ratio, seed=42, formats=["jsonl"])
        print(
            f"  {name}: {man.total_records} records "
            f"(train={man.splits.get('train')}, val={man.splits.get('validation', 0)}) -> {out}"
        )


if __name__ == "__main__":
    main()
