#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

NUM_COMBOS="${1:-5}"
MAX_FIX_ATTEMPTS="${2:-3}"
INPUT_FILE="${3:-$ROOT_DIR/../../../AutoCodeBenchmark/AutoCodeGen/data/domain_tagging/final_with_domains_20250908_211938.jsonl}"

LANG="${LANG:-python}"
MODEL="${MODEL:-gpt-4.1}"
MAX_TOKENS="${MAX_TOKENS:-12000}"
API_TEMPERATURE="${API_TEMPERATURE:-0.3}"
FIX_TEMPERATURE="${FIX_TEMPERATURE:-0.1}"
API_NUM_PROCESS="${API_NUM_PROCESS:-1}"
API_NUM_THREAD="${API_NUM_THREAD:-1}"
SANDBOX_CONCURRENCY="${SANDBOX_CONCURRENCY:-4}"

TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
OUTPUT_DIR="$ROOT_DIR/runs/run_$TIMESTAMP"

mkdir -p "$OUTPUT_DIR"

LOG_FILE="$OUTPUT_DIR/run.log"
exec > >(tee -a "$LOG_FILE")
exec 2>&1

echo "=== Combo Pipeline (with feedback loop) ==="
echo "Input: $INPUT_FILE"
echo "Output: $OUTPUT_DIR"
echo "Combos: $NUM_COMBOS"
echo "Max fix attempts: $MAX_FIX_ATTEMPTS"
echo "Language: $LANG"
echo "Model: $MODEL"
echo "API process/thread: $API_NUM_PROCESS/$API_NUM_THREAD"
echo "Sandbox concurrency: $SANDBOX_CONCURRENCY"
echo

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: input file not found: $INPUT_FILE"
    exit 1
fi

# ========================================
# PHASE 1: Generate Initial Combinations
# ========================================
echo "=========================================="
echo "PHASE 1: Generating Initial Combinations"
echo "=========================================="

echo "Step 1.1: Generating combination messages..."
python3 src/build_combo_evolve.py \
    --input_file "$INPUT_FILE" \
    --output_file "$OUTPUT_DIR/combo_msg.jsonl" \
    --num_combos "$NUM_COMBOS" \
    --lang "$LANG" \
    --stratified

echo "Step 1.2: Generating combined code..."
python3 src/call_api.py \
    --input "$OUTPUT_DIR/combo_msg.jsonl" \
    --output "$OUTPUT_DIR/combo_output.jsonl" \
    --model "$MODEL" \
    --max_tokens "$MAX_TOKENS" \
    --temperature "$API_TEMPERATURE" \
    --num_process "$API_NUM_PROCESS" \
    --num_thread "$API_NUM_THREAD"

echo "Step 1.3: Extracting combined code..."
python3 src/extract_combo_code.py \
    --input_file "$OUTPUT_DIR/combo_output.jsonl" \
    --output_file "$OUTPUT_DIR/combo_code.jsonl"

echo "Step 1.4: Initial sandbox validation..."
python3 src/call_sandbox.py \
    --input_file "$OUTPUT_DIR/combo_code.jsonl" \
    --output "$OUTPUT_DIR/combo_validated_0.jsonl" \
    --solution_key canonical_solution \
    --concurrency "$SANDBOX_CONCURRENCY"

# ========================================
# PHASE 2: Feedback Loop for Failed Codes
# ========================================
echo
echo "=========================================="
echo "PHASE 2: Feedback Loop for Failed Codes"
echo "=========================================="

CURRENT_VALIDATED="$OUTPUT_DIR/combo_validated_0.jsonl"

for ATTEMPT in $(seq 1 "$MAX_FIX_ATTEMPTS"); do
    echo
    echo "--- Fix Attempt $ATTEMPT/$MAX_FIX_ATTEMPTS ---"

    echo "Analyzing failures and generating fix prompts..."
    python3 src/fix_with_feedback.py \
        --validated_file "$CURRENT_VALIDATED" \
        --output_file "$OUTPUT_DIR/success_round_$ATTEMPT.jsonl"

    FIX_MSG_FILE="$OUTPUT_DIR/success_round_${ATTEMPT}_fix_msg.jsonl"
    if [ ! -f "$FIX_MSG_FILE" ] || [ ! -s "$FIX_MSG_FILE" ]; then
        echo "No codes need fixing, all successful!"
        break
    fi

    NUM_TO_FIX=$(wc -l < "$FIX_MSG_FILE")
    echo "Found $NUM_TO_FIX codes to fix"

    echo "Calling API to fix codes..."
    python3 src/call_api.py \
        --input "$FIX_MSG_FILE" \
        --output "$OUTPUT_DIR/fixed_output_$ATTEMPT.jsonl" \
        --model "$MODEL" \
        --max_tokens "$MAX_TOKENS" \
        --temperature "$FIX_TEMPERATURE" \
        --num_process "$API_NUM_PROCESS" \
        --num_thread "$API_NUM_THREAD"

    echo "Extracting fixed code..."
    python3 src/extract_combo_code.py \
        --input_file "$OUTPUT_DIR/fixed_output_$ATTEMPT.jsonl" \
        --output_file "$OUTPUT_DIR/fixed_code_$ATTEMPT.jsonl"

    echo "Validating fixed code..."
    python3 src/call_sandbox.py \
        --input_file "$OUTPUT_DIR/fixed_code_$ATTEMPT.jsonl" \
        --output "$OUTPUT_DIR/combo_validated_$ATTEMPT.jsonl" \
        --solution_key canonical_solution \
        --concurrency "$SANDBOX_CONCURRENCY"

    CURRENT_VALIDATED="$OUTPUT_DIR/combo_validated_$ATTEMPT.jsonl"

    python3 src/collect_round_results.py \
        --validated_file "$CURRENT_VALIDATED" \
        --success_file "$OUTPUT_DIR/success_round_$ATTEMPT.jsonl" \
        --attempt "$ATTEMPT"

    FAILED_COUNT=$(python3 - <<PYTHON
import json
failed = 0
with open("$CURRENT_VALIDATED", "r", encoding="utf-8") as f:
    for line in f:
        if line.strip() and not json.loads(line).get("success", False):
            failed += 1
print(failed)
PYTHON
)

    if [ "$FAILED_COUNT" -eq 0 ]; then
        echo "All codes successful after attempt $ATTEMPT!"
        break
    fi
