#!/usr/bin/env python3


import json
import os
import subprocess
import sys
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Resolve project-relative paths regardless of current working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

# Load environment variables from .env file

# Global variables for logging
log_file_path = None
original_stdout = sys.stdout

class TeeLogger:
    """Logger that writes to both console and file."""
    def __init__(self, log_file_path):
        self.terminal = sys.stdout
        self.log_file = open(log_file_path, 'w', encoding='utf-8')
    
    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)
        self.log_file.flush()
    
    def flush(self):
        self.terminal.flush()
        self.log_file.flush()
    
    def close(self):
        if self.log_file:
            self.log_file.close()

def load_env_from_parents(start: Path) -> Optional[Path]:
    for parent in [start] + list(start.parents):
        env_path = parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            return env_path
    return None

def setup_logging(output_dir: str) -> str:
    """Set up logging and return the timestamped directory path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_dir = os.path.join(output_dir, f"run_{timestamp}")
    os.makedirs(timestamped_dir, exist_ok=True)
    
    log_file_path = os.path.join(timestamped_dir, "console.log")
    
    tee_logger = TeeLogger(log_file_path)
    sys.stdout = tee_logger
    
    return timestamped_dir, tee_logger

def main():
    """Main entrypoint for the exploratory creativity benchmark."""
    import argparse

    parser = argparse.ArgumentParser(description='Self-Evolving Benchmark for Exploratory Creativity')
    parser.add_argument('--data-file', default='../../../AutoCodeGen/data/dataset/KodCode/train_sample_5_evolved_fixed.jsonl',
                       help='Input data file path')
    parser.add_argument('--num-problems', type=int, default=5,
                       help='Number of problems to test')
    parser.add_argument('--max-constraints', type=int, default=4,
                       help='Maximum number of constraint levels')
    parser.add_argument('--output-dir', default='test_results',
                       help='Output directory for results')
    parser.add_argument('--model', default='gpt-4.1',
                       help='Default LLM model (deprecated, use specific model args)')

    parser.add_argument('--analyzer-model', default='gpt-4.1',
                       help='Model for code analysis and technique identification')
    parser.add_argument('--verifier-model', default='gpt-4.1',
                       help='Model for constraint compliance verification')
    parser.add_argument('--solver-model', default='gpt-4.1',
                       help='Model for creative solution generation')
    parser.add_argument('--concurrency', type=int, default=1,
                       help='Parallel problems to process (per-problem; keep problem-internal steps serial)')
    parser.add_argument('--save-interval', type=int, default=5,
                       help='Save partial results every N processed problems (1 to save after each)')
    parser.add_argument('--use-canonical-reference', action='store_true',
                       help='If set, allow solver to view canonical solution as reference when generating constrained solutions')

    args = parser.parse_args()

    timestamped_dir = None
    tee_logger = None

    env_path = load_env_from_parents(Path(__file__).resolve())
    if env_path:
        print(f"✓ Loaded environment from {env_path}")

    os.makedirs(args.output_dir, exist_ok=True)

    timestamped_dir, tee_logger = setup_logging(args.output_dir)

    print("="*70)
    print("🚀 Self-Evolving Benchmark for Exploratory Creativity")
    print("="*70)
    print("\nThis benchmark measures AI models' ability to explore novel solutions")
    print("when conventional approaches are progressively constrained.\n")
    print(f"Configuration:")
    print(f"  Data: {args.data_file}")
    print(f"  Problems: {args.num_problems}")
    print(f"  Max constraints: {args.max_constraints}")
    print(f"  Models:")
    print(f"    - Analyzer: {args.analyzer_model}")
    print(f"    - Verifier: {args.verifier_model}")
    print(f"    - Solver: {args.solver_model}")
    print(f"  Output: {timestamped_dir}/")
    print(f"  Logging: console.log")
    print()

    from src.models.model_simple import APIModel

    analyzer = APIModel(
        model=args.analyzer_model,
        temperature=0.3,
        max_tokens=12000,
        gpt_setting="You are an expert code analyst."
    )

    verifier = APIModel(
        model=args.verifier_model,
        temperature=0.1,
        max_tokens=12000,
        gpt_setting="You are a strict code compliance verifier."
    )

    solver = APIModel(
        model=args.solver_model,
        temperature=0.7,
        max_tokens=12000,
        gpt_setting="You are a creative problem solver."
    )

    test_problems = load_test_problems(args.data_file, args.num_problems)

    results = []

    def _save_checkpoint(current_results, label: str = "partial"):
        try:
            ckpt_path = os.path.join(timestamped_dir, f"creativity_evolution_results.{label}.json")
            with open(ckpt_path, 'w', encoding='utf-8') as f:
                json.dump(current_results, f, indent=2, ensure_ascii=False)
            with open(os.path.join(timestamped_dir, 'progress.json'), 'w', encoding='utf-8') as f:
                json.dump({
                    'processed': len(current_results),
                    'total_planned': len(test_problems),
                }, f, indent=2, ensure_ascii=False)
            print(f"  💾 Checkpoint saved: {ckpt_path} (processed={len(current_results)})")
        except Exception as e:
            print(f"  ⚠️ Failed to save checkpoint: {e}")

    if args.concurrency and args.concurrency > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _process_single(idx_problem):
            i, problem = idx_problem
            local_analyzer = APIModel(
                model=args.analyzer_model,
                temperature=0.3,
                max_tokens=12000,
                gpt_setting="You are an expert code analyst."
            )
            local_verifier = APIModel(
                model=args.verifier_model,
                temperature=0.1,
                max_tokens=12000,
                gpt_setting="You are a strict code compliance verifier."
            )
            local_solver = APIModel(
                model=args.solver_model,
                temperature=0.7,
                max_tokens=12000,
                gpt_setting="You are a creative problem solver."
            )

            print(f"\n┌{'─'*70}┐")
            print(f"│ 📝 Problem {i+1}/{len(test_problems)}: {problem['problem_id']:<30} │")
            print(f"│ 🔤 Language: {problem['language']:<10} | 🎯 Difficulty: {problem.get('difficulty', 'unknown'):<10} │")
            print(f"└{'─'*70}┘")

            print("🔍 Analyzing core techniques...")
            key_techniques = identify_key_techniques(local_analyzer, problem)
            if not key_techniques:
                print("  ❌ Failed to identify key techniques - skipping problem")
                return i, None

            constraint_count = len(key_techniques['progressive_constraints'])
            print(f"  ✅ Identified {constraint_count} constraint levels")
            for j, constraint in enumerate(key_techniques['progressive_constraints'][:3], 1):
                print(f"    Level {j}: {constraint['constraint'][:50]}{'...' if len(constraint['constraint']) > 50 else ''}")
            if constraint_count > 3:
                print(f"    ... and {constraint_count - 3} more levels")

            print(f"\n🚀 Starting constraint evolution (max {args.max_constraints} levels)...")
            evolution = evolve_with_constraints(local_solver, local_verifier, problem, key_techniques, args.max_constraints, use_canonical_reference=args.use_canonical_reference)

            successful_levels = [e for e in evolution if e['success']]
            max_level = max([e['level'] for e in successful_levels]) if successful_levels else 0
            print(f"  📊 Evolution complete: Successfully reached Level {max_level}")

            return i, {
                'problem_id': problem['problem_id'],
                'language': problem['language'],
                'key_techniques': key_techniques,
                'evolution': evolution
            }

        ordered = [None] * len(test_problems)
        print(f"\n⚙️  Running with per-problem concurrency={args.concurrency}")
        with ThreadPoolExecutor(max_workers=max(1, int(args.concurrency))) as ex:
            futs = [ex.submit(_process_single, (i, p)) for i, p in enumerate(test_problems)]
            processed = 0
            for fut in as_completed(futs):
                try:
                    i, res = fut.result()
                    if res:
                        ordered[i] = res
                        processed += 1
                        if args.save_interval > 0 and (processed % args.save_interval == 0):
                            _save_checkpoint([r for r in ordered if r])
                except Exception as e:
                    print(f"  ❌ Worker failed: {e}")
        results = [r for r in ordered if r]
    else:
        for i, problem in enumerate(test_problems):
            print(f"\n┌{'─'*70}┐")
            print(f"│ 📝 Problem {i+1}/{len(test_problems)}: {problem['problem_id']:<30} │")
            print(f"│ 🔤 Language: {problem['language']:<10} | 🎯 Difficulty: {problem.get('difficulty', 'unknown'):<10} │")
            print(f"└{'─'*70}┘")

            print("🔍 Analyzing core techniques...")
            key_techniques = identify_key_techniques(analyzer, problem)
            if not key_techniques:
                print("  ❌ Failed to identify key techniques - skipping problem")
                continue

            constraint_count = len(key_techniques['progressive_constraints'])
            print(f"  ✅ Identified {constraint_count} constraint levels")
            for j, constraint in enumerate(key_techniques['progressive_constraints'][:3], 1):
                print(f"    Level {j}: {constraint['constraint'][:50]}{'...' if len(constraint['constraint']) > 50 else ''}")
            if constraint_count > 3:
                print(f"    ... and {constraint_count - 3} more levels")

            print(f"\n🚀 Starting constraint evolution (max {args.max_constraints} levels)...")
            evolution = evolve_with_constraints(solver, verifier, problem, key_techniques, args.max_constraints, use_canonical_reference=args.use_canonical_reference)

            successful_levels = [e for e in evolution if e['success']]
            max_level = max([e['level'] for e in successful_levels]) if successful_levels else 0
            print(f"  📊 Evolution complete: Successfully reached Level {max_level}")

            results.append({
                'problem_id': problem['problem_id'],
                'language': problem['language'],
                'key_techniques': key_techniques,
                'evolution': evolution
            })
            if args.save_interval > 0 and (len(results) % args.save_interval == 0):
                _save_checkpoint(results)

    save_results(results, timestamped_dir)
    analyze_creativity(results)

def identify_key_techniques(analyzer, problem: Dict) -> Optional[Dict]:
    """Identify key techniques and solution patterns."""

    print("\n  🔍 Analyzing solution to identify key techniques...")

    with open(os.path.join(TEMPLATES_DIR, 'identify_key_techniques.txt'), 'r') as f:
        template = f.read()

    prompt = template.replace('<<<LANGUAGE>>>', problem['language'])
    prompt = prompt.replace('<<<CODE>>>', problem['canonical_solution'])
    prompt = prompt.replace('<<<PROBLEM_DESCRIPTION>>>', problem['question'][:500])

    analyzer.restart()
    try:
        response = analyzer(prompt)[0]
    except Exception as e:
        print(f"  ⚠️ LLM analysis failed: {str(e)}")
        return None

    try:
        import re
        json_pattern = r'```json\n(.*?)```'
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            analysis = json.loads(matches[0])

            print("  ✓ Core techniques identified:")
            for tech in analysis['core_techniques'][:3]:
                print(f"    - {tech['technique']}: {tech['description'][:50]}...")

            return analysis
    except:
        print("  ⚠️ Failed to parse analysis")

    return None

def evolve_with_constraints(solver, verifier, problem: Dict,
                           key_techniques: Dict, max_constraints: int = 3,
                           use_canonical_reference: bool = False) -> List[Dict]:
    """Evolve solutions by progressively adding constraints."""

    evolution = []

    if use_canonical_reference:
        print("\n  ┌── Level 0: Baseline from Canonical Reference (No Constraints)")
        base_solution, base_approach = problem.get('canonical_solution', ''), 'reference_canonical'
    else:
        print("\n  ┌── Level 0: Model-Generated Baseline (No Constraints)")
        base_solution, base_approach = generate_baseline_solution(solver, problem)

    base_success = False
    if base_solution:
        test_func = problem.get('full_test_func')
        if test_func:
            # Use unified tester that handles `from solution import` by inlining tests
            base_success, _ = test_solution_with_feedback(
                base_solution, test_func, problem['language']
            )
        else:
            base_success = False
    else:
        print("  │   ⚠️ Failed to parse baseline code from model response; falling back to canonical baseline")
        base_solution = problem['canonical_solution']

    evolution.append({
        'level': 0,
        'constraints': [],
        'solution': base_solution,
        'success': base_success,
        'technique_used': 'baseline',
        'creative_approach': base_approach
    })

    if base_success:
        print("  └── ✅ Baseline solution passed tests")
    else:
        print("  └── ⚠️ Baseline solution did not pass tests (kept for similarity baseline)")
        # Policy change: skip constraint evolution when baseline fails
        print("  └── ⏭ Baseline failed; skip constraints per policy")
        return evolution

    current_constraints = []

    for constraint_info in key_techniques['progressive_constraints'][:max_constraints]:
        level = constraint_info['level']
        constraint = constraint_info['constraint']

        current_constraints.append(constraint_info)

        print(f"\n  ┌── Level {level}: Constraint Evolution")
        print(f"  │   🚫 Adding: {constraint[:60]}{'...' if len(constraint) > 60 else ''}")
        print(f"  │   🎯 Blocked technique: {constraint_info.get('blocked_technique', 'N/A')}")

        solution, success, approach, attempts_info = generate_creative_solution(
            solver, verifier, problem, current_constraints, use_reference=use_canonical_reference
        )

        evolution.append({
            'level': level,
            'constraints': [c['constraint'] for c in current_constraints],
            'solution': solution,
            'success': success,
            'technique_used': 'alternative' if success else 'failed',
            'creative_approach': approach if success else None,
            'attempts': attempts_info
        })

        if success:
            print(f"  └── ✅ Creative solution found! ({len(attempts_info)} attempts)")
            if approach:
                print(f"      💡 Approach: {approach[:80]}{'...' if len(approach) > 80 else ''}")
        else:
            print(f"  └── ❌ Failed after {len(attempts_info)} attempts - stopping evolution")
            break

    return evolution

def generate_creative_solution(solver, verifier, problem: Dict,
                              constraints: List[Dict], max_attempts: int = 3,
                              use_reference: bool = False) -> Tuple[Optional[str], bool, Optional[str], List[Dict]]:
    """Generate a constraint-compliant solution and return (code, success, approach, attempts)."""

    feedback_history = []
    attempts_info = []

    for attempt in range(max_attempts):
        print(f"  │   🔄 Attempt {attempt + 1}/{max_attempts}...")

        solution, approach = generate_with_constraints(solver, problem, constraints, feedback_history, use_reference=use_reference)

        attempt_record = {
            'attempt_number': attempt + 1,
            'generated_code': solution,
            'approach': approach,
            'correct': False,
            'constraint_compliant': False,
            'feedback': []
        }

        if not solution:
            attempt_record['feedback'].append("Failed to extract valid code from LLM response")
            feedback_history.append("Failed to extract valid code from LLM response")
            attempts_info.append(attempt_record)
            continue

        correct, detailed_feedback = test_solution_with_feedback(
            solution, problem['full_test_func'], problem['language']
        )

        attempt_record['correct'] = correct
        attempt_record['sandbox_feedback'] = detailed_feedback

        if not correct:
            attempt_record['feedback'].append(f"Code failed tests: {detailed_feedback}")
            feedback_history.append(f"Code failed tests: {detailed_feedback}")
            attempts_info.append(attempt_record)
            continue

        compliant = True
        constraint_feedback = []
        for constraint in constraints:
            is_compliant, reason = verify_constraint_compliance(
                verifier, solution, constraint, problem['language']
            )

            if not is_compliant:
                constraint_feedback.append(f"Constraint violation: {reason}")
                feedback_history.append(f"Constraint violation: {reason}")
                compliant = False
                break

        attempt_record['constraint_compliant'] = compliant
        attempt_record['constraint_feedback'] = constraint_feedback

        if compliant:
            attempts_info.append(attempt_record)
            return solution, True, approach, attempts_info

        attempts_info.append(attempt_record)

    return None, False, None, attempts_info


def test_solution_with_feedback(code: str, test_func: str, language: str) -> Tuple[bool, str]:
    """Test a solution and return detailed feedback."""
    import requests
    import time

    submit_url = "http://localhost:8080/submit"
    headers = {"Content-Type": "application/json"}

    if "from solution import" in test_func or "import solution" in test_func:
        simplified_test = test_func.replace("from solution import", "# from solution import")
        full_code = f"{code}\n\n{simplified_test}"

        payload = {
            "src_uid": f"evolve_test_{int(time.time())}",
            "source_code": full_code,
            "lang": language,
            "show_log": True,
            "request_extensions": {"timeout": 30, "debug": "false"}
        }
    else:
        payload = {
            "src_uid": f"evolve_test_{int(time.time())}",
            "func_code": code,
            "main_code": test_func,
            "lang": language,
            "show_log": True,
            "request_extensions": {"timeout": 30, "debug": "false"}
        }

    try:
        response = requests.post(submit_url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            success = result.get("exec_outcome") == "PASSED"

            if success:
                return True, "Test passed successfully"
            else:
                feedback = extract_sandbox_feedback(result)
                return False, feedback
        else:
            return False, f"HTTP error {response.status_code}: {response.text}"

    except requests.Timeout:
        return False, "Sandbox timeout (30s)"
    except Exception as e:
        return False, f"Execution error: {str(e)}"


def extract_sandbox_feedback(sandbox_result: dict) -> str:
    """Extract detailed feedback from sandbox result."""
    response_ext = sandbox_result.get("response_extensions", {})
    stderr = response_ext.get("stderr", "")
    if stderr:
        return stderr

    stderr = sandbox_result.get("exec_stderr", "")
    if stderr:
        return stderr

    compile_msg = sandbox_result.get("exec_compile_message", "")
    if compile_msg:
        return compile_msg

    outcome = sandbox_result.get("exec_outcome", "UNKNOWN")
    return f"Execution outcome: {outcome}"

def extract_function_signature(canonical_solution: str) -> str:
    """Extract function signature from reference solution (Python/C++)."""
    import re

    py_pat = r'^def\s+\w+\([^)]*\):'
    m = re.search(py_pat, canonical_solution, re.MULTILINE)
    if m:
        return m.group(0)

    cpp_lines = canonical_solution.splitlines()
    for line in cpp_lines:
        s = line.strip()
        if not s or s.startswith('//'):
            continue
        if s.startswith('#') or s.startswith('template') or s.startswith('class ') or s.startswith('struct '):
            continue
        if '(' in s and ')' in s and s.rstrip().endswith('{'):
            header = s[:-1].rstrip()
            return header
    return ""

def generate_with_constraints(solver, problem: Dict, constraints: List[Dict],
                             feedback: List[str], use_reference: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """Generate creative code under constraints and return code + approach."""

    with open(os.path.join(TEMPLATES_DIR, 'generate_with_constraints.txt'), 'r') as f:
        template = f.read()

    function_signature = extract_function_signature(problem['canonical_solution'])

    constraints_text = ""
    for i, c in enumerate(constraints, 1):
        constraints_text += f"{i}. **{c['constraint']}**\n"
        constraints_text += f"   - Blocked: {c['blocked_technique']}\n"

    feedback_text = ""
    if feedback:
        feedback_text = "Your previous attempts had these issues:\n"
        for i, f in enumerate(feedback[-2:], 1):
            feedback_text += f"{i}. {f}\n"
    else:
        feedback_text = "This is your first attempt."

    prompt = template.replace('<<<PROBLEM_DESCRIPTION>>>', problem['question'])
    prompt = prompt.replace('<<<FUNCTION_SIGNATURE>>>', function_signature)
    prompt = prompt.replace('<<<LANGUAGE>>>', problem['language'])
    prompt = prompt.replace('<<<CONSTRAINTS_LIST>>>', constraints_text)
    prompt = prompt.replace('<<<FEEDBACK_HISTORY>>>', feedback_text)

    if use_reference:
        reference_block = (
            "\n\n## Reference Solution (canonical, for adaptation)\n"
            f"```{problem['language']}\n"
            f"{problem['canonical_solution']}\n"
            "```\n"
            "You MUST adapt the reference to strictly satisfy ALL constraints above,"
            " and keep the exact required function signature and behavior."
        )
        prompt = prompt + reference_block

    solver.restart()
    response = solver(prompt)[0]

    return extract_code_and_approach(response, problem['language'])

def generate_baseline_solution(solver, problem: Dict) -> Tuple[Optional[str], Optional[str]]:
    """Generate an unconstrained baseline solution with a minimal prompt."""
    function_signature = extract_function_signature(problem['canonical_solution'])

    prompt = (
        f"You are an expert {problem['language']} programmer.\n"
        "Solve the following problem using exactly the given function signature.\n"
        "Return only a single code block with the implementation, no extra text.\n\n"
        "Problem:\n"
        f"{problem['question']}\n\n"
        "Function signature:\n"
        f"```{problem['language']}\n"
        f"{function_signature}\n"
        "```"
    )

    solver.restart()
    response = solver(prompt)[0]
    return extract_code_and_approach(response, problem['language'])

def verify_constraint_compliance(verifier, code: str, constraint: Dict,
                                language: str) -> Tuple[bool, str]:
    """Verify whether code follows constraints."""

    with open(os.path.join(TEMPLATES_DIR, 'verify_constraint_compliance.txt'), 'r') as f:
        template = f.read()

    prompt = template.replace('<<<LANGUAGE>>>', language)
    prompt = prompt.replace('<<<CODE>>>', code)
    prompt = prompt.replace('<<<CONSTRAINT>>>', constraint['constraint'])
    prompt = prompt.replace('<<<BLOCKED_TECHNIQUE>>>', constraint['blocked_technique'])
    prompt = prompt.replace('<<<VERIFICATION_HINT>>>', constraint.get('verification_hint', 'Check carefully'))

    verifier.restart()
    response = verifier(prompt)[0]

    try:
        import re
        json_pattern = r'```json\n(.*?)```'
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            result = json.loads(matches[0])
            return result['compliant'], result['reasoning']
    except:
        pass

    return False, "Unable to verify compliance"

def test_solution(code: str, test_func: str, language: str) -> bool:
    """Test solution correctness via HTTP API."""
    import requests
    import time

    submit_url = "http://localhost:8080/submit"
    headers = {"Content-Type": "application/json"}

    payload = {
        "src_uid": f"evolve_test_{int(time.time())}",
        "func_code": code,
        "main_code": test_func,
        "lang": language,
        "show_log": "true",
        "request_extensions": {"timeout": 10, "debug": "false"}
    }

    try:
        response = requests.post(submit_url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            return result.get("exec_outcome") == "PASSED"
        else:
            return False

    except requests.Timeout:
        print(f"    ⚠️ Test execution timeout (30s)")
        return False
    except Exception as e:
        print(f"    ⚠️ Test execution error: {str(e)}")
        return False

def extract_code_and_approach(text: str, language: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract code and approach from response."""
    import re

    code = None
    patterns = [
        rf'```{language}\n(.*?)```',
        r'```\n(.*?)```',
        r'```(.*?)```'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            code = matches[0].strip()
            break

    approach = None
    approach_pattern = r'\*\*Approach\*\*:\s*(.*?)(?:\n\n|\n$|$)'
    approach_matches = re.findall(approach_pattern, text, re.DOTALL)
    if approach_matches:
        approach = approach_matches[0].strip()

    return code, approach


def extract_code(text: str, language: str) -> Optional[str]:
    """Extract code from response (backward-compatible)."""
    code, _ = extract_code_and_approach(text, language)
    return code

def load_test_problems(data_file: str, num_problems: int) -> List[Dict]:
    """Load test problems."""

    problems = []
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            for i, line in enumerate(f):
                if len(problems) >= num_problems:
                    break
                data = json.loads(line)

                test_func = None
                if 'full_test_func' in data and data['full_test_func']:
                    test_func = data['full_test_func']
                elif 'assert_test_func' in data and data['assert_test_func']:
                    test_func = data['assert_test_func']

                if not test_func:
                    continue

                if data['language'] in ['python', 'cpp'] and data['difficulty'] in ['easy', 'medium', 'hard']:
                    problems.append({
                        'problem_id': f"problem_{i}",
                        'language': data['language'],
                        'difficulty': data['difficulty'],
                        'question': data['question'],
                        'canonical_solution': data['canonical_solution'],
                        'full_test_func': test_func
                    })

    return problems

def save_results(results: List[Dict], timestamped_dir: str):
    """Save results to timestamped directory."""

    print(f"\n🎨 Computing creativity scores based on code similarity...")
    from src.evaluators.creativity_scorer import CreativityScorer

    scorer = CreativityScorer()

    for i, result in enumerate(results):
        print(f"  📊 Problem {i+1}/{len(results)}: {result['problem_id']}...")
        creativity_eval = scorer.evaluate_evolution(result['evolution'])
        result['creativity_evaluation'] = creativity_eval

        if 'error' not in creativity_eval:
            print(f"      ✓ Average overall score: {creativity_eval['average_overall_score']:.2f}/100")

    results_path = os.path.join(timestamped_dir, 'creativity_evolution_results.json')
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    summary_path = os.path.join(timestamped_dir, 'summary_stats.json')
    summary = generate_summary_stats(results)
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n📁 Results saved to:")
    print(f"  - Detailed results: {results_path}")
    print(f"  - Summary stats: {summary_path}")

def generate_summary_stats(results: List[Dict]) -> Dict:
    """Generate summary statistics for results."""
    if not results:
        return {}

    total_problems = len(results)
    level_stats = {}

    for result in results:
        for evolution in result['evolution']:
            level = evolution['level']
            if level not in level_stats:
                level_stats[level] = {'total': 0, 'success': 0}
            level_stats[level]['total'] += 1
            if evolution['success']:
                level_stats[level]['success'] += 1

    max_levels = []
    for result in results:
        max_level = 0
        for evolution in result['evolution']:
            if evolution['success'] and evolution['level'] > max_level:
                max_level = evolution['level']
        max_levels.append(max_level)

    all_overall_scores = []
    level_creativity_stats = {}

    for result in results:
        if 'creativity_evaluation' in result:
            eval_data = result['creativity_evaluation']

            for level_str, scores in eval_data['level_scores'].items():
                level = int(level_str)
                if level not in level_creativity_stats:
                    level_creativity_stats[level] = {
                        'similarity': [],
                        'creativity': [],
                        'overall': []
                    }

                if scores.get('similarity') is not None:
                    level_creativity_stats[level]['similarity'].append(scores['similarity'])
                    level_creativity_stats[level]['creativity'].append(scores['creativity'])
                level_creativity_stats[level]['overall'].append(scores['overall'])

            all_overall_scores.append(eval_data['average_overall_score'])

    creativity_by_level = {}
    for level, stats_dict in level_creativity_stats.items():
        creativity_by_level[level] = {
            'avg_similarity': round(sum(stats_dict['similarity']) / len(stats_dict['similarity']), 4) if stats_dict['similarity'] else None,
            'avg_creativity': round(sum(stats_dict['creativity']) / len(stats_dict['creativity']), 2) if stats_dict['creativity'] else 0.0,
            'avg_overall': round(sum(stats_dict['overall']) / len(stats_dict['overall']), 2) if stats_dict['overall'] else 0.0
        }

    overall_creativity_score = round(sum(all_overall_scores) / len(all_overall_scores), 2) if all_overall_scores else 0.0

    return {
        'total_problems': total_problems,
        'level_stats': level_stats,
        'creativity_stats': {
            'overall_score': overall_creativity_score,
            'by_level': creativity_by_level
        },
        'max_successful_level': max(max_levels) if max_levels else 0,
        'avg_max_level': sum(max_levels) / len(max_levels) if max_levels else 0
    }

def analyze_creativity(results: List[Dict]):
    """Analyze exploratory creativity."""

    print(f"\n{'='*70}")
    print("📊 EXPLORATORY CREATIVITY ANALYSIS")
    print(f"{'='*70}")

    if not results:
        print("❌ No results to analyze")
        return

    level_stats = {}
    total_problems = len(results)
    total_attempts = 0
    successful_attempts = 0

    for result in results:
        for evolution in result['evolution']:
            level = evolution['level']

            if level not in level_stats:
                level_stats[level] = {'total': 0, 'success': 0}

            level_stats[level]['total'] += 1
            total_attempts += 1
            
            if evolution['success']:
                level_stats[level]['success'] += 1
                successful_attempts += 1

    print(f"\n📈 Overall Statistics:")
    print(f"┌────────────────────────────────────────────────────────────────────┐")
    print(f"│ Problems Processed: {total_problems:<3} │ Total Attempts: {total_attempts:<3} │ Success Rate: {successful_attempts/total_attempts:.1%} │")
    print(f"└────────────────────────────────────────────────────────────────────┘")

    print(f"\n🎯 Success Rate by Constraint Level:")
    print("┌──────────┬──────────────────────┬─────────┬────────────┐")
    print("│  Level   │      Progress        │ Success │   Rate     │") 
    print("├──────────┼──────────────────────┼─────────┼────────────┤")

    for level in sorted(level_stats.keys()):
        stats = level_stats[level]
        rate = stats['success'] / stats['total'] if stats['total'] > 0 else 0
        bar_filled = int(rate * 12)
        bar = '█' * bar_filled + '░' * (12 - bar_filled)
        
        print(f"│ Level {level:<2} │ [{bar}] │ {stats['success']:>2}/{stats['total']:<2} │   {rate:>6.1%}   │")
    
    print("└──────────┴──────────────────────┴─────────┴────────────┘")

    print(f"\n🎨 Code Creativity (Similarity-Based):")

    creativity_stats = {}
    for result in results:
        if 'creativity_evaluation' in result:
            eval_data = result['creativity_evaluation']
            for level_str, scores in eval_data['level_scores'].items():
                level = int(level_str)
                if level not in creativity_stats:
                    creativity_stats[level] = {'similarities': [], 'creativities': [], 'overall_scores': []}
                if scores.get('similarity') is not None:
                    creativity_stats[level]['similarities'].append(scores['similarity'])
                    creativity_stats[level]['creativities'].append(scores['creativity'])
                creativity_stats[level]['overall_scores'].append(scores['overall'])

    if creativity_stats:
        print("┌──────────┬──────────────┬──────────────┬──────────────┐")
        print("│  Level   │ Avg Sim.(%)  │ Avg Creat.   │ Avg Overall  │")
        print("├──────────┼──────────────┼──────────────┼──────────────┤")

        for level in sorted(creativity_stats.keys()):
            stats = creativity_stats[level]
            avg_sim = sum(stats['similarities']) / len(stats['similarities']) * 100 if stats['similarities'] else 0
            avg_creat = sum(stats['creativities']) / len(stats['creativities']) if stats['creativities'] else 0
            avg_overall = sum(stats['overall_scores']) / len(stats['overall_scores']) if stats['overall_scores'] else 0
            print(f"│ Level {level:<2} │    {avg_sim:>5.1f}%    │    {avg_creat:>5.1f}     │    {avg_overall:>5.1f}     │")

        print("└──────────┴──────────────┴──────────────┴──────────────┘")

        all_overall_scores = []
        for result in results:
            if 'creativity_evaluation' in result:
                all_overall_scores.append(result['creativity_evaluation']['average_overall_score'])

        overall_score = sum(all_overall_scores) / len(all_overall_scores) if all_overall_scores else 0
        print(f"\n🏆 Overall Creativity Score: {overall_score:.2f}/100")

    max_successful_level = 0
    problem_max_levels = []
    for result in results:
        problem_max = 0
        for evolution in result['evolution']:
            if evolution['success'] and evolution['level'] > problem_max:
                problem_max = evolution['level']
        problem_max_levels.append(problem_max)
        if problem_max > max_successful_level:
            max_successful_level = problem_max

    avg_max_level = sum(problem_max_levels) / len(problem_max_levels) if problem_max_levels else 0
    print(f"📊 Max Constraint Depth: Level {max_successful_level} | Avg: {avg_max_level:.1f}")

if __name__ == "__main__":
    main()
