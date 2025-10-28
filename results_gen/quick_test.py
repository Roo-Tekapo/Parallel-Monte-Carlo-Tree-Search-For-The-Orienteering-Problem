#!/usr/bin/env python3
"""
Quick test script to verify all algorithms work before running full benchmark.
This runs each algorithm once on a single small problem.
"""

import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from run_benchmark import BenchmarkRunner


def main():
    print("="*80)
    print("Quick Algorithm Test")
    print("="*80)
    print("\nThis will test each algorithm on a small grid problem.")
    print("Each algorithm will run with reasonable iterations (5000) to verify")
    print("it produces good results. This may take a minute or two.\n")
    
    # Initialize runner
    runner = BenchmarkRunner()
    
    # Get a small test problem
    test_problems = runner.get_problem_files('grid_sample')
    if not test_problems:
        print("Error: No grid_sample problems found!")
        return 1
    
    # Use the first (typically smallest) problem
    test_problem = test_problems[0]
    print(f"Test problem: {test_problem.name}\n")
    
    algorithms = ['uct', 'simple_wu', 'vl', 'ortools']
    
    # Test each algorithm with reasonable iterations for meaningful results
    # (enough to verify they work and produce decent solutions)
    for algo in algorithms:
        print(f"Testing {algo.upper()}...", end=' ', flush=True)
        
        try:
            if algo == 'uct':
                result = runner.run_uct_single(test_problem, max_iterations=10000)
            elif algo == 'simple_wu':
                result = runner.run_simple_wu(test_problem, max_iterations=10000, num_workers=4)
            elif algo == 'vl':
                result = runner.run_vl(test_problem, max_iterations=10000, num_workers=4)
            elif algo == 'ortools':
                result = runner.run_ortools(test_problem, time_limit=5)
            
            if result['success']:
                print(f"✓ Success (Reward: {result.get('raw_reward', 'N/A')})")
            else:
                error_msg = result.get('error', 'Unknown error')
                # Check if it's just missing ortools
                if algo == 'ortools' and 'ortools' in error_msg.lower():
                    print(f"⚠ Skipped (OR-Tools not installed)")
                    print("      Install with: pip install ortools")
                else:
                    print(f"✗ Failed: {error_msg}")
                    print(f"\nTraceback:\n{result.get('traceback', 'No traceback available')}")
                    return 1
                
        except Exception as e:
            print(f"✗ Exception: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    print("\n" + "="*80)
    print("✓ All available algorithms tested successfully!")
    print("="*80)
    print("\nYou can now run the full benchmark with:")
    print("  python run_benchmark.py --dataset grid_sample --algorithms uct simple_wu vl")
    print("\nOr see README.md for more options.")
    print("\nNote: To use OR-Tools, install it with: pip install ortools")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
