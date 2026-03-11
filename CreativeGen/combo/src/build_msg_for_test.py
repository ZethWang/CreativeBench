#!/usr/bin/env python3
"""
Build messages for generating test functions with assert statements.
This is the standard implementation following reference/build_msg_for_test.py
"""

import argparse
from utils import read_jsonl, write_jsonl, read_file
from tqdm import tqdm


def formatting_test_input_and_output(datas):
    """Format test input and output from sandbox results"""
    res = []
    for item in datas:
        if not item['success']: 
            continue
        
        dic = item['original_data']
        
        # Map test I/O from sandbox execution results
        dic['demo_test_input'] = item['original_data']['demo_test_func']
        dic['demo_test_output'] = item['demo_test_result']['response']['exec_cout']
        dic['full_test_input'] = item['original_data']['full_test_func']
        dic['full_test_output'] = item['full_test_result']['response']['exec_cout']
        
        # Clean up old test function fields (will be replaced with assert versions)
        if 'demo_test_func' in dic: del dic['demo_test_func']
        if 'full_test_func' in dic: del dic['full_test_func']
        
        # Clean up internal fields
        if '_absolute_line_number' in dic: del dic['_absolute_line_number']
        if '_relative_line_number' in dic: del dic['_relative_line_number']
        if 'extracted_code' in dic: del dic['extracted_code']
        
        res.append(dic)
    return res


def get_prompt(template, item, mode):
    """Generate prompt by filling in the template"""
    if mode == "gen_test_function":
        # Replace template placeholders with actual data
        prompt = template.replace("<<<<code>>>>", item['canonical_solution'])
        prompt = prompt.replace("<<<<test cases>>>>", item['demo_test_input'])
        prompt = prompt.replace("<<<<test case results>>>>", item['demo_test_output'])
        prompt = prompt.replace("<<<<test cases2>>>>", item['full_test_input'])
        prompt = prompt.replace("<<<<test case results2>>>>", item['full_test_output'])
    else:
        raise ValueError(f"Invalid mode: {mode}")
    return prompt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw_code_file', type=str, required=True,
                        help='Input file with solutions and test I/O from sandbox')
    parser.add_argument('--raw_code_msg_file', type=str, required=True,
                        help='Output file for test generation messages')
    parser.add_argument('--lang', type=str, default='cpp',
                        choices=['python', 'java', 'cpp', 'javascript', 'go', 'shell'])
    parser.add_argument('--mode', type=str, default='gen_test_function',
                        help='Mode of operation')
    args = parser.parse_args()

    # Load the standard template from reference
    template_file = f"templates/{args.mode}_templates/{args.lang}.txt"
    template = read_file(template_file)
    
    # Read input data
    dt = read_jsonl(args.raw_code_file)
    
    # Format test input and output
    prev_len = len(dt)
    dt = formatting_test_input_and_output(dt)
    print(f"Filtered out {prev_len - len(dt)} failed records based on sandbox results; {len(dt)} remaining")
    
    # Build messages
    datas = []
    for i, item in enumerate(tqdm(dt, desc="Processing data")):
        prompt = get_prompt(template, item, args.mode)
        item["messages"] = [
            {"role": "system", "content": "You are an expert programmer. Generate test functions with assert statements based on the provided code and test cases."},
            {"role": "user", "content": prompt}       
        ]
        datas.append(item)
    
    # Write output
    write_jsonl(datas, args.raw_code_msg_file, mode='w')
    print(f"Generated {len(datas)} test generation messages")
    print(f"Saved to: {args.raw_code_msg_file}")
