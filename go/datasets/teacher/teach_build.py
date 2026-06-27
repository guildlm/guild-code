"""Claude-as-teacher: author high-quality Go SFT pairs, compile-verify the code,
accumulate into a growing master dataset. $0, no API key, no rate limit.

go_generator examples are compiled with the real Go toolchain (drop if they fail).
reviewer/tester/explainer are authored by the teacher and kept as-is.
Runs are additive + deduped by instruction, so repeated batches accumulate.
"""
import hashlib, json, os, sys
sys.path.insert(0, "/Users/fatihturker/Desktop/Personal/Dev/guildlm/forge")
from src.core.verifier import GoVerifier
from src.core.dataset_builder import DatasetBuilder

OUT = "/Users/fatihturker/Desktop/Personal/Dev/guildlm/guild-code/go/datasets/code_guild_teacher_v1"
MASTER = f"{OUT}/code_guild_teacher_v1.train.jsonl"

# Imported from the batch file in the same dir.
from teach_examples import EXAMPLES  # noqa: E402


def main():
    ver = GoVerifier(strict=True)
    existing = []
    seen = set()
    for f in (f"{OUT}/code_guild_teacher_v1.train.jsonl", f"{OUT}/code_guild_teacher_v1.validation.jsonl"):
        if os.path.exists(f):
            for line in open(f):
                r = json.loads(line)
                existing.append(r)
                seen.add(hashlib.sha256(r["instruction"].encode()).hexdigest())

    kept_new, dropped, dups = [], 0, 0
    for ex in EXAMPLES:
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
                    print("     ", vr.diagnostics.strip().replace("\n", " ")[:160])
                continue
        seen.add(h)
        kept_new.append({"instruction": ex["instruction"], "response": ex["response"],
                         "context": ex.get("context", ""), "role": ex["role"]})

    allp = existing + kept_new
    print(f"\nnew authored: {len(EXAMPLES)} | kept: {len(kept_new)} | compile-dropped: {dropped} | dups: {dups}")
    print(f"master total now: {len(allp)}")

    b = DatasetBuilder(output_dir=OUT, system_prompt="You are a GuildLM Go specialist.")
    man = b.build(allp, name="code_guild_teacher_v1", val_ratio=0.1, seed=42, formats=["jsonl"])
    from collections import Counter
    roles = Counter(r.get("role", "?") for r in allp)
    print("by role:", dict(roles))
    print("manifest:", man.total_records, "records ->", OUT)


if __name__ == "__main__":
    main()
