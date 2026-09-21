#!/bin/bash
# the form-retry arm, stage 2: when the writer finishes, score the arm and re-run the router
# on the SAME final files with the NEW gate. No new loop, so the router row isolates the gate.
cd "$(dirname "$0")"
while pgrep -f "swe_bench_selftest_writer.py --model qwen3-coder:30b-32k --form-retry" > /dev/null; do sleep 20; done
echo "[$(date '+%H:%M')] writer done — scoring the arm"
python3 formretry_report.py > logs/formretry_report.txt 2>&1
tail -20 logs/formretry_report.txt
echo "[$(date '+%H:%M')] router, STRICT, new gate"
python3 swe_bench_router.py \
  --preferred data/go_swe_bench_v0_loop_qwen3-coder_30b-32k.selftest.jsonl \
  --alternate data/go_swe_bench_v0_loop_qwen2.5-coder_7b-32k.selftest.jsonl \
  --selftests data/go_swe_bench_v0_selftests_30b_formretry.jsonl \
  > logs/router_formretry.log 2>&1
echo "[$(date '+%H:%M')] ROUTER: $(grep 'ROUTER on' logs/router_formretry.log)"
echo "[$(date '+%H:%M')] queue done"
