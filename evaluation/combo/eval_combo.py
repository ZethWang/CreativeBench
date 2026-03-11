#!/usr/bin/env python3
"""Simple evaluation for combo outputs (pass@1 + proxy novelty)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


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


def load_dataset(dataset_path: Path) -> List[Dict]:
    return list(iter_jsonl(dataset_path))


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
    parser.add_argument("--dataset", required=True, help="Combo dataset JSONL")
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

    dataset = load_dataset(dataset_path)
    exec_results = load_exec_results(exec_results_path)

    total = 0
    passed = 0
    novelty_sum = 0.0
    creativity_sum = 0.0

    details_path = output_dir / "creativity_details.jsonl"
    if details_path.exists():
        details_path.unlink()

    for record in iter_jsonl(model_output_path):
        idx = int(record.get("index", total))
        if idx >= len(dataset):
            continue
        item = dataset[idx]
        output = record.get("output", "")
        gen_code = extract_code(output)
        ref_code = (item.get("canonical_solution") or "").strip()
        novelty = jaccard_distance(gen_code, ref_code, n=4)

        exec_record = exec_results.get(idx, {})
        success = exec_record.get("exec_status") == "PASS" or exec_record.get("success") is True
        creativity = novelty if success else 0.0

        total += 1
        passed += 1 if success else 0
        novelty_sum += novelty
        creativity_sum += creativity

        detail = {
            "index": idx,
            "success": success,
            "novelty": round(novelty, 6),
            "creativity": round(creativity, 6),
        }
        with details_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(detail, ensure_ascii=False) + "\n")

    avg_novelty = novelty_sum / total if total else 0.0
    avg_creativity = creativity_sum / total if total else 0.0

    summary = {
        "dataset": str(dataset_path),
        "model_output": str(model_output_path),
        "exec_results": str(exec_results_path) if exec_results_path else None,
        "total": total,
        "passed": passed,
        "pass@1": (passed / total) if total else 0.0,
        "avg_novelty": avg_novelty,
        "avg_creativity": avg_creativity,
        "note": (
            "Novelty is a proxy: char 4-gram Jaccard distance between generated code "
            "and canonical_solution."
        ),
    }

    summary_path = output_dir / "evaluation.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
