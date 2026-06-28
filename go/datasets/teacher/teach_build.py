"""Claude-as-teacher: assemble teacher-authored Go SFT pairs, compile-verify the
code examples, accumulate into a growing master dataset. $0, no API key, no limit.

Reads every ``teach_examples*.py`` in this directory (each defines ``EXAMPLES``),
compiles each ``go_generator`` response with the real Go toolchain (drops any that
fail), dedupes by instruction, and rebuilds the dataset. Additive across batches.

Usage (from this directory, with a forge checkout available):
    python teach_build.py
"""
import glob
import hashlib
import importlib.util
import os
import re
import subprocess
import sys

_FENCE = re.compile(r"```(?:go|golang)?\s*\n(.*?)```", re.DOTALL)


def _gofmt_syntax_ok(response: str) -> bool:
    """Syntax-check a teacher response's first Go block with gofmt.

    go_tester examples are complete files but aren't compile-verified (they
    reference external code), so authoring typos (a missing paren) would slip
    into the training data. gofmt parses without type-checking, catching syntax
    errors while tolerating undefined symbols.
    """
    m = _FENCE.search(response)
    if not m:
        return True
    try:
        proc = subprocess.run(
            ["gofmt", "-e"], input=m.group(1), capture_output=True, text=True, timeout=20
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True
    return proc.returncode == 0

# Locate a forge checkout so we can reuse its verifier + dataset builder.
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

OUT = os.path.abspath(os.path.join(_HERE, "..", "code_guild_teacher_v1"))
NAME = "code_guild_teacher_v1"


def load_batches():
    examples = []
    for path in sorted(glob.glob(os.path.join(_HERE, "teach_examples*.py"))):
        spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        batch = getattr(mod, "EXAMPLES", [])
        examples.extend(batch)
        print(f"  loaded {len(batch):3d} from {os.path.basename(path)}")
    return examples


def main():
    ver = GoVerifier(strict=True)
    examples = load_batches()

    kept, seen, dropped, dups = [], set(), 0, 0
    for ex in examples:
        h = hashlib.sha256(ex["instruction"].encode()).hexdigest()
        if h in seen:
            dups += 1
            continue
        if ex["role"] == "go_generator":
            vr = ver.verify(ex["response"], role="go_generator")
            if not vr.passed:
                dropped += 1
                print(f"  DROP (compile {vr.status}): {ex['instruction'][:60]}...")
                if vr.diagnostics:
                    print("     ", vr.diagnostics.strip().replace(chr(10), " ")[:160])
                continue
        elif ex["role"] == "go_tester" and not _gofmt_syntax_ok(ex["response"]):
            # Tester files aren't compile-verified, but they must at least parse.
            dropped += 1
            print(f"  DROP (tester syntax): {ex['instruction'][:60]}...")
            continue
        seen.add(h)
        kept.append({
            "instruction": ex["instruction"],
            "response": ex["response"],
            "context": ex.get("context", ""),
            "role": ex["role"],
        })

    print(f"\nauthored: {len(examples)} | kept: {len(kept)} | compile-dropped: {dropped} | dups: {dups}")

    b = DatasetBuilder(output_dir=OUT, system_prompt="You are a GuildLM Go specialist.")
    man = b.build(kept, name=NAME, val_ratio=0.1, seed=42, formats=["jsonl"])

    from collections import Counter
    roles = Counter(r["role"] for r in kept)
    print("by role:", dict(roles))
    print(f"dataset: {man.total_records} records "
          f"(train={man.splits.get('train')}, val={man.splits.get('validation')}) -> {OUT}")


if __name__ == "__main__":
    main()
