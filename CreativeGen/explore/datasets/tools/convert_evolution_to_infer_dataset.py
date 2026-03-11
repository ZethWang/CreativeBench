#!/usr/bin/env python3
"""
Convert creativity_evolution_results.json into a flat JSONL dataset for direct
constraint-based inference (no technique-identification step).

Each output line represents a (problem, level) pair with cumulative constraints.
Schema per line:
  - id: unique id "{problem_id}_L{level}"
  - problem_id, level
  - language, difficulty (if available)
  - question
  - function_signature (extracted from canonical_solution)
  - constraints: list[str] (cumulative up to `level`)
  - constraints_detail: list[dict] (original detailed objects up to `level`)
  - test_code: full test function text
  - reference_solution: canonical_solution (for similarity baseline)
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List


def extract_function_signature(canonical_solution: str) -> str:
    pattern = r"^def\s+\w+\([^)]*\):"
    m = re.search(pattern, canonical_solution, re.MULTILINE)
    return m.group(0) if m else ""


def load_source_dataset(path: Path) -> List[Dict]:
    items: List[Dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            items.append(json.loads(line))
    return items


def convert(results_json: Path, source_data: Path, out_path: Path,
            max_levels: int | None = None,
            only_success: bool = False) -> int:
    src_items = load_source_dataset(source_data)

    with results_json.open("r", encoding="utf-8") as f:
        results = json.load(f)

    written = 0
    with out_path.open("w", encoding="utf-8") as w:
        for item in results:
            pid = item.get("problem_id")
            if not pid or not pid.startswith("problem_"):
                continue
            try:
                idx = int(pid.split("_")[-1])
            except Exception:
                continue
            if idx < 0 or idx >= len(src_items):
                continue

            src = src_items[idx]
            language = src.get("language", item.get("language", "python"))
            question = src.get("question", "")
            canonical_solution = src.get("canonical_solution", "")
            test_code = src.get("full_test_func") or src.get("assert_test_func", "")
            difficulty = src.get("difficulty", "unknown")

            constraints_all = sorted(
                item.get("key_techniques", {}).get("progressive_constraints", []),
                key=lambda x: x.get("level", 0),
            )
            total_levels = len(constraints_all)
            if max_levels is not None:
                total_levels = min(total_levels, max_levels)

            # decide which levels to include
            include_levels = set(range(1, total_levels + 1))
            if only_success:
                evo = item.get("evolution", [])
                include_levels = {e.get("level") for e in evo if e.get("success") and isinstance(e.get("level"), int)}
                include_levels = {l for l in include_levels if 1 <= l <= total_levels}

            # level 0 (no constraints) — always include
            func_sig = extract_function_signature(canonical_solution)
            line0 = {
                "id": f"{pid}_L0",
                "problem_id": pid,
                "level": 0,
                "language": language,
                "difficulty": difficulty,
                "question": question,
                "function_signature": func_sig,
                "constraints": [],
                "constraints_detail": [],
                "test_code": test_code,
                "reference_solution": canonical_solution,
            }
            w.write(json.dumps(line0, ensure_ascii=False) + "\n")
            written += 1

            # levels 1..N cumulative
            for L in range(1, total_levels + 1):
                if only_success and L not in include_levels:
                    continue
                cumul = constraints_all[:L]
                constraints_text = [c.get("constraint", "") for c in cumul]
                line = {
                    "id": f"{pid}_L{L}",
                    "problem_id": pid,
                    "level": L,
                    "language": language,
                    "difficulty": difficulty,
                    "question": question,
                    "function_signature": func_sig,
                    "constraints": constraints_text,
                    "constraints_detail": cumul,
                    "test_code": test_code,
                    "reference_solution": canonical_solution,
                }
                w.write(json.dumps(line, ensure_ascii=False) + "\n")
                written += 1

    return written


def main() -> None:
    ap = argparse.ArgumentParser(description="Convert evolution results to flat inference dataset")
    ap.add_argument("--results", required=True, help="Path to creativity_evolution_results.json")
    ap.add_argument("--source", required=True, help="The source JSONL dataset used for the run")
    ap.add_argument("--out", required=True, help="Output JSONL path")
    ap.add_argument("--max-levels", type=int, default=None, help="Cap levels to this number if set")
    ap.add_argument("--only-success", action="store_true", help="Only include levels with success==true (always keeps level 0)")
    args = ap.parse_args()

    written = convert(Path(args.results), Path(args.source), Path(args.out), args.max_levels, args.only_success)
    print(f"✅ Wrote {written} lines to {args.out}")


if __name__ == "__main__":
    main()
