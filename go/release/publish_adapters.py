#!/usr/bin/env python3
"""Publish the whole LoRA-adapter archive (+ the Kaggle DAPT checkpoints) to one HF repo.

Why one repo: the adapters are the *learned* artefacts behind the fused specialists and
they are tiny (5.5 GB for 43 of them vs 8.4 GB for ONE fused model). Publishing the
archive lets the local fused copies (57 GB) be deleted without losing anything: any fused
model is `mlx_lm.fuse(base, adapter)`, which is deterministic.

Usage:
    python publish_adapters.py [--adapters ../../../.mlx-adapters] [--kaggle ../../../.kaggle-dapt]
                               [--org guildlm] [--user fatihturker] [--repo go-lora-adapters]
                               [--dry-run] [--verify-only]

--verify-only re-lists the remote repo and checks every local file is present with the
same size (the deletion gate: nothing local is removed until this passes).
$0 path: HuggingFace hosting is free.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

IGNORE = ["*.bak", ".DS_Store", "__pycache__/*"]


def _api():
    try:
        from huggingface_hub import HfApi
    except ImportError:
        sys.exit("pip install huggingface_hub")
    return HfApi()


def inventory(adapters: Path) -> str:
    """Markdown table of every adapter: base, data, iters, rank, lr — read from its config."""
    rows = []
    for d in sorted(p for p in adapters.iterdir() if p.is_dir()):
        cfg = d / "adapter_config.json"
        if not cfg.exists():
            continue
        c = json.loads(cfg.read_text())
        lp = c.get("lora_parameters", {}) or {}
        data = Path(c.get("data") or "").name or "—"
        base = (c.get("model") or "—").replace("mlx-community/", "")
        ckpts = sorted(p.name for p in d.glob("*_adapters.safetensors"))
        final = "yes" if (d / "adapters.safetensors").exists() else "**no final**"
        rows.append(
            f"| `{d.name}` | {base} | `{data}` | {c.get('iters', '—')} | "
            f"{lp.get('rank', '—')} | {c.get('learning_rate', '—')} | {final} | {len(ckpts)} |"
        )
    head = (
        "## Adapter inventory (from each `adapter_config.json`)\n\n"
        "| adapter | base | data dir | iters | rank | lr | final weights | kept checkpoints |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )
    return head + "\n".join(rows) + "\n"


def local_files(root: Path, prefix: str) -> dict[str, int]:
    out = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if p.suffix == ".bak" or p.name == ".DS_Store" or "__pycache__" in rel:
            continue
        out[f"{prefix}/{rel}"] = p.stat().st_size
    return out


def verify(api, repo_id: str, expected: dict[str, int]) -> bool:
    info = api.model_info(repo_id, files_metadata=True)
    remote = {s.rfilename: (s.size or 0) for s in info.siblings}
    missing = [k for k in expected if k not in remote]
    wrong = [k for k in expected if k in remote and remote[k] != expected[k]]
    print(f"remote files: {len(remote)}   expected: {len(expected)}   "
          f"missing: {len(missing)}   size-mismatch: {len(wrong)}")
    for k in missing[:20]:
        print("  MISSING", k)
    for k in wrong[:20]:
        print("  SIZE   ", k, expected[k], "!=", remote[k])
    return not missing and not wrong


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapters", default=str(here / "../../../.mlx-adapters"))
    ap.add_argument("--kaggle", default=str(here / "../../../.kaggle-dapt"))
    ap.add_argument("--org", default="guildlm")
    ap.add_argument("--user", default=None)
    ap.add_argument("--repo", default="go-lora-adapters")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify-only", action="store_true")
    a = ap.parse_args()

    adapters, kaggle = Path(a.adapters).resolve(), Path(a.kaggle).resolve()
    if not adapters.is_dir():
        sys.exit(f"no adapters dir: {adapters}")
    api = _api()
    owner = a.org or a.user or api.whoami()["name"]
    repo_id = f"{owner}/{a.repo}"

    expected = local_files(adapters, "adapters")
    if kaggle.is_dir():
        expected.update(local_files(kaggle, "kaggle-dapt"))
    total_gb = sum(expected.values()) / 1e9
    print(f"repo {repo_id}: {len(expected)} files, {total_gb:.2f} GB")

    if a.verify_only:
        return 0 if verify(api, repo_id, expected) else 1

    card = (here / "go-lora-adapters" / "README.md").read_text(encoding="utf-8")
    card = card.replace("{{NS}}", owner).replace("<!-- INVENTORY -->", inventory(adapters))

    if a.dry_run:
        print(card[:1500])
        print(f"[dry-run] would upload {len(expected)} files ({total_gb:.2f} GB) to {repo_id}")
        return 0

    api.create_repo(repo_id, repo_type="model", exist_ok=True)
    print("repo ready:", repo_id)
    api.upload_file(path_or_fileobj=card.encode("utf-8"), path_in_repo="README.md",
                    repo_id=repo_id, repo_type="model", commit_message="model card")
    print("uploading adapters/ ...")
    api.upload_folder(folder_path=str(adapters), path_in_repo="adapters", repo_id=repo_id,
                      repo_type="model", ignore_patterns=IGNORE,
                      commit_message="all GuildLM Go LoRA adapters (MLX)")
    if kaggle.is_dir():
        print("uploading kaggle-dapt/ ...")
        api.upload_folder(folder_path=str(kaggle), path_in_repo="kaggle-dapt", repo_id=repo_id,
                          repo_type="model", ignore_patterns=IGNORE,
                          commit_message="Kaggle DAPT checkpoints (HF-PEFT) and dataset bundles")
    print("upload done; verifying ...")
    ok = verify(api, repo_id, expected)
    print("VERIFY", "OK" if ok else "FAILED")
    print(f"https://huggingface.co/{repo_id}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
