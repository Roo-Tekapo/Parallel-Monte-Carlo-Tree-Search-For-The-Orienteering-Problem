#!/usr/bin/env python3
"""
Main entry point for Simple WU-UCT implementation.

This demonstrates how to use the simplified WU-UCT algorithm
with unified workers for solving orienteering problems.
"""

import argparse
import sys
import os
import time
import math
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


def run_simple_wu_uct(problem_file: str, 
                     max_iterations: int = 10000,
                     num_workers: int = 4,
                     max_distance: float = None,
                     max_time: float = None,
                     verbose: bool = True,
                     use_no_end: bool = False):
    """
    Run Simple WU-UCT on a given problem file.
    
    Args:
        problem_file: Path to orienteering problem file
        max_iterations: Maximum number of iterations
        num_workers: Number of unified workers
        max_distance: Maximum distance constraint (overrides problem budget if specified)
        max_time: Maximum time limit in seconds (optional)
        verbose: Whether to print detailed output
        use_no_end: Use no-end orienteering variant
        
    Returns:
        Tuple of (best_state, execution_time)
    """
    
    # Set the variant BEFORE importing modules
    os.environ['SIMPLE_WU_USE_NO_END'] = 'true' if use_no_end else 'false'
    
    # Import modules (they will use the adapter which reads the env var)
    from Simple_WU.simple_wu_coordinator import SimpleWUUCT
    from Simple_WU.orienteering_adapter import OrienteeringProblem, START_NODE, get_variant
    
    variant_name = get_variant()
    
    # Load the problem
    print(f"Loading problem from: {problem_file}")
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
    
    # Use provided max_distance or default to problem budget
    effective_max_distance = max_distance if max_distance is not None else problem.budget
    
    if verbose:
        print(f"Problem: {problem.num_nodes} nodes, budget: {problem.budget}")
        if max_distance is not None:
            print(f"Using custom max distance: {max_distance} (original budget: {problem.budget})")
        print(f"Variant: {variant_name} Orienteering")
        print(f"Initial state reward: {problem.nodes[START_NODE].score}")
    
    # Create and run Simple WU-UCT
    simple_wu_uct = SimpleWUUCT(
        problem=problem,
        num_workers=num_workers,
        exploration_constant=1.414,  # √2
        max_distance=effective_max_distance
    )
    
    start_time = time.time()
    
    best_state = simple_wu_uct.run(
        max_iterations=max_iterations,
        max_time=max_time,
        verbose=verbose
    )
    
    execution_time = time.time() - start_time
    
    if verbose:
        print(f"\nBest solution found:")
        print(f"  Path: {' -> '.join(map(str, best_state.path))}")
        print(f"  Reward: {best_state.reward_so_far}")
        print(f"  Distance: {best_state.cost_so_far:.2f}")
        print(f"  Execution time: {execution_time:.2f}s")
        
        # Get tree statistics
        tree_stats = simple_wu_uct.get_tree_statistics()
        print(f"\nTree Statistics:")
        print(f"  Total nodes: {tree_stats['nodes']}")
        print(f"  Maximum depth: {tree_stats['max_depth']}")
        print(f"  Total visits: {tree_stats['total_visits']}")
        
    return best_state, execution_time


