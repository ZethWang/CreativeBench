#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

DATASET="${1:-$REPO_ROOT/datasets/exploratory_creativity_dataset_551.jsonl}"
MODEL="${2:-gpt-4.1}"
OUTPUT_DIR="${3:-$REPO_ROOT/outputs}"

python3 "$SCRIPT_DIR/explore_api.py" \
  --dataset "$DATASET" \
  --model "$MODEL" \
  --output-dir "$OUTPUT_DIR"
