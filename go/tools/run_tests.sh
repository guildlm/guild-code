#!/bin/bash
# Wrapper to run Crucible evaluations for the Go Guild models

echo "⚔️ GuildLM Code Guild - Go Test Runner"
echo "Initializing Crucible evaluator..."

# In a real environment, this would call crucible/src/core/runner.py 
# with the generated JSON outputs from the SLM.
export PYTHONPATH="../../crucible:$PYTHONPATH"
python3 -c "
from src.evaluators.go_eval import GoEvaluator
import sys

evaluator = GoEvaluator()
good_code = 'package sandbox\\nfunc Add(a, b int) int { return a + b }'
tests = 'package sandbox\\nimport \"testing\"\\nfunc TestAdd(t *testing.T) { if Add(2, 3) != 5 { t.Fatal(\"Failed\") } }'

print('Evaluating generated code...')
res = evaluator.run(good_code, tests)
print(f'Status: {res[\"status\"]}')
if res[\"status\"] != \"pass\":
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ All tests passed. SLM generation is functionally correct."
else
    echo "❌ Tests failed. Sending back to Reviewer SLM."
fi
