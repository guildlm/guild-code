# -*- coding: utf-8 -*-
"""Build a $0 continued-pretraining corpus of canonical Go.

The GuildLM bet on deepening the base "for free": instead of scraping noisy,
mixed-license GitHub at scale (expensive + dirty), use the highest-signal Go that
already exists on disk — the **Go standard library source** ($GOROOT/src,
~5.6k files / ~2M lines of canonical, idiomatic, BSD-licensed Go) plus any
vendored idiomatic repos. This is a focused domain-adaptive-pretraining (DAPT)
corpus: a modest LoRA continued-pretraining pass over it on free Kaggle deepens
the base's Go idioms, no GPU bill for the data and no license risk.

The corpus is raw text documents ({"text", "source"}), one per .go file, deduped
by content hash. Test files are kept (they teach idiomatic testing too) but can
be excluded with --no-tests.

Usage:
    python build_pretrain_corpus.py                 # writes go_corpus.jsonl (gitignored)
    python build_pretrain_corpus.py --sample 25     # also writes a small committed sample
    python build_pretrain_corpus.py --no-tests
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def goroot_src() -> str | None:
    try:
        root = subprocess.run(
            ["go", "env", "GOROOT"], capture_output=True, text=True, timeout=20
        ).stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    src = os.path.join(root, "src")
    return src if os.path.isdir(src) else None


def extra_repo_roots() -> list[str]:
    """Idiomatic Go repos vendored on disk (best-effort; skipped if absent)."""
    base = os.path.abspath(os.path.join(_HERE, "../../../../forge/data/raw_test"))
    if not os.path.isdir(base):
        return []
    return [os.path.join(base, d) for d in sorted(os.listdir(base)) if os.path.isdir(os.path.join(base, d))]


def iter_go_files(root: str, include_tests: bool):
    for dirpath, _dirs, files in os.walk(root):
        # skip testdata / vendor noise
        if os.sep + "testdata" in dirpath or os.sep + "vendor" in dirpath:
            continue
        for f in files:
            if not f.endswith(".go"):
                continue
            if not include_tests and f.endswith("_test.go"):
                continue
            yield os.path.join(dirpath, f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-tests", action="store_true", help="exclude *_test.go files")
    ap.add_argument("--sample", type=int, default=0, help="also write N docs to a committed sample")
    ap.add_argument("--out", default=os.path.join(_HERE, "go_corpus.jsonl"))
    ap.add_argument("--max-chars", type=int, default=100_000, help="skip pathologically large files")
    args = ap.parse_args()

    src = goroot_src()
    if not src:
        sys.exit("Go toolchain / GOROOT/src not found")
    roots = [(src, "stdlib")] + [(r, os.path.basename(r)) for r in extra_repo_roots()]

    seen: set[str] = set()
    docs, total_chars = [], 0
    for root, label in roots:
        n = 0
        for path in iter_go_files(root, include_tests=not args.no_tests):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    text = fh.read()
            except (OSError, UnicodeDecodeError):
                continue
            if not text.strip() or len(text) > args.max_chars:
                continue
            h = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            rel = os.path.relpath(path, root)
            docs.append({"text": text, "source": f"{label}/{rel}"})
            total_chars += len(text)
            n += 1
        print(f"  {label}: {n} files")

    with open(args.out, "w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps(d) + "\n")

    est_tokens = total_chars // 4  # rough chars->tokens
    manifest = {
        "name": "go_pretrain_corpus_v1",
        "documents": len(docs),
        "total_chars": total_chars,
        "est_tokens": est_tokens,
        "include_tests": not args.no_tests,
        "sources": [label for _r, label in roots],
    }
    with open(os.path.join(_HERE, "corpus.manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)

    if args.sample:
        with open(os.path.join(_HERE, "go_corpus.sample.jsonl"), "w") as fh:
            for d in docs[: args.sample]:
                # trim the sample docs so the committed file stays small
                fh.write(json.dumps({"text": d["text"][:1500], "source": d["source"]}) + "\n")

    print(
        f"\ncorpus: {len(docs)} docs, ~{est_tokens/1e6:.1f}M tokens "
        f"({total_chars/1e6:.1f}M chars) -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
