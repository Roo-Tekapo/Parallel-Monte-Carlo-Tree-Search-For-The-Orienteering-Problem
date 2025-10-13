#!/usr/bin/env python3
"""
Batch script to run Simple WU-UCT on benchmark datasets.

This script runs WU-UCT on one representative file from each category in:
- parallel_friendly_v2: clustered, corridors, dense_grid, islands, sparse_grid, xlarge
- grid_patterns: corners, center, edges, diagonal, gradient, quadrants, checkerboard, ring, clustered, random
"""

import argparse
import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from orienteering.orienteering import OrienteeringProblem
from Simple_WU.simple_wu_coordinator import SimpleWUUCT


# Representative test files - one from each category
DEFAULT_PARALLEL_FRIENDLY_FILES = [
    "OP_Benchmark_Set/parallel_friendly_v2/clustered/clustered_c4_s5_sp8_32.txt",
    "OP_Benchmark_Set/parallel_friendly_v2/corridors/corridors_n4_l20_w3_24.txt",
    "OP_Benchmark_Set/parallel_friendly_v2/dense_grid/dense_20x20_r10_28.txt",
    "OP_Benchmark_Set/parallel_friendly_v2/islands/islands_n6_s5_b30_28.txt",
    "OP_Benchmark_Set/parallel_friendly_v2/sparse_grid/sparse_30x30_d50_44.txt",
    "OP_Benchmark_Set/parallel_friendly_v2/xlarge/xlarge_40x40_r0_84.txt",
]

# Grid pattern test files - one from each pattern type
DEFAULT_GRID_PATTERN_FILES = [
    "OP_Benchmark_Set/grid_patterns/grid_corners_b30.txt",
    "OP_Benchmark_Set/grid_patterns/grid_center_b30.txt",
    "OP_Benchmark_Set/grid_patterns/grid_edges_b30.txt",
    "OP_Benchmark_Set/grid_patterns/grid_diagonal_b30.txt",
    "OP_Benchmark_Set/grid_patterns/grid_grad_horiz_b30.txt",
    "OP_Benchmark_Set/grid_patterns/grid_quadrants_b30.txt",
    "OP_Benchmark_Set/grid_patterns/grid_checkerboard_b30.txt",
    "OP_Benchmark_Set/grid_patterns/grid_ring_b30.txt",
    "OP_Benchmark_Set/grid_patterns/grid_clustered_b30.txt",
    "OP_Benchmark_Set/grid_patterns/grid_random_b30.txt",
]


def run_wu_uct_on_file(problem_file: str, 
                       max_iterations: int = 10000,
                       num_workers: int = 4,
                       exploration_constant: float = 1.414,
                       max_time: float = None,
                       verbose: bool = False):
    """
    Run Simple WU-UCT on a single problem file.
    
    Args:
        problem_file: Path to orienteering problem file
        max_iterations: Maximum number of iterations
        num_workers: Number of unified workers
        exploration_constant: UCT exploration constant
        max_time: Maximum time limit in seconds (optional)
        verbose: Whether to print detailed output
        
    Returns:
        Dictionary with results and statistics
    """
    
    # Load the problem
    if verbose:
        print(f"Loading problem from: {problem_file}")
    
    try:
        nodes, budget = OrienteeringProblem.load_problem(problem_file)
        problem = OrienteeringProblem(nodes, budget)
    except Exception as e:
        print(f"ERROR: Failed to load problem file {problem_file}: {e}")
        return None
    
    if verbose:
        print(f"  Nodes: {problem.num_nodes}, Budget: {problem.budget}")
    
    # Create and run Simple WU-UCT
    simple_wu_uct = SimpleWUUCT(
        problem=problem,
        num_workers=num_workers,
        exploration_constant=exploration_constant,
        max_distance=problem.budget
    )
    
    start_time = time.time()
    
    try:
        best_state = simple_wu_uct.run(
            max_iterations=max_iterations,
            max_time=max_time,
            verbose=verbose
        )
    except Exception as e:
        print(f"ERROR: Failed to run algorithm on {problem_file}: {e}")
        return None
    
    execution_time = time.time() - start_time
    
    # Get tree statistics
    tree_stats = simple_wu_uct.get_tree_statistics()
    
    result = {
        'problem_file': problem_file,
        'problem_name': os.path.basename(problem_file),
        'num_nodes': problem.num_nodes,
        'budget': problem.budget,
        'path': best_state.path,
        'reward': best_state.reward_so_far,
        'cost': best_state.cost_so_far,
        'execution_time': execution_time,
        'tree_nodes': tree_stats['nodes'],
        'tree_depth': tree_stats['max_depth'],
        'tree_visits': tree_stats['total_visits'],
        'iterations': max_iterations,
        'num_workers': num_workers
    }
    
    if verbose:
        print(f"  Best reward: {result['reward']}")
        print(f"  Path length: {len(result['path'])}")
        print(f"  Cost: {result['cost']:.2f}")
        print(f"  Time: {result['execution_time']:.2f}s")
    
    return result