def main():
    """
    Main function with command-line argument parsing using argparse.
    """
    parser = argparse.ArgumentParser(description='Simple WU-UCT algorithm for the Orienteering Problem')
    
    parser.add_argument('--problem-file', '-p', type=str, required=True,
                       help='Path to the orienteering problem file')
    parser.add_argument('--max-iterations', type=int, default=10000,
                       help='Maximum number of iterations (default: 10000)')
    parser.add_argument('--max-time', type=float, default=None,
                       help='Maximum time in seconds (optional, overrides max-iterations if specified)')
    parser.add_argument('--exploration-constant', type=float, default=math.sqrt(2),
                       help='UCT exploration constant (default: sqrt(2))')
    parser.add_argument('--num-workers', '-n', type=int, default=4,
                       help='Number of unified workers (default: 4)')
    parser.add_argument('--max-distance', type=float, default=1.42,
                       help='Maximum distance constraint (default: 1.42, overrides problem budget)')
    parser.add_argument('--use-no-end', '-no-end', action='store_true',
                       help='Use no-end orienteering variant (maximize reward without end node requirement)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--output-file', type=str,
                       help='Output file to save results')
    
    args = parser.parse_args()
    
    # Set the variant BEFORE importing Simple_WU modules
    os.environ['SIMPLE_WU_USE_NO_END'] = 'true' if args.use_no_end else 'false'
    
    # Now import Simple_WU modules (they will use the adapter which reads the env var)
    from Simple_WU.simple_wu_coordinator import SimpleWUUCT
    from Simple_WU.orienteering_adapter import OrienteeringProblem, get_variant
    
    variant_name = get_variant()
    
    # Load problem
    try:
        nodes, budget = OrienteeringProblem.load_problem(args.problem_file)
        problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
        
        if args.verbose:
            print(f"Loaded problem: {len(nodes)} nodes, budget: {budget}")
            print(f"Problem file: {args.problem_file}")
            print(f"Variant: {variant_name} Orienteering")
            if args.max_distance:
                print(f"Max distance limit: {args.max_distance}")
            if args.max_time:
                print(f"Max time: {args.max_time} seconds")
    except Exception as e:
        print(f"ERROR: Failed to load problem file: {e}")
        sys.exit(1)
    
    # Run Simple WU-UCT
    start_time = time.time()
    
    if args.verbose:
        if args.max_time:
            print(f"Running Simple WU-UCT with max time {args.max_time}s")
        else:
            print(f"Running Simple WU-UCT with {args.max_iterations} iterations")
        print(f"Number of workers: {args.num_workers}")
        print(f"Exploration constant: {args.exploration_constant}")
    
    # Use provided max_distance or default to problem budget
    effective_max_distance = args.max_distance if args.max_distance is not None else budget
    
    simple_wu_uct = SimpleWUUCT(
        problem=problem,
        num_workers=args.num_workers,
        exploration_constant=args.exploration_constant,
        max_distance=effective_max_distance
    )
    
    best_state = simple_wu_uct.run(
        max_iterations=args.max_iterations,
        max_time=args.max_time,
        verbose=args.verbose
    )
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    if args.verbose:
        tree_stats = simple_wu_uct.get_tree_statistics()
        print(f"\nTree Statistics:")
        print(f"  Total nodes: {tree_stats['nodes']}")
        print(f"  Maximum depth: {tree_stats['max_depth']}")
        print(f"  Total visits: {tree_stats['total_visits']}")
    
    # Print results
    # Calculate raw reward by summing actual node scores
    raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.path)
    
    print(f"\nResults:")
    print(f"Algorithm: Simple WU-UCT")
    print(f"Best path: {' -> '.join(map(str, best_state.path))}")
    if problem.normalize_rewards:
        print(f"Normalized reward: {best_state.reward_so_far}")
        print(f"Raw reward: {raw_reward}")
    else:
        print(f"Total reward: {best_state.reward_so_far}")
        print(f"  (Same as raw reward: {raw_reward})")
    print(f"Total cost: {best_state.cost_so_far:.2f}")
    print(f"Execution time: {elapsed_time:.2f} seconds")
    
    # Save results to file if specified or create default filename
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(script_dir, 'results')
    
    if args.output_file:
        output_file = args.output_file
        # If output file doesn't have path, put it in results directory
        if not os.path.isabs(output_file):
            output_file = os.path.join(results_dir, output_file)
    else:
        # Create default filename in results directory
        problem_name = os.path.splitext(os.path.basename(args.problem_file))[0]
        output_file = os.path.join(results_dir, f"simple-wu-uct_{problem_name}_{args.max_iterations}.txt")
    
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(f"# Simple WU-UCT Results\n")
            f.write(f"# Problem: {args.problem_file}\n")
            f.write(f"# Iterations: {args.max_iterations}\n")
            if args.max_time:
                f.write(f"# Max time: {args.max_time}s\n")
            f.write(f"# Exploration constant: {args.exploration_constant}\n")
            f.write(f"# Number of workers: {args.num_workers}\n")
            if args.max_distance:
                f.write(f"# Max distance: {args.max_distance}\n")
            f.write(f"# Execution time: {elapsed_time:.2f}s\n")
            f.write(f"#\n")
            f.write(f"Path= {' '.join(map(str, best_state.path))}\n")
            f.write(f"Reward= {best_state.reward_so_far}\n")
            f.write(f"Cost= {best_state.cost_so_far}\n")
        
        print(f"Results saved to: {output_file}")
    except Exception as e:
        print(f"ERROR: Failed to save results to file: {e}")


def run_benchmark_comparison():
    """
    Run a comparison between different configurations.
    """
    print("Running Simple WU-UCT Benchmark Comparison")
    print("=" * 50)
    
    # Test problem
    problem_file = "../../OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    
    if not os.path.exists(problem_file):
        print(f"Benchmark problem file not found: {problem_file}")
        return
    
    configurations = [
        {"workers": 1, "iterations": 5000, "max_distance": None},
        {"workers": 2, "iterations": 5000, "max_distance": None},
        {"workers": 4, "iterations": 5000, "max_distance": None},
        {"workers": 8, "iterations": 5000, "max_distance": None},
    ]
    
    results = []
    
    for config in configurations:
        print(f"\nTesting {config['workers']} workers, {config['iterations']} iterations")
        print("-" * 40)
        
        best_state, execution_time = run_simple_wu_uct(
            problem_file=problem_file,
            max_iterations=config['iterations'],
            num_workers=config['workers'],
            max_distance=config['max_distance'],
            verbose=False,
            use_no_end=False  # Use traditional for benchmark
        )
        
        results.append({
            **config,
            'reward': best_state.reward_so_far,
            'time': execution_time,
            'iterations_per_second': config['iterations'] / execution_time
        })
        
        print(f"  Result: reward={best_state.reward_so_far}, time={execution_time:.2f}s")
    
    # Print summary
    print(f"\nBenchmark Results Summary")
    print("=" * 50)
    print(f"{'Workers':<8} {'Reward':<8} {'Time(s)':<8} {'Iter/s':<10}")
    print("-" * 40)
    
    for result in results:
        print(f"{result['workers']:<8} {result['reward']:<8} {result['time']:<8.2f} {result['iterations_per_second']:<10.1f}")


if __name__ == "__main__":
    # Check if benchmark mode is requested
    if len(sys.argv) > 1 and sys.argv[1] == "--benchmark":
        run_benchmark_comparison()
    else:
        main()