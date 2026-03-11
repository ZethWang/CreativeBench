#!/usr/bin/env python3
"""
Merge successful codes from different fix attempts into final result files.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Set


def load_jsonl(file_path: str) -> List[Dict]:
    """Load data from JSONL file."""
    data = []
    if Path(file_path).exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    return data


def save_jsonl(data: List[Dict], file_path: str) -> None:
    """Save data to JSONL file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def merge_successful_codes(output_dir: str, max_attempts: int) -> Dict:
    """
    Merge successful codes from all fix attempts.

    Args:
        output_dir: Output directory containing validation results
        max_attempts: Maximum number of fix attempts

    Returns:
        Statistics dictionary
    """
    output_path = Path(output_dir)
    all_successful = []
    seen_indices = set()

    # Statistics tracking
    stats = {
        'total_original': 0,
        'original_success': 0,
        'attempts': {}
    }

    # Process original results (attempt 0)
    original_file = output_path / 'combo_validated_0.jsonl'
    original_data = load_jsonl(str(original_file))
    stats['total_original'] = len(original_data)

    for data in original_data:
        if data.get('success', False):
            # Add fix_attempt field
            record = data.copy()
            record['fix_attempt'] = 0

            # Use index for deduplication
            idx = record.get('index', len(all_successful))
            if idx not in seen_indices:
                all_successful.append(record)
                seen_indices.add(idx)
                stats['original_success'] += 1

    # Process fix attempts (1 to max_attempts)
    for attempt in range(1, max_attempts + 1):
        attempt_file = output_path / f'combo_validated_{attempt}.jsonl'
        attempt_data = load_jsonl(str(attempt_file))

        attempt_success = 0
        for data in attempt_data:
            if data.get('success', False):
                # Add fix_attempt field
                record = data.copy()
                record['fix_attempt'] = attempt

                # Use index for deduplication
                idx = record.get('index', len(all_successful))
                if idx not in seen_indices:
                    all_successful.append(record)
                    seen_indices.add(idx)
                    attempt_success += 1

        stats['attempts'][attempt] = {
            'total': len(attempt_data),
            'success': attempt_success
        }

    # Save results
    all_successful_file = output_path / 'all_successful.jsonl'
    save_jsonl(all_successful, str(all_successful_file))

    # Save final success file (copy of all_successful for backward compatibility)
    final_success_file = output_path / 'combo_final_success.jsonl'
    save_jsonl(all_successful, str(final_success_file))

    # Update overall stats
    stats['final_total'] = len(all_successful)
    stats['final_success_rate'] = len(all_successful) / stats['total_original'] * 100 if stats['total_original'] > 0 else 0

    return stats


def main():
    parser = argparse.ArgumentParser(description='Merge successful codes from fix attempts')
    parser.add_argument('--output_dir', required=True, help='Output directory')
    parser.add_argument('--max_attempts', type=int, default=2, help='Maximum number of fix attempts')
    parser.add_argument('--verbose', action='store_true', help='Print detailed statistics')

    args = parser.parse_args()

    # Merge successful codes
    stats = merge_successful_codes(args.output_dir, args.max_attempts)

    # Print summary
    print("==========================================")
    print("PHASE 3: Collecting Final Results")
    print("==========================================")
    print(f"Merging all successful codes...")
    print(f"Total successful codes: {stats['final_total']} out of {stats['total_original']}")
    print()

    # Print detailed statistics
    print("Success by attempt:")
    print(f"  Original: {stats['original_success']} codes")

    for attempt, attempt_stats in stats['attempts'].items():
        if attempt_stats['success'] > 0:
            print(f"  Fix attempt {attempt}: {attempt_stats['success']} additional codes")

    print()
    print(f"Final success rate: {stats['final_success_rate']:.1f}%")

    if args.verbose:
        print("\nDetailed statistics:")
        print(f"  Original validation results: {stats['total_original']} total, {stats['original_success']} successful")
        for attempt, attempt_stats in stats['attempts'].items():
            if attempt_stats['total'] > 0:
                success_rate = attempt_stats['success'] / attempt_stats['total'] * 100
                print(f"  Fix attempt {attempt}: {attempt_stats['total']} total, {attempt_stats['success']} successful ({success_rate:.1f}%)")


if __name__ == '__main__':
    main()