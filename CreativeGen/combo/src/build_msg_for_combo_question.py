import argparse
from utils import *

def build_combo_question_messages(input_file, output_file, lang='cpp'):
    """Build messages for combined code question generation"""
    
    # Select template based on language
    template_path = f"templates/gen_question_templates/{lang}.txt"
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Read combined code data
    combo_data = read_jsonl(input_file)
    
    messages = []
    for idx, item in enumerate(combo_data):
        # Handle both formats: direct item or nested in success result
        if 'success' in item:
            # This is from filter_data.py output (nested format)
            if not item.get('success', False):
                continue
            # Extract from original_data for nested format
            data = item.get('original_data', {})
        else:
            # This is direct format (from combo_test_func.jsonl or similar)
            data = item
            
        # Remove language-specific markdown code block markers
        code_lang_marker = f'```{lang}\n' if lang == 'python' else '```cpp\n'
        code = data.get('canonical_solution', '').replace(code_lang_marker, '').replace('\n```', '')
        demo_test = data.get('demo_test_func', '')
        full_test = data.get('full_test_func', '')
        combo_info = data.get('combo_info', {})
        
        # Fill in the standard template placeholders
        prompt = template.replace('<<<code>>>', code)
        prompt = prompt.replace('<<<demo_test>>>', demo_test)
        prompt = prompt.replace('<<<full_test>>>', full_test)
        
        message = {
            "index": idx,
            "combo_info": combo_info,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "canonical_solution": data.get('canonical_solution'),
            "demo_test_func": demo_test,
            "full_test_func": full_test,
            "language": data.get('language', lang)
        }
        
        messages.append(message)
    
    # Write messages to output file
    write_jsonl(messages, output_file, mode='w')
    print(f"Generated {len(messages)} question generation messages")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file', type=str, required=True, 
                        help='Input file with combined code solutions')
    parser.add_argument('--output_file', type=str, required=True,
                        help='Output file for question generation messages')
    parser.add_argument('--lang', type=str, default='cpp',
                        choices=['cpp', 'python', 'java', 'javascript', 'go', 'shell'],
                        help='Target programming language')
    args = parser.parse_args()
    
    build_combo_question_messages(args.input_file, args.output_file, args.lang)