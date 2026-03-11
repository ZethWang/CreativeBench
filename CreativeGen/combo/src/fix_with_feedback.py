#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import json
import re
import argparse
from utils import read_jsonl, write_jsonl, read_file

def extract_error_info(sandbox_result):
    error_info = {
        "has_error": False,
        "error_type": "unknown",
        "error_message": "",
        "test_type": "",
        "exit_code": 0,
        "stderr": "",
        "compile_message": ""
    }

    if sandbox_result.get("success", False):
        return error_info

    error_info["has_error"] = True

    full_test = sandbox_result.get("full_test_result", {})
    demo_test = sandbox_result.get("demo_test_result", {})

    if not full_test.get("success", False):
        error_info["error_type"] = "api_error"
        error_info["test_type"] = "full_test"
        error_info["error_message"] = full_test.get("error", "Unknown API error")
        return error_info

    if not demo_test.get("success", False):
        error_info["error_type"] = "api_error"
        error_info["test_type"] = "demo_test"
        error_info["error_message"] = demo_test.get("error", "Unknown API error")
        return error_info

    full_test = sandbox_result.get("full_test_result", {})
    if full_test.get("success") and full_test.get("response"):
        response = full_test.get("response", {})
        outcome = response.get("exec_outcome", "")

        if outcome == "RUNTIME_ERROR":
            error_info["error_type"] = "runtime"
            error_info["test_type"] = "full_test"
            error_info["stderr"] = response.get("response_extensions", {}).get("stderr", "")
            error_info["exit_code"] = response.get("response_extensions", {}).get("exit_code", 0)
            error_info["error_message"] = error_info["stderr"]
        elif outcome == "COMPILE_ERROR":
            error_info["error_type"] = "compile"
            error_info["test_type"] = "full_test"
            error_info["compile_message"] = response.get("exec_compile_message", "")
            error_info["error_message"] = error_info["compile_message"]
        elif outcome == "TIMEOUT":
            error_info["error_type"] = "timeout"
            error_info["test_type"] = "full_test"
            error_info["error_message"] = "Code execution exceeded time limit"

    if not error_info["error_message"]:
        demo_test = sandbox_result.get("demo_test_result", {})
        if demo_test.get("success") and demo_test.get("response"):
            response = demo_test.get("response", {})
            outcome = response.get("exec_outcome", "")

            if outcome == "RUNTIME_ERROR":
                error_info["error_type"] = "runtime"
                error_info["test_type"] = "demo_test"
                error_info["stderr"] = response.get("response_extensions", {}).get("stderr", "")
                error_info["exit_code"] = response.get("response_extensions", {}).get("exit_code", 0)
                error_info["error_message"] = error_info["stderr"]
            elif outcome == "COMPILE_ERROR":
                error_info["error_type"] = "compile"
                error_info["test_type"] = "demo_test"
                error_info["compile_message"] = response.get("exec_compile_message", "")
                error_info["error_message"] = error_info["compile_message"]
            elif outcome == "TIMEOUT":
                error_info["error_type"] = "timeout"
                error_info["test_type"] = "demo_test"
                error_info["error_message"] = "Code execution exceeded time limit"

    return error_info

def classify_error_type(error_message):
    """Classify errors in more detail"""
    error_message_lower = error_message.lower()

    if "syntaxerror" in error_message_lower:
        return "syntax"
    elif "nameerror" in error_message_lower:
        return "undefined_variable"
    elif "typeerror" in error_message_lower:
        return "type_error"
    elif "attributeerror" in error_message_lower:
        return "attribute_error"
    elif "indexerror" in error_message_lower or "list index out of range" in error_message_lower:
        return "index_error"
    elif "keyerror" in error_message_lower:
        return "key_error"
    elif "valueerror" in error_message_lower:
        return "value_error"
    elif "zerodivisionerror" in error_message_lower:
        return "zero_division"
    elif "timeout" in error_message_lower:
        return "timeout"
    elif "recursionerror" in error_message_lower or "maximum recursion" in error_message_lower:
        return "recursion_error"
    elif "importerror" in error_message_lower or "modulenotfounderror" in error_message_lower:
        return "import_error"
    else:
        return "runtime"

