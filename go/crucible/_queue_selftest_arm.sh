#!/bin/zsh
# 2026-09-20 night — the SELF-TEST ARM, unattended (launch only AFTER the prereg is committed):
#   stage 1: 30B loop, K=2, self-test feedback, --no-peek   (r0 = plain edit form, r1/r2 = with the self-test)
#   stage 2: 7B  loop, same harness                          (its r0 = the 7B edit-form row)
#   stage 3: router: 30B preferred, 7B alternate, gate = the 30B's kept self-tests (hidden tests judge)
cd /Users/fatihturker/Desktop/Personal/Dev/guildlm/guild-code/go/crucible || exit 1
ST=data/go_swe_bench_v0_selftests_qwen3-coder_30b-32k.rescored.jsonl
while pgrep -f "swe_bench_selftest_writer.py --model qwen3-coder" >/dev/null; do sleep 30; done
echo "[$(date '+%H:%M')] stage 1: 30B loop with self-tests, no-peek"
python3 swe_bench_loop.py --model qwen3-coder:30b-32k --rounds 2 --selftests $ST --no-peek --save data/go_swe_bench_v0_loop_qwen3-coder_30b-32k.selftest.jsonl > logs/loop_30b_selftest.log 2>&1
echo "[$(date '+%H:%M')] stage 1 done: $(grep 'ladder by' logs/loop_30b_selftest.log)"
echo "[$(date '+%H:%M')] stage 2: 7B loop with self-tests, no-peek"
python3 swe_bench_loop.py --model qwen2.5-coder:7b-32k --rounds 2 --selftests $ST --no-peek --save data/go_swe_bench_v0_loop_qwen2.5-coder_7b-32k.selftest.jsonl > logs/loop_7b_selftest.log 2>&1
echo "[$(date '+%H:%M')] stage 2 done: $(grep 'ladder by' logs/loop_7b_selftest.log)"
echo "[$(date '+%H:%M')] stage 3: router"
python3 swe_bench_router.py --preferred data/go_swe_bench_v0_loop_qwen3-coder_30b-32k.selftest.jsonl --alternate data/go_swe_bench_v0_loop_qwen2.5-coder_7b-32k.selftest.jsonl --selftests $ST > logs/router_selftest.log 2>&1
echo "[$(date '+%H:%M')] stage 3 done: $(grep 'ROUTER on' logs/router_selftest.log)"
echo "[$(date '+%H:%M')] queue done"
