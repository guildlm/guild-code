#!/usr/bin/env python3
"""Publish a fused GuildLM Go specialist to the HuggingFace Hub.

Uploads, into one model repo:
  * the fused MLX/safetensors model (standalone — no separate adapter)
  * the GGUF quant (for `ollama run`), if present
  * the model card (README.md) and the Ollama Modelfile

Namespace: tries the `guildlm` org first (the GuildLM brand); if that repo can't
be created (the org doesn't exist yet / no access), it falls back to the
authenticated user's namespace and says so. HF orgs can only be created via the
website, so this keeps publishing un-blocked either way — the repo can be moved
to the org later from repo settings.

Usage:
    python publish.py --model go-dev \
        --fused ../../../.mlx-fused/go-dev \
        [--gguf ../../../.mlx-fused/go-dev/go-dev.Q4_K_M.gguf] \
        [--org guildlm] [--user fatihturker] [--private] [--dry-run]

$0 path: HuggingFace hosting is free.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _api():
    try:
        from huggingface_hub import HfApi
    except ImportError:
        sys.exit("pip install huggingface_hub")
    return HfApi()


def resolve_repo(api, model: str, org: str | None, user: str | None, dry_run: bool) -> str:
    """Pick owner/model. Prefer the org; fall back to the user if the org repo
    can't be created. Returns the repo_id that exists (or would, on dry-run)."""
    candidates = [o for o in (org, user) if o]
    if not candidates:
        candidates = [api.whoami()["name"]]
    for owner in candidates:
        repo_id = f"{owner}/{model}"
        if dry_run:
            print(f"[dry-run] would use {repo_id}")
            return repo_id
        try:
            api.create_repo(repo_id, repo_type="model", exist_ok=True)
            print(f"repo ready: {repo_id}")
            return repo_id
        except Exception as e:  # noqa: BLE001 — org may not exist / no perms
            print(f"  cannot use {repo_id}: {e}")
    sys.exit("no usable namespace (create the org on huggingface.co, or pass --user)")


def _render_card(card: Path, owner: str) -> str | None:
    """Substitute the {{NS}} namespace placeholder in the model card so the
    quickstart commands and sibling-model links point at the repo we actually
    publish to (the org if it exists, else the user). Returns rendered text."""
    if not card.exists():
        return None
    return card.read_text(encoding="utf-8").replace("{{NS}}", owner)


def upload(api, repo_id: str, fused: Path, gguf: Path | None, card: Path, modelfile: Path, dry_run: bool):
    owner = repo_id.split("/")[0]
    plan = []
    # model weights + tokenizer + config (the fused standalone model)
    for f in sorted(fused.iterdir()):
        if f.is_file() and f.name != "README.md":
            plan.append((f, f.name))
    if gguf and gguf.exists():
        plan.append((gguf, gguf.name))
    if modelfile.exists():
        plan.append((modelfile, "Modelfile"))

    for src, dest in plan:
        size = src.stat().st_size / 1e6
        if dry_run:
            print(f"[dry-run] upload {dest}  ({size:.1f} MB)")
            continue
        print(f"uploading {dest} ({size:.1f} MB) ...")
        api.upload_file(path_or_fileobj=str(src), path_in_repo=dest, repo_id=repo_id, repo_type="model")

    # README rendered with the resolved namespace (uploaded from memory)
    rendered = _render_card(card, owner)
    if rendered is not None:
        if dry_run:
            print(f"[dry-run] upload README.md  (rendered {{NS}}->{owner})")
        else:
            print(f"uploading README.md (rendered {{NS}}->{owner}) ...")
            api.upload_file(
                path_or_fileobj=rendered.encode("utf-8"),
                path_in_repo="README.md", repo_id=repo_id, repo_type="model",
            )
    print(("[dry-run] " if dry_run else "") + f"done: https://huggingface.co/{repo_id}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="go-dev | go-test | go-review")
    ap.add_argument("--fused", required=True, help="dir of the fused standalone model")
    ap.add_argument("--gguf", default=None, help="optional GGUF file to include")
    ap.add_argument("--org", default="guildlm")
    ap.add_argument("--user", default=None, help="fallback namespace if org unusable")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv[1:])

    here = Path(__file__).resolve().parent
    fused = Path(args.fused).resolve()
    if not fused.is_dir():
        sys.exit(f"fused dir not found: {fused}")
    card = here / args.model / "README.md"
    modelfile = here / args.model / "Modelfile"
    gguf = Path(args.gguf).resolve() if args.gguf else None

    api = _api()
    user = args.user or api.whoami()["name"]
    repo_id = resolve_repo(api, args.model, args.org, user, args.dry_run)
    upload(api, repo_id, fused, gguf, card, modelfile, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