def get_fix_guidelines(error_type, error_message):
    guidelines = []

    if error_type == "syntax":
        guidelines.append("- Check for missing colons, parentheses, or quotes")
        guidelines.append("- Verify proper indentation (use 4 spaces)")
        guidelines.append("- Look for unclosed brackets or strings")

    elif error_type == "undefined_variable":
        guidelines.append("- Ensure all variables are defined before use")
        guidelines.append("- Check if function parameters are passed correctly")
        guidelines.append("- Verify all necessary imports are present")
        match = re.search(r"name '(\w+)' is not defined", error_message)
        if match:
            var_name = match.group(1)
            guidelines.append(f"- Specifically check the definition of '{var_name}'")

    elif error_type == "type_error":
        guidelines.append("- Check data type compatibility in operations")
        guidelines.append("- Verify function arguments match expected types")
        guidelines.append("- Look for None values being used inappropriately")

    elif error_type == "attribute_error":
        guidelines.append("- Verify object has the attribute being accessed")
        guidelines.append("- Check for typos in attribute names")
        guidelines.append("- Ensure object is properly initialized")

    elif error_type == "index_error":
        guidelines.append("- Check list/array bounds before accessing")
        guidelines.append("- Verify loop ranges are correct")
        guidelines.append("- Handle empty lists appropriately")

    elif error_type == "timeout":
        guidelines.append("- Optimize loops to reduce iterations")
        guidelines.append("- Check for infinite loops or recursion")
        guidelines.append("- Consider more efficient algorithms")
        guidelines.append("- Add early termination conditions")

    elif error_type == "recursion_error":
        guidelines.append("- Add proper base cases to recursive functions")
        guidelines.append("- Verify recursion terminates correctly")
        guidelines.append("- Consider iterative solutions if recursion is too deep")

    elif error_type == "import_error":
        guidelines.append("- Only use Python standard library modules")
        guidelines.append("- Check for typos in import statements")
        guidelines.append("- Ensure correct import syntax (from X import Y)")

    line_match = re.search(r"line (\d+)", error_message)
    if line_match:
        line_num = line_match.group(1)
        guidelines.append(f"- Focus on fixing the error at line {line_num}")

    return "\n".join(guidelines)

def build_fix_prompt(code_data, error_info):
    """Build fix prompt"""
    template = read_file("templates/fix_code_with_error.txt")

    code = code_data.get("canonical_solution", "")

    combo_info = code_data.get("combo_info", {})
    domain1 = combo_info.get("domain1", "Unknown")
    domain2 = combo_info.get("domain2", "Unknown")

    detailed_error_type = classify_error_type(error_info["error_message"])

    fix_guidelines = get_fix_guidelines(detailed_error_type, error_info["error_message"])

    prompt = template.replace("<<<code>>>", code)
    prompt = prompt.replace("<<<error_type>>>", detailed_error_type)
    prompt = prompt.replace("<<<error_message>>>", error_info["error_message"])
    prompt = prompt.replace("<<<test_type>>>", error_info["test_type"])
    prompt = prompt.replace("<<<exit_code>>>", str(error_info["exit_code"]))
    prompt = prompt.replace("<<<domain1>>>", domain1)
    prompt = prompt.replace("<<<domain2>>>", domain2)
    prompt = prompt.replace("<<<fix_guidelines>>>", fix_guidelines)

    return prompt

def extract_fixed_code(response):
    """Extract fixed code block from LLM response"""
    pattern = r'```python\n(.*?)```'
    matches = re.findall(pattern, response, re.DOTALL)

    if len(matches) >= 3:
        return {
            "canonical_solution": matches[0].strip(),
            "demo_test_func": matches[1].strip(),
            "full_test_func": matches[2].strip()
        }
    elif len(matches) == 1:
        return {
            "canonical_solution": matches[0].strip(),
            "demo_test_func": None,
            "full_test_func": None
        }
    else:
        return {
            "canonical_solution": response,
            "demo_test_func": None,
            "full_test_func": None
        }