done

# ========================================
# PHASE 3: Collect and Analyze Results
# ========================================
echo
echo "=========================================="
echo "PHASE 3: Collecting Final Results"
echo "=========================================="

python3 src/merge_successful_codes.py \
    --output_dir "$OUTPUT_DIR" \
    --max_attempts "$MAX_FIX_ATTEMPTS" \
    --verbose

# ========================================
# PHASE 4: Generate Test Functions
# ========================================
echo
echo "=========================================="
echo "PHASE 4: Generating Test Functions"
echo "=========================================="

TEST_INPUT_FILE="$OUTPUT_DIR/combo_final_success.jsonl"
if [ ! -f "$TEST_INPUT_FILE" ]; then
    echo "Warning: $TEST_INPUT_FILE not found, falling back to $CURRENT_VALIDATED"
    TEST_INPUT_FILE="$CURRENT_VALIDATED"
fi

echo "Building test generation messages..."
python3 src/build_msg_for_test.py \
    --raw_code_file "$TEST_INPUT_FILE" \
    --raw_code_msg_file "$OUTPUT_DIR/test_msg.jsonl" \
    --lang "$LANG" \
    --mode gen_test_function

echo "Generating test functions..."
python3 src/call_api.py \
    --input "$OUTPUT_DIR/test_msg.jsonl" \
    --output "$OUTPUT_DIR/test_output.jsonl" \
    --model "$MODEL" \
    --max_tokens "$MAX_TOKENS" \
    --temperature "$FIX_TEMPERATURE" \
    --num_process "$API_NUM_PROCESS" \
    --num_thread "$API_NUM_THREAD"

echo "Extracting test functions..."
python3 src/extract_two_code_blocks.py \
    --input "$OUTPUT_DIR/test_output.jsonl" \
    --output "$OUTPUT_DIR/test_func.jsonl"

echo "Verifying test functions..."
python3 src/call_sandbox.py \
    --input_file "$OUTPUT_DIR/test_func.jsonl" \
    --output "$OUTPUT_DIR/test_verified.jsonl" \
    --solution_key canonical_solution \
    --concurrency "$SANDBOX_CONCURRENCY"

echo "Filtering successful tests..."
python3 src/filter_data.py \
    --input "$OUTPUT_DIR/test_verified.jsonl" \
    --output "$OUTPUT_DIR/combo_successful.jsonl"

SKIP_DOWNSTREAM="false"
if [ ! -s "$OUTPUT_DIR/combo_successful.jsonl" ]; then
    echo "Warning: No successful tests generated. Skipping question generation and dataset formatting."
    SKIP_DOWNSTREAM="true"
fi

# ========================================
# PHASE 5: Generating Problem Statements
# ========================================
echo
echo "=========================================="
echo "PHASE 5: Generating Problem Statements"
echo "=========================================="

if [ "$SKIP_DOWNSTREAM" = "true" ]; then
    echo "Skipping PHASE 5 and PHASE 6 due to missing successful tests."
else
    echo "Building question generation messages..."
    python3 src/build_msg_for_combo_question.py \
        --input_file "$OUTPUT_DIR/combo_successful.jsonl" \
        --output_file "$OUTPUT_DIR/combo_question_msg.jsonl" \
        --lang "$LANG"

    echo "Calling API to generate questions..."
    python3 src/call_api.py \
        --input "$OUTPUT_DIR/combo_question_msg.jsonl" \
        --output "$OUTPUT_DIR/combo_question_output.jsonl" \
        --model "$MODEL" \
        --max_tokens "$MAX_TOKENS" \
        --temperature "$FIX_TEMPERATURE" \
        --num_process "$API_NUM_PROCESS" \
        --num_thread "$API_NUM_THREAD"

    echo "Extracting questions..."
    python3 src/extract_combo_question.py \
        --input_file "$OUTPUT_DIR/combo_question_output.jsonl" \
        --output_file "$OUTPUT_DIR/combo_final_dataset.jsonl" \
        --msg_file "$OUTPUT_DIR/combo_question_msg.jsonl"

    echo "=========================================="
    echo "PHASE 6: Formatting Final Dataset"
    echo "=========================================="

    python3 src/format_final_dataset.py \
        --input "$OUTPUT_DIR/combo_final_dataset.jsonl" \
        --output "$OUTPUT_DIR/combo_final_formatted.jsonl" \
        --verify-asserts \
        --min-asserts 1
fi

echo
echo "=========================================="
echo "PIPELINE COMPLETED"
echo "=========================================="
echo "Output directory: $OUTPUT_DIR"