def run_batch(test_files=None,
              dataset: str = 'parallel_friendly',
              max_iterations: int = 10000,
              num_workers: int = 4,
              exploration_constant: float = 1.414,
              max_time: float = None,
              verbose: bool = False,
              output_dir: str = None):
    """
    Run Simple WU-UCT on a batch of problem files.
    
    Args:
        test_files: List of problem files to test (uses dataset defaults if None)
        dataset: Which dataset to use - 'parallel_friendly' or 'grid_patterns' (default: 'parallel_friendly')
        max_iterations: Maximum iterations per problem
        num_workers: Number of unified workers
        exploration_constant: UCT exploration constant
        max_time: Maximum time per problem (optional)
        verbose: Whether to print detailed output
        output_dir: Directory to save results (defaults to Simple_WU/)
        
    Returns:
        List of result dictionaries
    """
    
    if test_files is None:
        if dataset == 'grid_patterns':
            test_files = DEFAULT_GRID_PATTERN_FILES
            dataset_name = "Grid Patterns"
        else:
            test_files = DEFAULT_PARALLEL_FRIENDLY_FILES
            dataset_name = "Parallel Friendly"
    else:
        dataset_name = "Custom"
    
    # Resolve file paths relative to project root
    base_path = Path(__file__).parent.parent
    resolved_files = []
    for f in test_files:
        full_path = base_path / f
        if not full_path.exists():
            print(f"WARNING: File not found: {full_path}")
        else:
            resolved_files.append(str(full_path))
    
    if not resolved_files:
        print("ERROR: No valid test files found!")
        return []
    
    print(f"\n{'='*80}")
    print(f"Simple WU-UCT Batch Run - {dataset_name} Dataset")
    print(f"{'='*80}")
    print(f"Test files: {len(resolved_files)}")
    print(f"Max iterations per file: {max_iterations}")
    if max_time:
        print(f"Max time per file: {max_time}s")
    print(f"Number of workers: {num_workers}")
    print(f"Exploration constant: {exploration_constant}")
    print(f"{'='*80}\n")
    
    results = []
    
    for i, problem_file in enumerate(resolved_files, 1):
        print(f"\n[{i}/{len(resolved_files)}] Running: {os.path.basename(problem_file)}")
        print("-" * 80)
        
        result = run_wu_uct_on_file(
            problem_file=problem_file,
            max_iterations=max_iterations,
            num_workers=num_workers,
            exploration_constant=exploration_constant,
            max_time=max_time,
            verbose=verbose
        )
        
        if result:
            results.append(result)
            print(f"✓ Completed: Reward={result['reward']}, Time={result['execution_time']:.2f}s")
        else:
            print(f"✗ Failed to run on this problem")
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"BATCH RUN SUMMARY")
    print(f"{'='*80}")
    print(f"Total problems: {len(resolved_files)}")
    print(f"Successful runs: {len(results)}")
    print(f"Failed runs: {len(resolved_files) - len(results)}")
    print()
    
    if results:
        print(f"{'Problem':<45} {'Nodes':<7} {'Reward':<8} {'Time(s)':<8}")
        print("-" * 80)
        for result in results:
            print(f"{result['problem_name']:<45} {result['num_nodes']:<7} {result['reward']:<8} {result['execution_time']:<8.2f}")
        
        # Overall statistics
        total_time = sum(r['execution_time'] for r in results)
        total_reward = sum(r['reward'] for r in results)
        avg_time = total_time / len(results)
        
        print("-" * 80)
        print(f"Total execution time: {total_time:.2f}s")
        print(f"Average time per problem: {avg_time:.2f}s")
        print(f"Total reward collected: {total_reward}")
    
    # Save results to file
    if output_dir is None:
        output_dir = Path(__file__).parent / 'results'
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = output_dir / f"batch_results_{timestamp}.txt"
    
    try:
        with open(results_file, 'w') as f:
            f.write(f"# Simple WU-UCT Batch Results\n")
            f.write(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Max iterations: {max_iterations}\n")
            if max_time:
                f.write(f"# Max time per problem: {max_time}s\n")
            f.write(f"# Number of workers: {num_workers}\n")
            f.write(f"# Exploration constant: {exploration_constant}\n")
            f.write(f"#\n")
            f.write(f"# Results:\n")
            f.write(f"#\n")
            
            for result in results:
                f.write(f"\n## {result['problem_name']}\n")
                f.write(f"Problem file: {result['problem_file']}\n")
                f.write(f"Nodes: {result['num_nodes']}\n")
                f.write(f"Budget: {result['budget']}\n")
                f.write(f"Path: {' -> '.join(map(str, result['path']))}\n")
                f.write(f"Reward: {result['reward']}\n")
                f.write(f"Cost: {result['cost']:.2f}\n")
                f.write(f"Execution time: {result['execution_time']:.2f}s\n")
                f.write(f"Tree nodes: {result['tree_nodes']}\n")
                f.write(f"Tree depth: {result['tree_depth']}\n")
                f.write(f"Tree visits: {result['tree_visits']}\n")
                f.write(f"\n")
            
            # Summary statistics
            f.write(f"\n{'='*80}\n")
            f.write(f"SUMMARY\n")
            f.write(f"{'='*80}\n")
            f.write(f"Total problems: {len(resolved_files)}\n")
            f.write(f"Successful runs: {len(results)}\n")
            f.write(f"Total execution time: {total_time:.2f}s\n")
            f.write(f"Average time per problem: {avg_time:.2f}s\n")
            f.write(f"Total reward collected: {total_reward}\n")
        
        print(f"\nResults saved to: {results_file}")
    except Exception as e:
        print(f"ERROR: Failed to save results: {e}")
    
    return results


def main():
    """
    Main function with command-line argument parsing.
    """
    parser = argparse.ArgumentParser(
        description='Run Simple WU-UCT on benchmark datasets (parallel_friendly_v2 or grid_patterns)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run parallel_friendly dataset with default settings
  python run_parallel_friendly_batch.py
  
  # Run grid_patterns dataset
  python run_parallel_friendly_batch.py --dataset grid_patterns
  
  # Run with custom iterations and workers
  python run_parallel_friendly_batch.py --max-iterations 20000 --num-workers 8
  
  # Run with time limit instead of iteration limit
  python run_parallel_friendly_batch.py --max-time 60 --dataset grid_patterns
  
  # Run on specific files
  python run_parallel_friendly_batch.py --files file1.txt file2.txt file3.txt
  
  # Run with verbose output
  python run_parallel_friendly_batch.py --verbose
        """
    )
    
    parser.add_argument('--dataset', type=str, default='parallel_friendly',
                       choices=['parallel_friendly', 'grid_patterns'],
                       help='Dataset to use: parallel_friendly or grid_patterns (default: parallel_friendly)')
    parser.add_argument('--files', type=str, nargs='+',
                       help='Specific problem files to test (relative to project root)')
    parser.add_argument('--max-iterations', type=int, default=10000,
                       help='Maximum number of iterations per problem (default: 10000)')
    parser.add_argument('--max-time', type=float, default=None,
                       help='Maximum time in seconds per problem (optional)')
    parser.add_argument('--num-workers', type=int, default=4,
                       help='Number of unified workers (default: 4)')
    parser.add_argument('--exploration-constant', type=float, default=1.414,
                       help='UCT exploration constant (default: 1.414)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output for each problem')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Directory to save results (default: Simple_WU/)')
    
    args = parser.parse_args()
    
    # Run batch
    results = run_batch(
        test_files=args.files,
        dataset=args.dataset,
        max_iterations=args.max_iterations,
        num_workers=args.num_workers,
        exploration_constant=args.exploration_constant,
        max_time=args.max_time,
        verbose=args.verbose,
        output_dir=args.output_dir
    )
    
    # Exit with appropriate code
    if results:
        print(f"\n✓ Batch run completed successfully!")
        sys.exit(0)
    else:
        print(f"\n✗ Batch run failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
