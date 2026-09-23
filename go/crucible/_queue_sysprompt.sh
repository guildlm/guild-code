#!/bin/bash
# the system-prompt repair (PREREG-selftest-system-prompt-the-writer-was-told-to-fix.txt): D1 then D2, then the router on D1.
cd "$(dirname "$0")"
M=qwen3-coder:30b-32k
echo "[$(date '+%H:%M')] D1 FULL: exemplar + form-retry 1 + compile-retry + keep-tests"
python3 swe_bench_selftest_writer.py --model $M --compile-retry --keep-package-tests \
  --save data/go_swe_bench_v0_selftests_30b_sysprompt_full.jsonl > logs/sysprompt_d1.log 2>&1
echo "[$(date '+%H:%M')] D1: $(grep -c USEFUL logs/sysprompt_d1.log) USEFUL lines"
echo "[$(date '+%H:%M')] D2 BARE: no exemplar, no retries, keep-tests"
python3 swe_bench_selftest_writer.py --model $M --no-exemplar --form-retry 0 --keep-package-tests \
  --save data/go_swe_bench_v0_selftests_30b_sysprompt_bare.jsonl > logs/sysprompt_d2.log 2>&1
echo "[$(date '+%H:%M')] router, STRICT, D1 gate"
python3 swe_bench_router.py \
  --preferred data/go_swe_bench_v0_loop_qwen3-coder_30b-32k.selftest.jsonl \
  --alternate data/go_swe_bench_v0_loop_qwen2.5-coder_7b-32k.selftest.jsonl \
  --selftests data/go_swe_bench_v0_selftests_30b_sysprompt_full.jsonl \
  > logs/router_sysprompt.log 2>&1
echo "[$(date '+%H:%M')] ROUTER: $(grep 'ROUTER on' logs/router_sysprompt.log)"
echo "[$(date '+%H:%M')] queue done"
