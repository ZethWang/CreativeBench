import argparse
import random
from utils import *

def select_combo_pairs(data, num_combos=10, stratified=True):
    """Select pairs for combination from different domains using stratified sampling
    
    Args:
        data: List of data items
        num_combos: Number of combinations to generate
        stratified: If True, use stratified sampling to ensure balanced domain representation
    """
    # Group by domain
    domains = {}
    for item in data:
        domain = item.get('domain', 'Unknown')
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(item)
    
    domain_list = list(domains.keys())
    print(f"Found {len(domain_list)} domains with sizes: {[(d, len(domains[d])) for d in domain_list]}")
    
    if len(domain_list) < 2:
        print("Error: Need at least 2 domains for combinations")
        return []
    
    combinations = []
    
    if stratified:
        # Stratified sampling approach
        print("Using stratified sampling for balanced domain combinations...")
        
        # Calculate how many samples each domain should contribute
        total_domain_pairs = len(domain_list) * (len(domain_list) - 1) // 2  # C(n,2)
        samples_per_domain_pair = max(1, num_combos // total_domain_pairs)
        
        # Create all possible domain pairs
        import itertools
        all_domain_pairs = list(itertools.combinations(domain_list, 2))
        
        print(f"Total domain pairs: {len(all_domain_pairs)}")
        print(f"Target samples per domain pair: {samples_per_domain_pair}")
        
        # For each domain pair, sample items
        for d1, d2 in all_domain_pairs:
            # Calculate how many combinations for this domain pair
            remaining_combos = num_combos - len(combinations)
            remaining_pairs = len(all_domain_pairs) - all_domain_pairs.index((d1, d2))
            
            if remaining_combos <= 0:
                break
                
            # Allocate samples for this pair (ensure we don't exceed num_combos)
            samples_for_this_pair = min(samples_per_domain_pair, 
                                       remaining_combos // remaining_pairs + (1 if remaining_combos % remaining_pairs > all_domain_pairs.index((d1, d2)) else 0))
            
            # Sample items from each domain
            domain1_items = random.sample(domains[d1], min(samples_for_this_pair, len(domains[d1])))
            domain2_items = random.sample(domains[d2], min(samples_for_this_pair, len(domains[d2])))
            
            # Create combinations (pair items from the two domains)
            for i in range(samples_for_this_pair):
                if len(combinations) >= num_combos:
                    break
                    
                item1 = domain1_items[i % len(domain1_items)]
                item2 = domain2_items[i % len(domain2_items)]
                combinations.append((item1, item2))
        
        # Fill remaining slots if needed
        while len(combinations) < num_combos:
            d1, d2 = random.sample(domain_list, 2)
            item1 = random.choice(domains[d1])
            item2 = random.choice(domains[d2])
            combinations.append((item1, item2))
        
        # Print domain participation statistics
        domain_usage = {}
        for item1, item2 in combinations:
            d1, d2 = item1.get('domain'), item2.get('domain')
            domain_usage[d1] = domain_usage.get(d1, 0) + 1
            domain_usage[d2] = domain_usage.get(d2, 0) + 1
        
        print("Domain participation statistics (stratified):")
        for domain, count in sorted(domain_usage.items()):
            print(f"  {domain}: {count} times")
            
    else:
        # Original random approach
        print("Using random sampling...")
        for i in range(num_combos):
            if len(domain_list) < 2:
                continue
            d1, d2 = random.sample(domain_list, 2)
            item1 = random.choice(domains[d1])
            item2 = random.choice(domains[d2])
            combinations.append((item1, item2))
    
    return combinations[:num_combos]  # Ensure exact number

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file', type=str, required=True)
    parser.add_argument('--output_file', type=str, required=True)
    parser.add_argument('--num_combos', type=int, default=10)
    parser.add_argument('--lang', type=str, default='cpp', 
                        choices=['cpp', 'python'],
                        help='Target programming language')
    parser.add_argument('--stratified', action='store_true', default=True,
                        help='Use stratified sampling for balanced domain representation')
    parser.add_argument('--random', action='store_true', 
                        help='Use random sampling instead of stratified sampling')
    args = parser.parse_args()
    
    # Handle sampling method selection
    if args.random:
        stratified = False
    else:
        stratified = args.stratified

    # Select template based on language
    if args.lang == 'python':
        template = read_file('templates/combo_evolve_py.txt')
    else:
        template = read_file('templates/combo_evolve.txt')
    
    data = read_jsonl(args.input_file)
    
    # Filter data by language
    filtered_data = [item for item in data if item.get('language', 'cpp') == args.lang]
    print(f"Total data: {len(data)}, Filtered {args.lang} data: {len(filtered_data)}")
    
    if len(filtered_data) == 0:
        print(f"Error: No {args.lang} data found in the input file")
        exit(1)
    
    # Select combination pairs
    combos = select_combo_pairs(filtered_data, args.num_combos, stratified=stratified)
    print(f"Generated {len(combos)} combination pairs")
    
    messages = []
    for i, (item1, item2) in enumerate(combos):
        prompt = template.replace("<<<domain1>>>", item1.get('domain', 'Unknown'))
        prompt = prompt.replace("<<<domain2>>>", item2.get('domain', 'Unknown'))
        prompt = prompt.replace("<<<code1>>>", item1.get('canonical_solution', ''))
        prompt = prompt.replace("<<<code2>>>", item2.get('canonical_solution', ''))
        
        data_item = {
            "messages": [
                {"role": "system", "content": "You are an expert programmer specializing in creative code combination."},
                {"role": "user", "content": prompt}
            ],
            "index": i,
            "language": args.lang,  # Add language field
            # Persist parent codes for downstream combinational novelty evaluation
            "parent_codeA": item1.get('canonical_solution', ''),
            "parent_codeB": item2.get('canonical_solution', ''),
            "combo_info": {
                "domain1": item1.get('domain', 'Unknown'),
                "domain2": item2.get('domain', 'Unknown'),
                "source1_question": item1.get('question', '')[:200] + "...",
                "source2_question": item2.get('question', '')[:200] + "..."
            }
        }
        messages.append(data_item)
    
    write_jsonl(messages, args.output_file, mode='w')
    print(f"Generated {len(messages)} combination messages for {args.lang}")
