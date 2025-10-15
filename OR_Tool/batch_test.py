"""
Batch testing script for OR-Tools solver across all benchmark sets.

This script runs the OR-Tools solver on multiple benchmark directories
and generates a comprehensive comparison report.
"""

import os
import sys
import json
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from or_tools_solver import solve_benchmark_problem, ORToolsOrienteeringSolver
from orienteering.orienteering import OrienteeringProblem


def run_comprehensive_benchmark(benchmark_base_dir: str = "OP_Benchmark_Set",
                                time_limits: dict = None,
                                output_file: str = "or_tools_benchmark_results.json"):
    """
    Run OR-Tools on all benchmark sets with appropriate time limits.
    
    Args:
        benchmark_base_dir: Base directory containing benchmark sets
        time_limits: Dictionary mapping directory name to time limit in seconds
        output_file: Output JSON file for results
    """
    
    if time_limits is None:
        # Default time limits based on problem size
        time_limits = {
            'sample': 10,
            'grid_sample': 30,
            'grid_patterns': 30,
            'parallel_friendly_v2': 60,
            'set_64_1': 60,
            'set_100_1': 120,
            'set_1000_1': 300,
            'Tsiligirides_1': 60
        }
    
    print("="*80)
    print("OR-TOOLS COMPREHENSIVE BENCHMARK TEST")
    print("="*80)
    print(f"\nBenchmark directory: {benchmark_base_dir}")
    print(f"Output file: {output_file}")
    print("\nTime limits:")
    for dir_name, limit in time_limits.items():
        print(f"  {dir_name}: {limit}s")
    
    all_results = []
    start_time = time.time()
    
    # Process each benchmark directory
    for dir_name, time_limit in time_limits.items():
        dir_path = os.path.join(benchmark_base_dir, dir_name)
        
        if not os.path.exists(dir_path):
            print(f"\n⚠ Skipping {dir_name}: directory not found")
            continue
        
        print(f"\n{'='*80}")
        print(f"BENCHMARK SET: {dir_name}")
        print(f"{'='*80}")
        
        # Find all .txt files in directory
        problem_files = []
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.txt') and not file.startswith('.'):
                    problem_files.append(os.path.join(root, file))
        
        if not problem_files:
            print(f"  No problem files found in {dir_path}")
            continue
        
        print(f"Found {len(problem_files)} problems")
        
        # Solve each problem
        dir_results = []
        for i, problem_file in enumerate(sorted(problem_files), 1):
            print(f"\n[{i}/{len(problem_files)}] {os.path.basename(problem_file)}")
            print("-"*60)
            
            result = solve_benchmark_problem(
                problem_file,
                time_limit=time_limit,
                verbose=False  # Keep output minimal for batch
            )
            
            if result:
                # Print brief summary
                print(f"  Reward: {result['reward']:.2f}, "
                      f"Distance: {result['distance']:.2f}/{result['budget']:.2f}, "
                      f"Time: {result['solve_time']:.2f}s, "
                      f"Nodes: {len(result['path'])}/{result['num_nodes']}")
                
                dir_results.append(result)
                all_results.append({
                    'benchmark_set': dir_name,
                    **result
                })
        
        # Print summary for this directory
        if dir_results:
            print(f"\n{'-'*60}")
            print(f"Summary for {dir_name}:")
            print(f"  Problems solved: {len(dir_results)}")
            print(f"  Total reward: {sum(r['reward'] for r in dir_results):.2f}")
            print(f"  Avg solve time: {sum(r['solve_time'] for r in dir_results)/len(dir_results):.2f}s")
    
    total_time = time.time() - start_time
    
    # Save results to JSON
    print(f"\n{'='*80}")
    print("SAVING RESULTS")
    print(f"{'='*80}")
    
    results_data = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_time_seconds': total_time,
        'total_problems': len(all_results),
        'results': all_results
    }
    
    with open(output_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"Results saved to: {output_file}")
    
    # Print final summary
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"Total problems solved: {len(all_results)}")
    print(f"Total reward collected: {sum(r['reward'] for r in all_results):.2f}")
    print(f"Total benchmark time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
    print(f"Average time per problem: {total_time/len(all_results):.2f}s")
    
    # Summary by benchmark set
    print(f"\n{'='*80}")
    print("RESULTS BY BENCHMARK SET")
    print(f"{'='*80}")
    print(f"{'Benchmark Set':<25} {'Problems':<10} {'Avg Reward':<12} {'Avg Time':<10}")
    print("-"*80)
    
    benchmark_sets = {}
    for result in all_results:
        bm_set = result['benchmark_set']
        if bm_set not in benchmark_sets:
            benchmark_sets[bm_set] = []
        benchmark_sets[bm_set].append(result)
    
    for bm_set, results in sorted(benchmark_sets.items()):
        avg_reward = sum(r['reward'] for r in results) / len(results)
        avg_time = sum(r['solve_time'] for r in results) / len(results)
        print(f"{bm_set:<25} {len(results):<10} {avg_reward:<12.2f} {avg_time:<10.2f}s")
    
    print("="*80)
    
    return all_results


def compare_with_mcts_results(or_tools_file: str = "or_tools_benchmark_results.json",
                              mcts_output_dir: str = "UCT/uct-output"):
    """
    Compare OR-Tools results with existing MCTS results.
    
    Args:
        or_tools_file: JSON file with OR-Tools results
        mcts_output_dir: Directory containing MCTS output files
    """
    
    print("="*80)
    print("COMPARING OR-TOOLS vs MCTS RESULTS")
    print("="*80)
    
    # Load OR-Tools results
    if not os.path.exists(or_tools_file):
        print(f"OR-Tools results file not found: {or_tools_file}")
        return
    
    with open(or_tools_file, 'r') as f:
        or_data = json.load(f)
    
    print(f"\nLoaded {len(or_data['results'])} OR-Tools results")
    print(f"Searching for MCTS results in: {mcts_output_dir}")
    
    # This is a placeholder - you would need to implement parsing of your MCTS output format
    print("\nNote: Implement MCTS output parsing based on your specific output format")
    print("      to enable detailed comparison.")


def quick_test():
    """Quick test on sample problems."""
    print("="*80)
    print("QUICK TEST - Sample Problems")
    print("="*80)
    
    sample_dir = "OP_Benchmark_Set/sample"
    
    if not os.path.exists(sample_dir):
        print(f"Sample directory not found: {sample_dir}")
        return
    
    import glob
    problems = glob.glob(os.path.join(sample_dir, "*.txt"))
    
    print(f"\nFound {len(problems)} sample problems")
    
    results = []
    for problem_file in problems:
        print(f"\nSolving: {os.path.basename(problem_file)}")
        result = solve_benchmark_problem(problem_file, time_limit=10, verbose=True)
        if result:
            results.append(result)
    
    print(f"\n{'='*80}")
    print(f"Completed {len(results)} problems")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Batch testing for OR-Tools orienteering solver"
    )
    parser.add_argument(
        '--mode',
        choices=['quick', 'full', 'compare'],
        default='quick',
        help='Test mode: quick (sample only), full (all benchmarks), compare (with MCTS)'
    )
    parser.add_argument(
        '--output',
        default='or_tools_benchmark_results.json',
        help='Output JSON file (default: or_tools_benchmark_results.json)'
    )
    parser.add_argument(
        '--benchmark-dir',
        default='OP_Benchmark_Set',
        help='Benchmark directory (default: OP_Benchmark_Set)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'quick':
        quick_test()
    
    elif args.mode == 'full':
        run_comprehensive_benchmark(
            benchmark_base_dir=args.benchmark_dir,
            output_file=args.output
        )
    
    elif args.mode == 'compare':
        compare_with_mcts_results(or_tools_file=args.output)
    
    print("\n✅ Batch test complete!")
