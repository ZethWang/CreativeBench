#!/usr/bin/env python3
"""
Format the final dataset to include only the required fields.
Ensures test functions contain assert statements.
"""

import argparse
import json
from utils import read_jsonl, write_jsonl


def verify_assert_in_test(test_func_code):
    """
    Verify that test function contains assert statements.
    Returns the count of assert statements.
    """
    if not test_func_code:
        return 0
    return test_func_code.count('assert')


def format_dataset_entry(item):
    """
    Format a dataset entry to include only required fields.
    
    Required fields:
    1. question - Problem description
    2. canonical_solution - Solution code
    3. demo_test_func - Demo test with asserts
    4. full_test_func - Full test with asserts
    5. language - Programming language
    6. difficulty - Problem difficulty
    
    Plus optional:
    - combo_info - Information about source problems (for combo datasets)
    """
    
    # Extract required fields
    formatted = {
        "question": item.get("question", ""),
        "canonical_solution": item.get("canonical_solution", ""),
        "demo_test_func": item.get("demo_test_func", ""),
        "full_test_func": item.get("full_test_func", ""),
        "language": item.get("language", "cpp"),
        "difficulty": item.get("difficulty", "medium-hard")
    }
    
    # Add combo_info if it exists (tracks source problems)
    if "combo_info" in item:
        formatted["combo_info"] = item["combo_info"]
    
    # Verify assert statements are present
    demo_asserts = verify_assert_in_test(formatted["demo_test_func"])
    full_asserts = verify_assert_in_test(formatted["full_test_func"])
    
    if demo_asserts == 0:
        print(f"Warning: No assert statements in demo_test_func for item")
    if full_asserts == 0:
        print(f"Warning: No assert statements in full_test_func for item")
    
    # Add assert counts as metadata (optional, can be removed)
    formatted["_assert_counts"] = {
        "demo": demo_asserts,
        "full": full_asserts
    }
    
    return formatted


def main():
    parser = argparse.ArgumentParser(description='Format final dataset with required fields')
    parser.add_argument('--input', type=str, required=True,
                        help='Input dataset file')
    parser.add_argument('--output', type=str, required=True,
                        help='Output formatted dataset file')
    parser.add_argument('--verify-asserts', action='store_true',
                        help='Verify and report assert statement counts')
    parser.add_argument('--min-asserts', type=int, default=1,
                        help='Minimum number of assert statements required (default: 1)')
    
    args = parser.parse_args()
    
    # Read input data
    data = read_jsonl(args.input)
    print(f"Loaded {len(data)} entries from {args.input}")
    
    # Format and filter data
    formatted_data = []
    stats = {
        "total": len(data),
        "with_asserts": 0,
        "without_asserts": 0,
        "total_demo_asserts": 0,
        "total_full_asserts": 0
    }
    
    for i, item in enumerate(data):
        formatted = format_dataset_entry(item)
        
        # Check assert counts
        demo_asserts = formatted["_assert_counts"]["demo"]
        full_asserts = formatted["_assert_counts"]["full"]
        
        stats["total_demo_asserts"] += demo_asserts
        stats["total_full_asserts"] += full_asserts
        
        # Only include entries with sufficient asserts
        if demo_asserts >= args.min_asserts and full_asserts >= args.min_asserts:
            stats["with_asserts"] += 1
            
            # Remove the assert count metadata from final output
            if not args.verify_asserts:
                del formatted["_assert_counts"]
            
            formatted_data.append(formatted)
        else:
            stats["without_asserts"] += 1
            print(f"Skipping entry {i}: insufficient asserts (demo={demo_asserts}, full={full_asserts})")
    
    # Write formatted data
    write_jsonl(formatted_data, args.output, mode='w')
    
    # Print statistics
    print("\n=== Dataset Formatting Statistics ===")
    print(f"Total entries processed: {stats['total']}")
    print(f"Entries with asserts (>={args.min_asserts}): {stats['with_asserts']}")
    print(f"Entries without sufficient asserts: {stats['without_asserts']}")
    print(f"Average demo asserts: {stats['total_demo_asserts']/max(1, stats['total']):.1f}")
    print(f"Average full asserts: {stats['total_full_asserts']/max(1, stats['total']):.1f}")
    print(f"\nFormatted dataset saved to: {args.output}")
    
    # Sample output
    if formatted_data:
        print("\n=== Sample Entry Structure ===")
        sample = formatted_data[0]
        print("Fields in dataset:")
        for key in sample.keys():
            if key != "_assert_counts":
                value_preview = str(sample[key])[:50] + "..." if len(str(sample[key])) > 50 else str(sample[key])
                print(f"  - {key}: {value_preview}")


if __name__ == "__main__":
    main()