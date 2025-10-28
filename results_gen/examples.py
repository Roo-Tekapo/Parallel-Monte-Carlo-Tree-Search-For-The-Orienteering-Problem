#!/usr/bin/env python3
"""
Example: Using BenchmarkRunner Programmatically

This example shows how to use the BenchmarkRunner class
directly in your own Python scripts for custom benchmarking needs.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from run_benchmark import BenchmarkRunner


def example_custom_benchmark():
    """Example: Run a custom benchmark configuration."""
    
    print("Example: Custom Benchmark")
    print("="*80)
    
    # Initialize runner
    runner = BenchmarkRunner()
    
    # Get specific problem files
    problem_files = runner.get_problem_files('sample')
    
    # Select first 3 problems for quick test
    test_problems = problem_files[:3]
    
    print(f"Testing on {len(test_problems)} problems:")
    for p in test_problems:
        print(f"  - {p.name}")
    
    # Run benchmark with custom parameters
    runner.run_benchmark(
        problem_files=test_problems,
        algorithms=['uct', 'vl'],  # Only test UCT and VL
        max_iterations=5000,
        num_workers=4,
        vl_value=1.5,  # Custom VL value
        verbose=True
    )
    
    # Save results
    output_file = runner.save_results_to_excel('custom_benchmark.xlsx')
    print(f"\nResults saved to: {output_file}")


def example_algorithm_comparison():
    """Example: Compare parallel algorithms with different worker counts."""
    
    print("\nExample: Worker Count Comparison")
    print("="*80)
    
    runner = BenchmarkRunner()
    problems = runner.get_problem_files('grid_sample')[:5]  # First 5 problems
    
    worker_counts = [2, 4, 8]
    
    for workers in worker_counts:
        print(f"\nTesting with {workers} workers...")
        
        # Run only parallel algorithms
        runner.run_benchmark(
            problem_files=problems,
            algorithms=['simple_wu', 'vl'],
            max_iterations=5000,
            num_workers=workers,
            verbose=False  # Quiet mode
        )
    
    # Save consolidated results
    output_file = runner.save_results_to_excel('worker_comparison.xlsx')
    print(f"\nAll results saved to: {output_file}")


def example_single_algorithm_test():
    """Example: Test a single algorithm on a single problem."""
    
    print("\nExample: Single Algorithm Test")
    print("="*80)
    
    runner = BenchmarkRunner()
    
    # Get first problem file
    problems = runner.get_problem_files('sample')
    if not problems:
        print("No problems found!")
        return
    
    test_problem = problems[0]
    print(f"Testing problem: {test_problem.name}")
    
    # Test VL algorithm with custom parameters
    result = runner.run_vl(
        problem_file=test_problem,
        max_iterations=10000,
        num_workers=4,
        vl_value=2.0
    )
    
    if result['success']:
        print("\n✓ Success!")
        print(f"  Reward: {result['raw_reward']:.2f}")
        print(f"  Time: {result['elapsed_time']:.2f}s")
        print(f"  Path: {result['best_path']}")
    else:
        print(f"\n✗ Failed: {result['error']}")


def example_dataset_sweep():
    """Example: Test all algorithms on all datasets (comprehensive)."""
    
    print("\nExample: Complete Dataset Sweep")
    print("="*80)
    print("WARNING: This will take a long time!")
    
    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    runner = BenchmarkRunner()
    
    datasets = ['sample', 'grid_sample', 'set_64_1']
    
    for dataset in datasets:
        print(f"\n{'='*80}")
        print(f"Processing dataset: {dataset}")
        print('='*80)
        
        problems = runner.get_problem_files(dataset)
        
        if not problems:
            print(f"No problems found in {dataset}, skipping...")
            continue
        
        runner.run_benchmark(
            problem_files=problems,
            algorithms=['uct', 'simple_wu', 'vl', 'ortools'],
            max_iterations=10000,
            num_workers=4,
            verbose=True
        )
    
    # Save all results
    output_file = runner.save_results_to_excel('complete_sweep.xlsx')
    print(f"\n{'='*80}")
    print(f"Complete sweep finished!")
    print(f"Results saved to: {output_file}")
    print('='*80)


def main():
    """Main menu for examples."""
    
    print("="*80)
    print("BenchmarkRunner - Programmatic Usage Examples")
    print("="*80)
    print("\nAvailable examples:")
    print("  1. Custom benchmark configuration")
    print("  2. Worker count comparison")
    print("  3. Single algorithm test")
    print("  4. Complete dataset sweep (WARNING: slow!)")
    print("  5. Run all quick examples (1-3)")
    print("\n  0. Exit")
    
    choice = input("\nSelect example (0-5): ").strip()
    
    if choice == '1':
        example_custom_benchmark()
    elif choice == '2':
        example_algorithm_comparison()
    elif choice == '3':
        example_single_algorithm_test()
    elif choice == '4':
        example_dataset_sweep()
    elif choice == '5':
        example_custom_benchmark()
        example_algorithm_comparison()
        example_single_algorithm_test()
    elif choice == '0':
        print("Exiting...")
    else:
        print("Invalid choice!")


if __name__ == '__main__':
    main()
