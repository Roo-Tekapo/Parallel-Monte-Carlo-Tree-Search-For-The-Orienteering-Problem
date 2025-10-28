#!/usr/bin/env python3
"""
Results Analyzer

Loads benchmark results from Excel and provides summary statistics and comparisons.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Error: pandas not available. Install with: pip install pandas openpyxl")
    sys.exit(1)


def load_results(filepath: str) -> pd.DataFrame:
    """Load results from Excel file."""
    try:
        df = pd.read_excel(filepath, sheet_name='Successful Runs')
        return df
    except:
        # Fall back to All Results if Successful Runs sheet doesn't exist
        df = pd.read_excel(filepath, sheet_name='All Results')
        return df[df['success'] == True]


def print_algorithm_comparison(df: pd.DataFrame):
    """Print comparison of algorithms."""
    print("\n" + "="*80)
    print("ALGORITHM COMPARISON")
    print("="*80)
    
    # Group by algorithm
    grouped = df.groupby('algorithm')
    
    metrics = {
        'Raw Reward': 'raw_reward',
        'Time (s)': 'elapsed_time',
        'Budget Used (%)': 'budget_used_pct',
        'Path Length': 'path_length'
    }
    
    for metric_name, column in metrics.items():
        if column not in df.columns:
            continue
        
        print(f"\n{metric_name}:")
        print("-" * 60)
        
        stats = grouped[column].agg(['count', 'mean', 'std', 'min', 'max'])
        print(stats.to_string())
    
    print("\n" + "="*80)


def print_dataset_performance(df: pd.DataFrame):
    """Print performance by dataset."""
    print("\n" + "="*80)
    print("PERFORMANCE BY DATASET")
    print("="*80)
    
    if 'dataset' not in df.columns:
        print("No dataset information available.")
        return
    
    # Group by dataset and algorithm
    grouped = df.groupby(['dataset', 'algorithm'])['raw_reward'].mean().unstack()
    
    print("\nAverage Raw Reward by Dataset:")
    print("-" * 80)
    print(grouped.to_string())
    
    print("\n" + "="*80)


def print_best_solutions(df: pd.DataFrame, n: int = 10):
    """Print best solutions found."""
    print("\n" + "="*80)
    print(f"TOP {n} SOLUTIONS")
    print("="*80)
    
    if 'raw_reward' not in df.columns:
        print("No reward information available.")
        return
    
    top = df.nlargest(n, 'raw_reward')
    
    cols_to_show = ['algorithm', 'problem_file', 'raw_reward', 'elapsed_time', 'path_length']
    cols_available = [col for col in cols_to_show if col in df.columns]
    
    print(top[cols_available].to_string(index=False))
    
    print("\n" + "="*80)


def print_efficiency_analysis(df: pd.DataFrame):
    """Analyze efficiency (reward per second)."""
    print("\n" + "="*80)
    print("EFFICIENCY ANALYSIS (Reward / Second)")
    print("="*80)
    
    if 'raw_reward' not in df.columns or 'elapsed_time' not in df.columns:
        print("Cannot calculate efficiency: missing reward or time data.")
        return
    
    # Calculate efficiency
    df_temp = df.copy()
    df_temp['efficiency'] = df_temp['raw_reward'] / df_temp['elapsed_time'].replace(0, np.nan)
    
    # Group by algorithm
    grouped = df_temp.groupby('algorithm')['efficiency'].agg(['mean', 'std', 'min', 'max'])
    
    print("\nEfficiency by Algorithm:")
    print("-" * 60)
    print(grouped.to_string())
    
    print("\n" + "="*80)


def print_parallel_speedup(df: pd.DataFrame):
    """Analyze parallel speedup if worker information is available."""
    print("\n" + "="*80)
    print("PARALLEL ALGORITHM ANALYSIS")
    print("="*80)
    
    # Filter to parallel algorithms
    parallel_algos = ['Simple_WU', 'VL']
    df_parallel = df[df['algorithm'].isin(parallel_algos)]
    
    if df_parallel.empty:
        print("No parallel algorithm results found.")
        return
    
    if 'num_workers' in df_parallel.columns:
        grouped = df_parallel.groupby(['algorithm', 'num_workers'])['elapsed_time'].mean().unstack()
        print("\nAverage Time by Worker Count:")
        print("-" * 60)
        print(grouped.to_string())
    
    # Compare parallel vs single-threaded
    if 'UCT' in df['algorithm'].values and not df_parallel.empty:
        uct_time = df[df['algorithm'] == 'UCT']['elapsed_time'].mean()
        
        print(f"\n\nSpeedup vs Single-Threaded UCT (baseline: {uct_time:.2f}s):")
        print("-" * 60)
        
        for algo in parallel_algos:
            algo_df = df_parallel[df_parallel['algorithm'] == algo]
            if not algo_df.empty:
                avg_time = algo_df['elapsed_time'].mean()
                speedup = uct_time / avg_time
                print(f"{algo:15s}: {avg_time:7.2f}s  (speedup: {speedup:.2f}x)")
    
    print("\n" + "="*80)


def generate_comparison_report(filepath: str, output: Optional[str] = None):
    """Generate a comprehensive comparison report."""
    print("="*80)
    print(f"BENCHMARK RESULTS ANALYSIS")
    print(f"File: {filepath}")
    print("="*80)
    
    # Load results
    df = load_results(filepath)
    
    print(f"\nTotal successful runs: {len(df)}")
    print(f"Algorithms tested: {', '.join(df['algorithm'].unique())}")
    
    if 'dataset' in df.columns:
        print(f"Datasets: {', '.join(df['dataset'].unique())}")
    
    # Run analyses
    print_algorithm_comparison(df)
    print_dataset_performance(df)
    print_efficiency_analysis(df)
    print_parallel_speedup(df)
    print_best_solutions(df, n=10)
    
    # Save report if requested
    if output:
        output_path = Path(output)
        with open(output_path, 'w') as f:
            # Redirect stdout to file
            original_stdout = sys.stdout
            sys.stdout = f
            
            print("="*80)
            print(f"BENCHMARK RESULTS ANALYSIS")
            print(f"File: {filepath}")
            print("="*80)
            
            print(f"\nTotal successful runs: {len(df)}")
            print(f"Algorithms tested: {', '.join(df['algorithm'].unique())}")
            
            print_algorithm_comparison(df)
            print_dataset_performance(df)
            print_efficiency_analysis(df)
            print_parallel_speedup(df)
            print_best_solutions(df, n=20)
            
            sys.stdout = original_stdout
        
        print(f"\n✓ Report saved to: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze benchmark results from Excel file',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('file', type=str,
                       help='Path to Excel results file')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='Save report to text file')
    parser.add_argument('--top', '-t', type=int, default=10,
                       help='Number of top solutions to show (default: 10)')
    
    args = parser.parse_args()
    
    # Check if file exists
    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}")
        return 1
    
    # Generate report
    try:
        generate_comparison_report(args.file, args.output)
        return 0
    except Exception as e:
        print(f"Error analyzing results: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
