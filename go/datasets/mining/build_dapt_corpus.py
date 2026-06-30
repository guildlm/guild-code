# -*- coding: utf-8 -*-
"""Stage 3 of the GitHub Go mining pipeline — build the DAPT (continued-pretrain)
text corpus from the cloned repos.

This is the *knowledge* lever from the real-data recipe: a large, clean corpus
of real-world idiomatic Go (on top of the stdlib corpus we already had) for one
LoRA continued-pretraining pass that deepens the base's Go fluency, $0 on a free
Kaggle GPU.

Quality filtering (real GitHub is noisier than the stdlib):
  - skip vendor/, testdata/, node_modules/, .git/
  - skip machine-generated files (`// Code generated ... DO NOT EDIT.`, *.pb.go,
    zz_generated*.go, bindata.go, *.gen.go) — they teach codegen noise, not idiom
  - skip empty / pathologically large files
  - dedup by content hash across ALL repos (and optionally vs the stdlib corpus)
  - cap files-per-repo so one mega-repo can't dominate the mixture

Output: go_dapt_mined.jsonl of {"text", "source"} rows (same schema as the
stdlib go_corpus.jsonl, so anvil mode:pretrain consumes either/both), plus a
committed sample and a manifest.

Usage:
  python build_dapt_corpus.py
  python build_dapt_corpus.py --cap-per-repo 800 --merge-stdlib
  python build_dapt_corpus.py --sample 30
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CACHE = os.path.join(_HERE, "repos")
_STDLIB_CORPUS = os.path.join(_HERE, "..", "pretrain", "go_corpus.jsonl")

_SKIP_DIR_PARTS = (
    os.sep + "vendor" + os.sep,
    os.sep + "testdata" + os.sep,
    os.sep + "node_modules" + os.sep,
    os.sep + ".git" + os.sep,
    os.sep + "third_party" + os.sep,
)
_GENERATED_RE = re.compile(r"^//\s*Code generated .* DO NOT EDIT\.?\s*$", re.M)
_GENERATED_NAME = re.compile(
    r"(\.pb\.go|\.pb\.gw\.go|\.gen\.go|_generated\.go|^zz_generated|bindata\.go|"
    r"_string\.go|\.qtpl\.go)$"
)


def looks_generated(name: str, head: str) -> bool:
    if _GENERATED_NAME.search(name):
        return True
    if _GENERATED_RE.search(head):
        return True
    return False


def iter_repo_dirs(cache: str):
    for d in sorted(os.listdir(cache)):
        full = os.path.join(cache, d)
        if os.path.isdir(full) and os.path.isdir(os.path.join(full, ".git")):
            yield d, full


def iter_go_files(root: str, include_tests: bool):
    for dirpath, dirs, files in os.walk(root):
        if any(p in dirpath + os.sep for p in _SKIP_DIR_PARTS):
            dirs[:] = []
            continue
        # don't descend into .git
        if ".git" in dirs:
            dirs.remove(".git")
        for f in files:
            if not f.endswith(".go"):
                continue
            if not include_tests and f.endswith("_test.go"):
                continue
            yield os.path.join(dirpath, f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=_DEFAULT_CACHE)
    ap.add_argument("--out", default=os.path.join(_HERE, "go_dapt_mined.jsonl"))
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--cap-per-repo", type=int, default=1200,
                    help="max files kept per repo (0 = unlimited)")
    ap.add_argument("--max-chars", type=int, default=120_000)
    ap.add_argument("--min-chars", type=int, default=80,
                    help="skip trivially small files")
    ap.add_argument("--merge-stdlib", action="store_true",
                    help="also dedup against the existing stdlib go_corpus.jsonl")
    ap.add_argument("--sample", type=int, default=0)
    args = ap.parse_args()

    if not os.path.isdir(args.cache):
        sys.exit(f"no clone cache at {args.cache} — run clone_repos.py first")

    seen: set[str] = set()
    # Pre-seed dedup set with stdlib hashes so we never duplicate stdlib content.
    if args.merge_stdlib and os.path.isfile(_STDLIB_CORPUS):
        n = 0
        with open(_STDLIB_CORPUS, encoding="utf-8") as fh:
            for line in fh:
                try:
                    t = json.loads(line)["text"]
                except (json.JSONDecodeError, KeyError):
                    continue
                seen.add(hashlib.sha256(t.encode("utf-8", "ignore")).hexdigest())
                n += 1
        print(f"pre-seeded dedup with {n} stdlib docs")

    docs, total_chars = [], 0
    per_repo_kept: dict[str, int] = {}
    skipped = {"gen": 0, "dup": 0, "size": 0, "read": 0}

    for label, root in iter_repo_dirs(args.cache):
        kept = 0
        for path in iter_go_files(root, include_tests=not args.no_tests):
            if args.cap_per_repo and kept >= args.cap_per_repo:
                break
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    text = fh.read()
            except (OSError, UnicodeDecodeError):
                skipped["read"] += 1
                continue
            if len(text) < args.min_chars or len(text) > args.max_chars:
                skipped["size"] += 1
                continue
            if looks_generated(os.path.basename(path), text[:2000]):
                skipped["gen"] += 1
                continue
            h = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()
            if h in seen:
                skipped["dup"] += 1
                continue
            seen.add(h)
            rel = os.path.relpath(path, root)
            docs.append({"text": text, "source": f"{label}/{rel}"})
            total_chars += len(text)
            kept += 1
        per_repo_kept[label] = kept

    with open(args.out, "w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps(d) + "\n")

    est_tokens = total_chars // 4
    manifest = {
        "name": "go_dapt_mined_v1",
        "documents": len(docs),
        "total_chars": total_chars,
        "est_tokens": est_tokens,
        "include_tests": not args.no_tests,
        "repos": len(per_repo_kept),
        "skipped": skipped,
    }
    with open(os.path.join(_HERE, "corpus.manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)

    if args.sample:
        with open(os.path.join(_HERE, "go_dapt_mined.sample.jsonl"), "w") as fh:
            for d in docs[: args.sample]:
                fh.write(json.dumps(
                    {"text": d["text"][:1500], "source": d["source"]}) + "\n")

    print(f"\n{len(per_repo_kept)} repos -> {len(docs)} docs, "
          f"~{est_tokens/1e6:.1f}M tokens ({total_chars/1e6:.1f}M chars)")
    print(f"skipped: {skipped}")
    print(f"-> {args.out}")
    top = sorted(per_repo_kept.items(), key=lambda kv: kv[1], reverse=True)[:12]
    print("files kept per repo (top):")
    for label, n in top:
        print(f"  {n:5d}  {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
