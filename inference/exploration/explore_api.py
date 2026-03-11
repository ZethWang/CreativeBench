#!/usr/bin/env python3
"""Minimal API inference + sandbox evaluation for CreativeBench exploration dataset."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests


CODE_BLOCK_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", re.DOTALL)


def load_env_from_parents(start: Path) -> None:
    for parent in [start] + list(start.parents):
        env_path = parent / ".env"
        if env_path.exists():
            _load_env_file(env_path)
            return


def _load_env_file(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def iter_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, record: Dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def sanitize_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "model"


def build_base_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    return base_url if base_url.endswith("/v1") else f"{base_url}/v1"


def extract_code(text: str) -> str:
    match = CODE_BLOCK_RE.search(text or "")
    return match.group(1).strip() if match else (text or "").strip()


def format_constraints(item: Dict) -> str:
    constraints = item.get("constraints_detail") or item.get("constraints") or []
    if isinstance(constraints, list):
        parts = []
        for entry in constraints:
            if isinstance(entry, dict):
                parts.append(entry.get("constraint") or entry.get("blocked_technique") or "")
            else:
                parts.append(str(entry))
        constraints = [c for c in parts if c]
    if not constraints:
        return "None."
    return "\n".join(f"- {c}" for c in constraints)


def build_prompt(item: Dict) -> str:
    question = item.get("question", "").strip()
    signature = item.get("function_signature", "").strip()
    constraints = format_constraints(item)
    prompt = (
        "You are an expert programmer. Follow the task and constraints below. "
        "Return only one Markdown code block with the complete solution.\n\n"
        f"Task:\n{question}\n\n"
    )
    if signature:
        prompt += f"Function signature:\n{signature}\n\n"
    prompt += f"Constraints:\n{constraints}\n"
    return prompt


def chat_completion(
    model: str,
    prompt: str,
    api_key: str,
    base_url: str,
    temperature: float,
    max_tokens: Optional[int],
    timeout: int,
) -> str:
    url = f"{build_base_url(base_url)}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")


def call_sandbox(
    code: str,
    test_code: str,
    language: str,
    host: str,
    port: int,
    timeout: int,
) -> Tuple[bool, Dict]:
    payload = {
        "src_uid": f"creativebench_{int(time.time())}",
        "func_code": code,
        "main_code": test_code,
        "lang": language,
        "show_log": "true",
        "request_extensions": {"timeout": timeout, "debug": "false"},
    }
    url = f"http://{host}:{port}/submit"
    response = requests.post(url, json=payload, timeout=timeout + 10)
    response.raise_for_status()
    result = response.json()
    success = result.get("exec_outcome") == "PASSED"
    return success, result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Path to exploration JSONL dataset")
    parser.add_argument("--model", default="gpt-4.1", help="API-compatible model name")
    parser.add_argument("--output-dir", default=None, help="Output root directory")
    parser.add_argument("--max-items", type=int, default=None, help="Limit number of samples")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--sandbox-host", default="localhost")
    parser.add_argument("--sandbox-port", type=int, default=8080)
    parser.add_argument("--sandbox-timeout", type=int, default=30)
    parser.add_argument("--no-eval", action="store_true", help="Skip sandbox execution")
    args = parser.parse_args()

    dataset_path = Path(args.dataset).resolve()
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    load_env_from_parents(Path(__file__).resolve())

    api_key = args.api_key or os.getenv("MODEL_API_KEY")
    base_url = args.base_url or os.getenv("MODEL_BASE_URL", "http://localhost:8000/v1")
    if not api_key:
        raise ValueError("MODEL_API_KEY is required for API inference.")

    output_root = Path(args.output_dir) if args.output_dir else Path(__file__).resolve().parents[2] / "outputs"
    run_tag = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    model_dir = sanitize_name(args.model)
    out_dir = output_root / "exploration" / model_dir / run_tag
    out_dir.mkdir(parents=True, exist_ok=True)

    model_output_path = out_dir / "model_output.jsonl"
    exec_output_path = out_dir / "exec_results.jsonl"
    summary_path = out_dir / "evaluation.json"

    total = 0
    passed = 0

    for idx, item in enumerate(iter_jsonl(dataset_path)):
        if args.max_items is not None and idx >= args.max_items:
            break
        prompt = build_prompt(item)
        output = chat_completion(
            model=args.model,
            prompt=prompt,
            api_key=api_key,
            base_url=base_url,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            timeout=60,
        )
        record = {
            "index": idx,
            "model": args.model,
            "output": output,
            "problem_id": item.get("problem_id"),
            "level": item.get("level"),
        }
        write_jsonl(model_output_path, record)

        if args.no_eval:
            continue

        code = extract_code(output)
        test_code = item.get("test_code", "")
        language = (item.get("language") or "python").lower()
        success = False
        response = {}
        error = None
        if not test_code:
            error = "missing test code"
        else:
            try:
                success, response = call_sandbox(
                    code=code,
                    test_code=test_code,
                    language=language,
                    host=args.sandbox_host,
                    port=args.sandbox_port,
                    timeout=args.sandbox_timeout,
                )
            except Exception as exc:  # pragma: no cover - best effort logging
                error = str(exc)

        exec_record = {
            "index": idx,
            "language": language,
            "difficulty": item.get("difficulty"),
            "problem_id": item.get("problem_id"),
            "level": item.get("level"),
            "exec_status": "PASS" if success else "FAIL",
            "success": success,
            "error": error,
            "response": response,
        }
        write_jsonl(exec_output_path, exec_record)
        total += 1
        passed += 1 if success else 0

    summary = {
        "dataset": str(dataset_path),
        "model": args.model,
        "total": total,
        "passed": passed,
        "pass@1": (passed / total) if total else 0.0,
        "model_output": str(model_output_path),
        "exec_results": None if args.no_eval else str(exec_output_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
