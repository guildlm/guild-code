#!/bin/bash
# the compile-retry arm, stage 2: when the writer finishes, score it against the prereg and re-run the router.
cd "$(dirname "$0")"
while pgrep -f "swe_bench_selftest_writer.py --model qwen3-coder:30b-32k --compile-retry" > /dev/null; do sleep 20; done
echo "[$(date '+%H:%M')] writer done — scoring the compile-retry arm"
python3 compileretry_report.py > logs/compileretry_report.txt 2>&1
tail -26 logs/compileretry_report.txt
echo "[$(date '+%H:%M')] router, STRICT, compile-retry gate"
python3 swe_bench_router.py \
  --preferred data/go_swe_bench_v0_loop_qwen3-coder_30b-32k.selftest.jsonl \
  --alternate data/go_swe_bench_v0_loop_qwen2.5-coder_7b-32k.selftest.jsonl \
  --selftests data/go_swe_bench_v0_selftests_30b_compileretry.jsonl \
  > logs/router_compileretry.log 2>&1
echo "[$(date '+%H:%M')] ROUTER: $(grep 'ROUTER on' logs/router_compileretry.log)"
echo "[$(date '+%H:%M')] queue done"
