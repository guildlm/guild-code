#!/usr/bin/env python3
"""Build the REPLAY-MIX DAPT corpus — recipe 2 of DAPT-on-Kaggle.

Recipe 1 (pure next-token on raw Go over the INSTRUCT base) measurably damaged
chat behaviour: after 300-600 steps the model stops emitting <|im_end|> and
closing fences, rambles endless Go, and — even after a full mixed SFT on top —
fails every project-level Builder run (4 runs, 4 distinct instruction-following
collapses; unit bench merely flat). The standard fix is REPLAY: interleave a
slice of chat-FORMATTED data into the pretraining stream so the chat special
tokens stay in-distribution while the model absorbs the raw-Go knowledge.

This script renders instruct examples ({"messages": [...]} JSONL, the exact SFT
sets we already trust) through the model's own chat template into plain `text`
docs and shuffles them into go_dapt_core.jsonl at a target token fraction.

Usage:
  python build_dapt_replay.py \
      --core go_dapt_core.jsonl \
      --chat ~/.../.mlx-data-godev-mixed2/train.jsonl \
      --chat ~/.../.mlx-data-mined/godev2048/train.jsonl \
      --frac 0.12 --out go_dapt_replay.jsonl

Token counts are approximated at 3.5 chars/token (Go-heavy text); the replay
slice is repeated as needed (replay data repeating a few times within one DAPT
pass is standard and harmless).
"""
import argparse
import json
import random

CHARS_PER_TOKEN = 3.5
BASE = "Qwen/Qwen2.5-Coder-7B-Instruct"


def render_chat(messages, tokenizer) -> str:
    return tokenizer.apply_chat_template(messages, tokenize=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True, help="raw-Go DAPT corpus ({'text'} JSONL)")
    ap.add_argument("--chat", action="append", required=True,
                    help="chat SFT JSONL ({'messages'}); repeatable")
    ap.add_argument("--frac", type=float, default=0.12,
                    help="target REPLAY fraction of total tokens (default 0.12)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(BASE)

    core = [json.loads(l) for l in open(args.core)]
    core_chars = sum(len(r["text"]) for r in core)

    chat_docs = []
    for path in args.chat:
        for line in open(path):
            msgs = json.loads(line)["messages"]
            chat_docs.append({"text": render_chat(msgs, tok), "source": f"replay:{path.rsplit('/', 2)[-2]}"})
    chat_chars_once = sum(len(d["text"]) for d in chat_docs)

    # replay/(replay+core) = frac  ->  replay_chars = core_chars * frac/(1-frac)
    want_chars = core_chars * args.frac / (1.0 - args.frac)
    repeats = max(1, round(want_chars / max(1, chat_chars_once)))
    replay = chat_docs * repeats

    rng = random.Random(args.seed)
    mixed = core + replay
    rng.shuffle(mixed)

    with open(args.out, "w") as fh:
        for r in mixed:
            fh.write(json.dumps({"text": r["text"], "source": r.get("source", "core")}) + "\n")

    total_chars = core_chars + chat_chars_once * repeats
    print(f"core   : {len(core)} docs, ~{core_chars/CHARS_PER_TOKEN/1e6:.1f}M tokens")
    print(f"replay : {len(chat_docs)} docs x{repeats}, ~{chat_chars_once*repeats/CHARS_PER_TOKEN/1e6:.1f}M tokens "
          f"({chat_chars_once*repeats/total_chars:.1%} of stream)")
    print(f"out    : {args.out} ({len(mixed)} docs, ~{total_chars/CHARS_PER_TOKEN/1e6:.1f}M tokens)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
