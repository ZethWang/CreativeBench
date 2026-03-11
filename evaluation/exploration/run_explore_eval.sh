#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

MODEL_OUTPUT="${1:-}"
if [[ -z "$MODEL_OUTPUT" ]]; then
  echo "Usage: $0 <model_output.jsonl> [exec_results.jsonl] [dataset.jsonl]" >&2
  exit 1
fi

EXEC_RESULTS="${2:-$(dirname "$MODEL_OUTPUT")/exec_results.jsonl}"
DATASET="${3:-$REPO_ROOT/datasets/exploratory_creativity_dataset_551.jsonl}"

python3 "$SCRIPT_DIR/eval_explore.py" \
  --dataset "$DATASET" \
  --model-output "$MODEL_OUTPUT" \
  --exec-results "$EXEC_RESULTS"