def fix_single_code(code_data, sandbox_result):
    """Fix a single code"""
    error_info = extract_error_info(sandbox_result)

    if not error_info["has_error"]:
        print(f"  Code {code_data.get('index', 'unknown')} has no error, skipping")
        return code_data

    print(f"\n  === Fixing code {code_data.get('index', 'unknown')} ===")
    print(f"  Error type: {error_info['error_type']}")
    print(f"  Test type: {error_info['test_type']}")

    if error_info['error_message']:
        print(f"  ╔══════════════════════════════════════════════════════════════")
        print(f"  ║ SANDBOX ERROR (NOT OUR CODE ERROR):")
        print(f"  ╟──────────────────────────────────────────────────────────────")
        error_lines = error_info['error_message'].split('\n')[:5]
        for line in error_lines:
            print(f"  ║ {line[:200]}")
        if len(error_lines) < len(error_info['error_message'].split('\n')):
            print(f"  ║ ... (truncated)")
        print(f"  ╚══════════════════════════════════════════════════════════════")

    prompt = build_fix_prompt(code_data, error_info)



    fix_message = {
        "messages": [
            {"role": "system", "content": "You are an expert Python programmer specializing in debugging and fixing code."},
            {"role": "user", "content": prompt}
        ],
        "index": code_data.get("index", 0),
        "error_info": error_info
    }

    return fix_message

def process_feedback_loop(validated_file, output_file, max_attempts=3):
    """Handle feedback loop"""
    validated_data = read_jsonl(validated_file)

    success_codes = []
    failed_codes = []

    for item in validated_data:
        if item.get("success", False):
            success_codes.append(item["original_data"])
        else:
            failed_codes.append({
                "code_data": item["original_data"],
                "sandbox_result": item
            })

    print(f"Initial results: {len(success_codes)} success, {len(failed_codes)} failed")

    fixed_codes = []
    for failed_item in failed_codes:
        code_data = failed_item["code_data"]
        sandbox_result = failed_item["sandbox_result"]
        fix_message = fix_single_code(code_data, sandbox_result)
        fixed_codes.append(fix_message)

    if fixed_codes:
        fix_msg_file = output_file.replace(".jsonl", "_fix_msg.jsonl")
        write_jsonl(fixed_codes, fix_msg_file)
        print(f"Generated {len(fixed_codes)} fix messages: {fix_msg_file}")

    final_results = success_codes

    write_jsonl(final_results, output_file)
    print(f"Saved {len(final_results)} successful codes to: {output_file}")

    return {
        "total": len(validated_data),
        "success": len(success_codes),
        "failed": len(failed_codes),
        "fix_messages_generated": len(fixed_codes)
    }

def main():
    parser = argparse.ArgumentParser(description="Fix code based on sandbox feedback")
    parser.add_argument("--validated_file", type=str, required=True,
                        help="Sandbox validation results file")
    parser.add_argument("--output_file", type=str, required=True,
                        help="Output file for successful codes")
    parser.add_argument("--max_attempts", type=int, default=3,
                        help="Maximum fix attempts per code")

    args = parser.parse_args()

    stats = process_feedback_loop(args.validated_file, args.output_file, args.max_attempts)

    print("\n=== Feedback Loop Statistics ===")
    print(f"Total codes: {stats['total']}")
    print(f"Initially successful: {stats['success']} ({stats['success']*100/stats['total']:.1f}%)")
    print(f"Initially failed: {stats['failed']} ({stats['failed']*100/stats['total']:.1f}%)")
    print(f"Fix messages generated: {stats['fix_messages_generated']}")

if __name__ == "__main__":
    main()
