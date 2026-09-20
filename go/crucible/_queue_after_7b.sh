#!/bin/zsh
# 2026-09-20 — runs unattended after the 7B v0 draw (pid $1) exits, so a dead session cannot leave a draw
# unscored again. Stages: rescore 7B -> labelled 12k-token redraws of the truncated rows (both models) ->
# the registered algorithm arm on the 30B (PREREG-go-swe-bench-algorithm-arm-...). Every stage has its log.
cd /Users/fatihturker/Desktop/Personal/Dev/guildlm/guild-code/go/crucible || exit 1
PID=${1:-2377}
while kill -0 "$PID" 2>/dev/null; do sleep 30; done
echo "[$(date '+%H:%M')] stage 0: 7B draw (pid $PID) exited"
python3 swe_bench_rescore.py data/go_swe_bench_v0_qwen2.5-coder_7b-32k.jsonl > logs/swe_v0_7b_rescore.log 2>&1
echo "[$(date '+%H:%M')] stage 1: 7B rescored: $(tail -3 logs/swe_v0_7b_rescore.log | grep registered)"
IDS30=$(python3 -c "import json;r=json.load(open('data/go_swe_bench_v0_qwen3-coder_30b-32k.rescore.json'));print(','.join(k for k,v in r.items() if v['truncated']))")
IDS7=$(python3 -c "import json;r=json.load(open('data/go_swe_bench_v0_qwen2.5-coder_7b-32k.rescore.json'));print(','.join(k for k,v in r.items() if v['truncated']))")
echo "[$(date '+%H:%M')] stage 2: redraw truncated at 12k tokens — 30B: $IDS30 | 7B: $IDS7"
if [ -n "$IDS30" ]; then python3 swe_bench_eval.py --model qwen3-coder:30b-32k --bench data/go_swe_bench_v0_eval.jsonl --ids "$IDS30" --max-tokens 12000 --save data/go_swe_bench_v0_qwen3-coder_30b-32k.redraw12k.jsonl > logs/swe_v0_30b_redraw12k.log 2>&1; echo "[$(date '+%H:%M')] 30B redraw: $(grep pass@1 logs/swe_v0_30b_redraw12k.log)"; fi
if [ -n "$IDS7" ]; then python3 swe_bench_eval.py --model qwen2.5-coder:7b-32k --bench data/go_swe_bench_v0_eval.jsonl --ids "$IDS7" --max-tokens 12000 --save data/go_swe_bench_v0_qwen2.5-coder_7b-32k.redraw12k.jsonl > logs/swe_v0_7b_redraw12k.log 2>&1; echo "[$(date '+%H:%M')] 7B redraw: $(grep pass@1 logs/swe_v0_7b_redraw12k.log)"; fi
echo "[$(date '+%H:%M')] stage 3: algorithm arm, 30B, K=2"
python3 swe_bench_loop.py --model qwen3-coder:30b-32k --rounds 2 --max-tokens 6000 --save data/go_swe_bench_v0_loop_qwen3-coder_30b-32k.jsonl > logs/loop_30b_v0eval.log 2>&1
echo "[$(date '+%H:%M')] stage 3 done: $(grep 'ladder by' logs/loop_30b_v0eval.log)"
echo "[$(date '+%H:%M')] queue done"
