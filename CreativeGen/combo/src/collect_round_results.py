#!/usr/bin/env python3
"""
Collect successful results from a specific validation round.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List


def collect_round_results(validated_file: str, success_file: str, attempt: int) -> Dict:
    """
    Collect successful results from a validation file.

    Args:
        validated_file: Path to validation results file
        success_file: Path to save successful results
        attempt: Fix attempt number

    Returns:
        Statistics dictionary
    """
    successful_data = []
    total_count = 0
    success_count = 0

    # Read validation results
    with open(validated_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                total_count += 1
                data = json.loads(line)
                if data.get('success', False):
                    success_count += 1
                    # Add fix_attempt field and save
                    record = data.copy()
                    record['fix_attempt'] = attempt
                    successful_data.append(record)

    # Save successful results
    with open(success_file, 'w', encoding='utf-8') as f:
        for record in successful_data:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    # Calculate statistics
    success_rate = success_count / total_count * 100 if total_count > 0 else 0
    failed_count = total_count - success_count

    stats = {
        'attempt': attempt,
        'total': total_count,
        'success': success_count,
        'failed': failed_count,
        'success_rate': success_rate,
        'all_successful': failed_count == 0
    }

    return stats


def main():
    parser = argparse.ArgumentParser(description='Collect successful results from validation')
    parser.add_argument('--validated_file', required=True, help='Validation results file')
    parser.add_argument('--success_file', required=True, help='Output file for successful results')
    parser.add_argument('--attempt', type=int, required=True, help='Fix attempt number')

    args = parser.parse_args()

    # Collect results
    stats = collect_round_results(args.validated_file, args.success_file, args.attempt)

    # Print results
    print(f"Attempt {stats['attempt']} results: {stats['success']}/{stats['total']} successful ({stats['success_rate']:.1f}%)")

    if stats['all_successful']:
        print('All codes successful!')

    # Return status code for bash script
    return 0 if stats['success'] > 0 else 1


if __name__ == '__main__':
    exit(main())