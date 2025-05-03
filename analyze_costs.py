import json
import os
import datetime
import argparse
from collections import defaultdict

def analyze_openrouter_costs(days=30):
    """Analyze OpenRouter costs from the log file"""
    log_file = os.environ.get("OPENROUTER_COST_LOG", "openrouter_costs.json")
    
    if not os.path.exists(log_file):
        print("No cost log file found.")
        return
    
    with open(log_file, 'r') as f:
        logs = json.load(f)
    
    # Filter by date range if needed
    if days:
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        logs = [entry for entry in logs if entry.get('timestamp', '') >= cutoff]
    
    if not logs:
        print(f"No entries found in the past {days} days.")
        return
    
    # Analysis by provider and model
    total_cost = sum(entry.get('cost', 0) for entry in logs)
    total_tokens = sum(entry.get('total_tokens', 0) for entry in logs)
    total_runs = len(logs)
    
    by_provider = defaultdict(lambda: defaultdict(int))
    by_model = defaultdict(lambda: defaultdict(int))
    
    for entry in logs:
        provider = entry.get('provider', 'unknown')
        model = entry.get('model', 'unknown')
        cost = entry.get('cost', 0)
        tokens = entry.get('total_tokens', 0)
        
        by_provider[provider]['cost'] += cost
        by_provider[provider]['tokens'] += tokens
        by_provider[provider]['runs'] += 1
        
        by_model[model]['cost'] += cost
        by_model[model]['tokens'] += tokens
        by_model[model]['runs'] += 1
    
    # Print report
    print(f"{'=' * 50}")
    print(f"OPENROUTER COST ANALYSIS - PAST {days} DAYS")
    print(f"{'=' * 50}")
    print(f"Total runs: {total_runs}")
    print(f"Total tokens: {total_tokens:,}")
    print(f"Total cost: ${total_cost:.4f}")
    print(f"Average cost per run: ${total_cost/total_runs if total_runs else 0:.4f}")
    
    print("\nCOST BY PROVIDER:")
    for provider, stats in by_provider.items():
        pct_cost = (stats['cost'] / total_cost * 100) if total_cost else 0
        print(f"  {provider}: ${stats['cost']:.4f} ({pct_cost:.1f}% of total)")
        print(f"    - Runs: {stats['runs']} ({stats['runs']/total_runs*100:.1f}% of total)")
        print(f"    - Tokens: {stats['tokens']:,} ({stats['tokens']/total_tokens*100:.1f}% of total)")
        print(f"    - Avg cost per token: ${stats['cost']/stats['tokens']*1000:.5f} per 1K tokens" if stats['tokens'] else "")
    
    print("\nCOST BY MODEL:")
    for model, stats in by_model.items():
        pct_cost = (stats['cost'] / total_cost * 100) if total_cost else 0
        print(f"  {model}: ${stats['cost']:.4f} ({pct_cost:.1f}% of total)")
        print(f"    - Runs: {stats['runs']}")
        print(f"    - Tokens: {stats['tokens']:,}")
        print(f"    - Avg cost per token: ${stats['cost']/stats['tokens']*1000:.5f} per 1K tokens" if stats['tokens'] else "")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze OpenRouter costs")
    parser.add_argument("--days", type=int, default=30, help="Number of days to analyze")
    args = parser.parse_args()
    
    analyze_openrouter_costs(args.days) 