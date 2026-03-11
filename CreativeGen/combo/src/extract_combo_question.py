import argparse
import re
from utils import *

def extract_question(response_text):
    """Extract question from response text"""
    # Look for question tags
    question_pattern = r'<question>(.*?)</question>'
    matches = re.findall(question_pattern, response_text, re.DOTALL)
    
    if matches:
        return matches[0].strip()
    
    # Fallback: return the whole response
    return response_text.strip()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file', type=str, required=True,
                        help='Input file with API responses')
    parser.add_argument('--output_file', type=str, required=True,
                        help='Output file with extracted questions')
    parser.add_argument('--msg_file', type=str, default=None,
                        help='Optional: Question message file (with asserts) for backfilling fields')
    parser.add_argument('--combo_msg_file', type=str, default=None,
                        help='Optional: Original combo message file to recover parent_codeA/B by index')
    args = parser.parse_args()
    
    responses = read_jsonl(args.input_file)
    
    # If msg_file is provided, load it to get the original test functions with asserts
    if args.msg_file:
        msg_data = read_jsonl(args.msg_file)
        # Create a mapping by index for easy lookup
        msg_dict = {item.get('index', i): item for i, item in enumerate(msg_data)}
    else:
        msg_dict = {}

    # Optionally load original combo messages (carry parent_codeA/B)
    if args.combo_msg_file:
        combo_msg_data = read_jsonl(args.combo_msg_file)
        combo_msg_dict = {item.get('index', i): item for i, item in enumerate(combo_msg_data)}
    else:
        combo_msg_dict = {}
    
    results = []
    for i, response in enumerate(responses):
        output = response.get('output', '')
        question = extract_question(output)
        
        # Get test functions from msg_file if available, otherwise from response
        if args.msg_file and i in msg_dict:
            # Use test functions from the original msg file (with asserts)
            demo_test = msg_dict[i].get('demo_test_func', response.get('demo_test_func'))
            full_test = msg_dict[i].get('full_test_func', response.get('full_test_func'))
            canonical_solution = msg_dict[i].get('canonical_solution', response.get('canonical_solution'))
            combo_info = msg_dict[i].get('combo_info', response.get('combo_info', {}))
            language = msg_dict[i].get('language', response.get('language', 'cpp'))
            parent_codeA = msg_dict[i].get('parent_codeA', response.get('parent_codeA'))
            parent_codeB = msg_dict[i].get('parent_codeB', response.get('parent_codeB'))
        else:
            # Fallback to response data
            demo_test = response.get('demo_test_func')
            full_test = response.get('full_test_func')
            canonical_solution = response.get('canonical_solution')
            combo_info = response.get('combo_info', {})
            language = response.get('language', 'cpp')
            parent_codeA = response.get('parent_codeA')
            parent_codeB = response.get('parent_codeB')

        # If parents still missing, try to recover from original combo messages
        if (not parent_codeA or not parent_codeB) and i in combo_msg_dict:
            parent_codeA = parent_codeA or combo_msg_dict[i].get('parent_codeA')
            parent_codeB = parent_codeB or combo_msg_dict[i].get('parent_codeB')
        
        # Only include the 6 required fields + combo_info (+ parents for offline CN)
        result = {
            "question": question,
            "canonical_solution": canonical_solution,
            "demo_test_func": demo_test,
            "full_test_func": full_test,
            "language": language,
            "difficulty": "medium-hard",  # Combination problems are inherently more complex
            "combo_info": combo_info,  # Track source problems
            # Parents are optional; present if build step persisted them.
            "parent_codeA": parent_codeA,
            "parent_codeB": parent_codeB,
        }
        
        # Verify that test functions contain assert statements
        demo_asserts = result['demo_test_func'].count('assert') if result['demo_test_func'] else 0
        full_asserts = result['full_test_func'].count('assert') if result['full_test_func'] else 0
        
        if demo_asserts == 0 or full_asserts == 0:
            print(f"Warning: Missing asserts - demo: {demo_asserts}, full: {full_asserts}")
        
        results.append(result)
    
    write_jsonl(results, args.output_file, mode='w')
    print(f"Extracted {len(results)} combination questions")
