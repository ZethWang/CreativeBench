import argparse
import re
from utils import *

def extract_code_blocks(text):
    """Extract three code blocks from response"""
    pattern = r'```(\w+)\s([\s\S]*?)```'
    matches = re.findall(pattern, text)
    code_blocks = []
    try:
        for match in matches:
            language, code = match
            code_blocks.append((language, code.strip()))
        assert len(code_blocks) == 3
        return code_blocks
    except:
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file', type=str, required=True)
    parser.add_argument('--output_file', type=str, required=True)
    args = parser.parse_args()
    
    responses = read_jsonl(args.input_file)
    
    results = []
    for response in responses:
        output = response.get('output', '')
        code_blocks = extract_code_blocks(output)
        
        if code_blocks is None:
            print(f"Warning: Could not extract 3 code blocks from response {response.get('index', -1)}")
            continue
            
        (lang, solution), (_, demo_test_func), (_, full_test_func) = code_blocks
        
        result = {
            "index": response.get('index', -1),
            "combo_info": response.get('combo_info', {}),
            "canonical_solution": solution,
            "demo_test_func": demo_test_func,
            "full_test_func": full_test_func,
            "language": lang.lower(),
            "question": f"Combined solution from domains: {response.get('combo_info', {}).get('domain1', 'N/A')} + {response.get('combo_info', {}).get('domain2', 'N/A')}",
            "raw_response": output
        }
        results.append(result)
    
    write_jsonl(results, args.output_file, mode='w')
    print(f"Extracted {len(results)} combined code solutions with test functions")