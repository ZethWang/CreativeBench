#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3}"

DATA_ORIG="${1:-$ROOT_DIR/../../../AutoCodeGen/data/code/autocodebench.jsonl}"
MAX_CONSTRAINTS="${MAX_CONSTRAINTS:-7}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/runs}"
MODEL="${MODEL:-gpt-4.1}"
ANALYZER_MODEL="${ANALYZER_MODEL:-$MODEL}"
VERIFIER_MODEL="${VERIFIER_MODEL:-gpt-4.1-mini}"
SOLVER_MODEL="${SOLVER_MODEL:-$MODEL}"
CONCURRENCY="${CONCURRENCY:-1}"
SAVE_INTERVAL="${SAVE_INTERVAL:-10}"
NUM_PROBLEMS="${NUM_PROBLEMS:-}"
USE_CANONICAL="${USE_CANONICAL:-1}"
FLAT_OUT="${FLAT_OUT:-}"

CONVERT_DIR="$ROOT_DIR/data/converted/autocodebench"
DATA_PY_ONLY="$CONVERT_DIR/autocodebench_python_only.jsonl"

if [[ ! -f "$DATA_ORIG" ]]; then
  echo "❌ Source dataset not found: $DATA_ORIG" >&2
  exit 1
fi

mkdir -p "$CONVERT_DIR" "$OUTPUT_DIR"

echo "Filtering python-only records from: $DATA_ORIG"
$PYTHON - "$DATA_ORIG" "$DATA_PY_ONLY" << 'PY'
import json, sys
src, out = sys.argv[1], sys.argv[2]
keep_difficulties = {"easy", "medium", "hard"}
written = 0
with open(src, "r", encoding="utf-8") as f, open(out, "w", encoding="utf-8") as w:
    for line in f:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("language") != "python":
            continue
        if obj.get("difficulty") not in keep_difficulties:
            continue
        tf = obj.get("full_test_func") or obj.get("assert_test_func")
        if not tf:
            continue
        w.write(json.dumps(obj, ensure_ascii=False) + "\n")
        written += 1
print(written)
PY

PY_COUNT=$(tail -n1 <<< "$($PYTHON - "$DATA_PY_ONLY" << 'PY'
import sys
c = 0
for line in open(sys.argv[1], "r", encoding="utf-8"):
    if line.strip():
        c += 1
print(c)
PY
)" )

if [[ -z "$NUM_PROBLEMS" ]]; then
  NUM_PROBLEMS="$PY_COUNT"
fi

echo "========================================"
echo "Self-Evolving (explore, python-only)"
echo "========================================"
echo "Root:        $ROOT_DIR"
echo "Data (orig): $DATA_ORIG"
echo "Data (py):   $DATA_PY_ONLY"
echo "Problems:    $NUM_PROBLEMS / total_py=$PY_COUNT"
echo "Constraints: $MAX_CONSTRAINTS"
echo "Output dir:  $OUTPUT_DIR"
echo "Models:"
echo "  - analyzer: $ANALYZER_MODEL"
echo "  - verifier: $VERIFIER_MODEL"
echo "  - solver:   $SOLVER_MODEL"
echo "Concurrency: $CONCURRENCY"
echo "Save every:  $SAVE_INTERVAL"
echo "========================================"

$PYTHON "$ROOT_DIR/evolve_llm_based.py" \
  --data-file "$DATA_PY_ONLY" \
  --num-problems "$NUM_PROBLEMS" \
  --max-constraints "$MAX_CONSTRAINTS" \
  --output-dir "$OUTPUT_DIR" \
  --model "$MODEL" \
  --analyzer-model "$ANALYZER_MODEL" \
  --verifier-model "$VERIFIER_MODEL" \
  --solver-model "$SOLVER_MODEL" \
  --concurrency "$CONCURRENCY" \
  --save-interval "$SAVE_INTERVAL" \
  $( [[ "$USE_CANONICAL" -eq 1 ]] && echo "--use-canonical-reference" )

echo "Evolution completed"

LATEST_RUN=$(ls -td "$OUTPUT_DIR"/run_* 2>/dev/null | head -1 || true)
if [[ -z "$LATEST_RUN" ]]; then
  echo "Warning: no run_* directory found under $OUTPUT_DIR"
  exit 0
fi
echo "Results saved to: $LATEST_RUN/"

echo "Generating visualization..."
$PYTHON "$ROOT_DIR/analyze_creativity_results.py" "$LATEST_RUN/creativity_evolution_results.json" || true

RUN_BASENAME=$(basename "$LATEST_RUN")
RUN_TS=${RUN_BASENAME#run_}
DATA_BASENAME=$(basename "$DATA_PY_ONLY")
DATA_STEM=${DATA_BASENAME%.jsonl}

if [[ -z "$FLAT_OUT" ]]; then
  FLAT_DIR="$CONVERT_DIR/$DATA_STEM"
  mkdir -p "$FLAT_DIR"
  FLAT_OUT="$FLAT_DIR/${DATA_STEM}_infer_${RUN_TS}.jsonl"
else
  mkdir -p "$(dirname "$FLAT_OUT")"
fi

echo "Converting to flat infer dataset..."
$PYTHON "$ROOT_DIR/datasets/tools/convert_evolution_to_infer_dataset.py" \
  --results "$LATEST_RUN/creativity_evolution_results.json" \
  --source "$DATA_PY_ONLY" \
  --out "$FLAT_OUT" \
  --max-levels "$MAX_CONSTRAINTS" \
  --only-success || true

if [[ -f "$FLAT_OUT" ]]; then
  echo "Flat dataset saved to: $FLAT_OUT"
else
  echo "Warning: flat dataset conversion did not produce file"
fi

echo "Done."
