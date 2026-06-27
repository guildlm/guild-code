#!/usr/bin/env python3
"""Build the Code Guild *sample* SFT dataset by running forge OFFLINE.

This script drives forge's real pipeline (process -> generate -> build) over the
curated Go snippets in ``sources/`` to produce a small, deterministic SFT
dataset plus a manifest under ``code_guild_sample_v1/``.

It uses forge's **offline** ``InstructionGenerator``, so the responses are
deterministic synthetic *placeholders* (``[offline:<role>:<seed>] ...``), not
teacher-grade training labels. The dataset exists to smoke-test the data ->
train pipeline end-to-end with no network, GPU, or teacher endpoint.

Run it with forge's virtualenv interpreter::

    /path/to/forge/.venv/bin/python build_sample.py

or simply ``python build_sample.py`` from within an activated forge venv.
"""

from __future__ import annotations

import json
import os
import sys

# --------------------------------------------------------------------------- #
# Locate the forge repo and make its `src` package importable.
# --------------------------------------------------------------------------- #
HERE = os.path.dirname(os.path.abspath(__file__))
# guild-code/go/datasets -> guild-code/go/datasets/../../..  == repo parent dir
GUILDLM_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FORGE_ROOT = os.environ.get("FORGE_ROOT", os.path.join(GUILDLM_ROOT, "forge"))
if FORGE_ROOT not in sys.path:
    sys.path.insert(0, FORGE_ROOT)

from src.core.dataset_builder import DatasetBuilder  # noqa: E402
from src.core.instruction_gen import InstructionGenerator  # noqa: E402
from src.core.processor import Processor  # noqa: E402

# --------------------------------------------------------------------------- #
# Configuration (kept in sync with go/forge/*.yaml conventions).
# --------------------------------------------------------------------------- #
SOURCES_DIR = os.path.join(HERE, "sources")
DATASET_NAME = "code_guild_sample_v1"
OUTPUT_DIR = os.path.join(HERE, DATASET_NAME)

# All four Go specialist roles registered in forge's ROLE_REGISTRY.
ROLES = ["go_explainer", "go_reviewer", "go_generator", "go_tester"]

# These curated snippets are our own permissively-licensed examples.
SOURCE_LICENSE = "Apache-2.0"

# A fixed seed makes the train/validation split deterministic.
SEED = 42
VAL_RATIO = 0.1

SYSTEM_PROMPT = "You are a GuildLM Go specialist."


def main() -> None:
    # 1. PROCESS: extract + clean the curated Go snippets.
    #    We pass a minimal exclude set (instead of forge's DEFAULT_EXCLUDES) so
    #    that the idiomatic `*_test.go` table-driven example is *kept*.
    processor = Processor(
        include_extensions=[".go"],
        exclude_patterns=["vendor/", "node_modules/", ".git/"],
        min_length=200,
        max_length=50_000,
        near_dup_threshold=0.85,
        allow_unknown_license=True,
    )
    raw_docs = list(processor.process_repository(SOURCES_DIR, license=SOURCE_LICENSE))
    docs, stats = processor.clean(raw_docs)
    docs.sort(key=lambda d: d["file_path"])  # stable, reproducible ordering
    print(f"processed {stats.total_in} -> {stats.total_out} clean documents")

    # 2. GENERATE: deterministic OFFLINE synthetic pairs, one per (doc, role).
    generator = InstructionGenerator(offline=True)
    pairs: list[dict] = []
    for doc in docs:
        for role in ROLES:
            # normalize() keeps only instruction/response/context, so we don't
            # attach extra keys here -- they would be dropped by the builder.
            pairs.extend(generator.generate_pairs(doc["content"], role=role, max_pairs=1))
    print(f"generated {len(pairs)} instruction/response pairs across {len(ROLES)} roles")

    # 3. BUILD: validate, deterministically split, and export JSONL + manifest.
    builder = DatasetBuilder(output_dir=OUTPUT_DIR, system_prompt=SYSTEM_PROMPT)
    manifest = builder.build(
        pairs,
        name=DATASET_NAME,
        val_ratio=VAL_RATIO,
        seed=SEED,
        formats=["jsonl"],
        source_stats={
            "cleaning": stats.to_dict(),
            "roles": ROLES,
            "source_files": [d["file_path"] for d in docs],
            "generation": "forge offline (deterministic synthetic placeholders)",
            "seed": SEED,
        },
    )

    print(f"built {manifest.total_records} records -> {OUTPUT_DIR}")
    print(json.dumps(manifest.to_dict()["splits"], indent=2))


if __name__ == "__main__":
    main()
