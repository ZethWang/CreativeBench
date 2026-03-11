#!/usr/bin/env python3
"""Simple evaluation for exploration outputs (pass@1 + baseline novelty)."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional


CODE_BLOCK_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", re.DOTALL)


def iter_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def extract_code(text: str) -> str:
    match = CODE_BLOCK_RE.search(text or "")
    return match.group(1).strip() if match else (text or "").strip()


def char_ngrams(text: str, n: int = 4) -> set:
    if not text or len(text) < n:
        return set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def jaccard_distance(a: str, b: str, n: int = 4) -> float:
    if not a and not b:
        return 0.0
    if not a or not b:
        return 1.0
    set_a = char_ngrams(a, n=n)
    set_b = char_ngrams(b, n=n)
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 1.0
    return 1.0 - (len(set_a & set_b) / len(union))


def load_exec_results(exec_path: Optional[Path]) -> Dict[int, Dict]:
    if exec_path is None or not exec_path.exists():
        return {}
    results: Dict[int, Dict] = {}
    for record in iter_jsonl(exec_path):
        idx = record.get("index")
        if idx is not None:
            results[int(idx)] = record
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Exploration dataset JSONL")
    parser.add_argument("--model-output", required=True, help="model_output.jsonl")
    parser.add_argument("--exec-results", default="", help="exec_results.jsonl (optional)")
    parser.add_argument("--output-dir", default="", help="Directory to write evaluation files")
    args = parser.parse_args()

    dataset_path = Path(args.dataset).resolve()
    model_output_path = Path(args.model_output).resolve()
    exec_results_path = Path(args.exec_results).resolve() if args.exec_results else None

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    if not model_output_path.exists():
        raise FileNotFoundError(f"Model output not found: {model_output_path}")

    output_dir = Path(args.output_dir).resolve() if args.output_dir else model_output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = list(iter_jsonl(dataset_path))
    exec_results = load_exec_results(exec_results_path)

    baseline_by_problem: Dict[str, str] = {}
    for record in iter_jsonl(model_output_path):
        problem_id = str(record.get("problem_id", ""))
        level = record.get("level")
        if problem_id and level == 0:
            baseline_by_problem[problem_id] = extract_code(record.get("output", ""))

    reference_by_problem: Dict[str, str] = {}
    for item in dataset:
        problem_id = str(item.get("problem_id", ""))
        if problem_id and problem_id not in reference_by_problem:
            reference_by_problem[problem_id] = (item.get("reference_solution") or "").strip()

    total = 0
    passed = 0
    novelty_sum = 0.0
    creativity_sum = 0.0

    by_level = defaultdict(lambda: {"total": 0, "passed": 0, "novelty_sum": 0.0, "creativity_sum": 0.0})

    details_path = output_dir / "creativity_details.jsonl"
    if details_path.exists():
        details_path.unlink()

    for record in iter_jsonl(model_output_path):
        idx = int(record.get("index", total))
        if idx >= len(dataset):
            continue
        item = dataset[idx]
        problem_id = str(item.get("problem_id", ""))
        level = item.get("level", record.get("level", 0))

        gen_code = extract_code(record.get("output", ""))
        baseline = baseline_by_problem.get(problem_id) or reference_by_problem.get(problem_id, "")
        novelty = 0.0 if level == 0 else jaccard_distance(gen_code, baseline, n=4)

        exec_record = exec_results.get(idx, {})
        success = exec_record.get("exec_status") == "PASS" or exec_record.get("success") is True
        creativity = novelty if success else 0.0

        total += 1
        passed += 1 if success else 0
        novelty_sum += novelty
        creativity_sum += creativity

        lvl = int(level) if level is not None else 0
        by_level[lvl]["total"] += 1
        by_level[lvl]["passed"] += 1 if success else 0
        by_level[lvl]["novelty_sum"] += novelty
        by_level[lvl]["creativity_sum"] += creativity

        detail = {
            "index": idx,
            "problem_id": problem_id,
            "level": lvl,
            "success": success,
            "novelty": round(novelty, 6),
            "creativity": round(creativity, 6),
        }
        with details_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(detail, ensure_ascii=False) + "\n")

    avg_novelty = novelty_sum / total if total else 0.0
    avg_creativity = creativity_sum / total if total else 0.0

    by_level_summary = {}
    for lvl, stats in sorted(by_level.items()):
        total_lvl = stats["total"]
        passed_lvl = stats["passed"]
        by_level_summary[str(lvl)] = {
            "total": total_lvl,
            "passed": passed_lvl,
            "pass@1": (passed_lvl / total_lvl) if total_lvl else 0.0,
            "avg_novelty": (stats["novelty_sum"] / total_lvl) if total_lvl else 0.0,
            "avg_creativity": (stats["creativity_sum"] / total_lvl) if total_lvl else 0.0,
        }

    summary = {
        "dataset": str(dataset_path),
        "model_output": str(model_output_path),
        "exec_results": str(exec_results_path) if exec_results_path else None,
        "total": total,
        "passed": passed,
        "pass@1": (passed / total) if total else 0.0,
        "avg_novelty": avg_novelty,
        "avg_creativity": avg_creativity,
        "by_level": by_level_summary,
        "note": (
            "Novelty is a proxy: char 4-gram Jaccard distance to level-0 baseline "
            "generated code (fallback to reference_solution when missing)."
        ),
    }

    summary_path = output_dir / "evaluation.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
