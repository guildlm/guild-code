#!/bin/bash
# the exemplar arm, stage 2: when the writer finishes, score it against the prereg and re-run the router.
cd "$(dirname "$0")"
while pgrep -f "swe_bench_selftest_writer.py --model qwen3-coder:30b-32k --exemplar" > /dev/null; do sleep 20; done
echo "[$(date '+%H:%M')] writer done — scoring the exemplar arm"
python3 exemplar_report.py > logs/exemplar_report.txt 2>&1
tail -26 logs/exemplar_report.txt
echo "[$(date '+%H:%M')] router, STRICT, exemplar gate"
python3 swe_bench_router.py \
  --preferred data/go_swe_bench_v0_loop_qwen3-coder_30b-32k.selftest.jsonl \
  --alternate data/go_swe_bench_v0_loop_qwen2.5-coder_7b-32k.selftest.jsonl \
  --selftests data/go_swe_bench_v0_selftests_30b_exemplar.jsonl \
  > logs/router_exemplar.log 2>&1
echo "[$(date '+%H:%M')] ROUTER: $(grep 'ROUTER on' logs/router_exemplar.log)"
echo "[$(date '+%H:%M')] queue done"
