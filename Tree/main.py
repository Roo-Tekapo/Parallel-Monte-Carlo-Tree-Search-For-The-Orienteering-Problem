#!/usr/bin/env python3
"""
Main entry point for Tree-Parallel MCTS implementation.

This demonstrates how to use the tree-parallel MCTS algorithm
with standard UCT (no WU-UCT modifications) for solving orienteering problems.
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


def run_tree_parallel_mcts(problem_file: str, 
                          max_iterations: int = 10000,
                          num_workers: int = 4,
                          exploration_constant: float = math.sqrt(2),
                          max_time: float = None,
                          verbose: bool = True,
                          use_optimized: bool = True,
                          use_no_end: bool = False):
    """
    Run Tree-Parallel MCTS on a given problem file.
    
    Args:
        problem_file: Path to orienteering problem file
        max_iterations: Maximum number of iterations
        num_workers: Number of parallel workers
        exploration_constant: UCT exploration parameter
        max_time: Maximum time limit in seconds (optional)
        verbose: Whether to print detailed output
        use_optimized: Use optimized orienteering (pre-computed paths)
        use_no_end: Use no-end orienteering variant
        
    Returns:
        Tuple of (best_state, execution_time)
    """
    
    # Set the variant BEFORE importing modules
    if use_no_end:
        os.environ['TREE_USE_NO_END'] = 'true'
        os.environ['TREE_USE_OPTIMIZED'] = 'false'
    else:
        os.environ['TREE_USE_NO_END'] = 'false'
        os.environ['TREE_USE_OPTIMIZED'] = 'true' if use_optimized else 'false'
    
    # Import modules (they will use the adapter which reads the env var)
    from Tree.tree_parallel_coordinator import TreeParallelMCTS
    from Tree.orienteering_adapter import OrienteeringProblem, START_NODE, get_variant
    
    variant_name = get_variant()
    
    # Load the problem
    print(f"Loading problem from: {problem_file}")
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
    
    if verbose:
        print(f"Problem: {problem.num_nodes} nodes, budget: {problem.budget}")
        print(f"Variant: {variant_name} Orienteering")
        print(f"Initial state reward: {problem.nodes[START_NODE].score}")
    
    # Create and run Tree-Parallel MCTS
    coordinator = TreeParallelMCTS(
        problem=problem,
        num_workers=num_workers,
        exploration_constant=exploration_constant
    )
    
    start_time = time.time()
    
    best_state = coordinator.run(
        max_iterations=max_iterations,
        max_time=max_time,
        verbose=verbose
    )
    
    execution_time = time.time() - start_time
    
    if verbose:
        print(f"\nBest solution found:")
        print(f"  Path: {' -> '.join(map(str, best_state.path))}")
        print(f"  Reward: {best_state.reward_so_far}")
        print(f"  Cost: {best_state.cost_so_far:.2f}")
        print(f"  Valid: {best_state.is_terminal()}")
        print(f"  Execution time: {execution_time:.2f}s")
        
        # Get tree statistics
        tree_stats = coordinator.get_tree_statistics()
        print(f"\nTree Statistics:")
        print(f"  Total nodes: {tree_stats['total_nodes']}")
        print(f"  Maximum depth: {tree_stats['max_depth']}")
        
    return best_state, execution_time


def main():
    """
    Main function with command-line argument parsing using argparse.
    """
    parser = argparse.ArgumentParser(description='Tree-Parallel MCTS for the Orienteering Problem')
    
    parser.add_argument('--problem-file', '-p', type=str, required=True,
                       help='Path to the orienteering problem file')
    parser.add_argument('--max-iterations', type=int, default=10000,
                       help='Maximum number of iterations (default: 10000)')
    parser.add_argument('--max-time', type=float, default=None,
                       help='Maximum time in seconds (optional, overrides max-iterations if specified)')
    parser.add_argument('--exploration-constant', type=float, default=math.sqrt(2),
                       help='UCT exploration constant (default: sqrt(2))')
    parser.add_argument('--num-workers', '-n', type=int, default=4,
                       help='Number of parallel workers (default: 4)')
    parser.add_argument('--use-traditional', action='store_true',
                       help='Use traditional (non-optimized) orienteering implementation')
    parser.add_argument('--use-no-end', '-no-end', action='store_true',
                       help='Use no-end orienteering variant (maximize reward without end node requirement)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--output-file', type=str,
                       help='Output file to save results')
    
    args = parser.parse_args()
    
    # Set the variant BEFORE importing Tree modules
    if args.use_no_end:
        os.environ['TREE_USE_NO_END'] = 'true'
        os.environ['TREE_USE_OPTIMIZED'] = 'false'
    else:
        os.environ['TREE_USE_NO_END'] = 'false'
        os.environ['TREE_USE_OPTIMIZED'] = 'false' if args.use_traditional else 'true'
    
    # Now import Tree modules (they will use the adapter which reads the env var)
    from Tree.tree_parallel_coordinator import TreeParallelMCTS
    from Tree.orienteering_adapter import OrienteeringProblem, get_variant
    
    variant_name = get_variant()
    
    # Load problem
    try:
        nodes, budget = OrienteeringProblem.load_problem(args.problem_file)
        problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
        
        if args.verbose:
            print(f"Loaded problem: {len(nodes)} nodes, budget: {budget}")
            print(f"Problem file: {args.problem_file}")
            print(f"Variant: {variant_name} Orienteering")
            if args.max_time:
                print(f"Max time: {args.max_time} seconds")
    except Exception as e:
        print(f"ERROR: Failed to load problem file: {e}")
        sys.exit(1)
    
    # Run Tree-Parallel MCTS
    start_time = time.time()
    
    if args.verbose:
        if args.max_time:
            print(f"Running Tree-Parallel MCTS with max time {args.max_time}s")
        else:
            print(f"Running Tree-Parallel MCTS with {args.max_iterations} iterations")
        print(f"Number of workers: {args.num_workers}")
        print(f"Exploration constant: {args.exploration_constant}")
    
    coordinator = TreeParallelMCTS(
        problem=problem,
        num_workers=args.num_workers,
        exploration_constant=args.exploration_constant
    )
    
    best_state = coordinator.run(
        max_iterations=args.max_iterations,
        max_time=args.max_time,
        verbose=args.verbose
    )
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    if args.verbose:
        tree_stats = coordinator.get_tree_statistics()
        print(f"\nTree Statistics:")
        print(f"  Total nodes: {tree_stats['total_nodes']}")
        print(f"  Maximum depth: {tree_stats['max_depth']}")
    
    # Print results
    # Calculate raw reward by summing actual node scores
    raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.path)
    
    print(f"\nResults:")
    print(f"Algorithm: Tree-Parallel MCTS (Standard UCT)")
    print(f"Best path: {' -> '.join(map(str, best_state.path))}")
    if problem.normalize_rewards:
        print(f"Normalized reward: {best_state.reward_so_far}")
        print(f"Raw reward: {raw_reward}")
    else:
        print(f"Total reward: {best_state.reward_so_far}")
        print(f"  (Same as raw reward: {raw_reward})")
    print(f"Total cost: {best_state.cost_so_far:.2f}")
    print(f"Valid solution: {best_state.is_terminal()}")
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
        output_file = os.path.join(results_dir, f"tree-parallel-mcts_{problem_name}_{args.max_iterations}.txt")
    
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(f"# Tree-Parallel MCTS Results\n")
            f.write(f"# Algorithm: Standard UCT (No WU-UCT modifications)\n")
            f.write(f"# Problem: {args.problem_file}\n")
            f.write(f"# Iterations: {args.max_iterations}\n")
            if args.max_time:
                f.write(f"# Max time: {args.max_time}s\n")
            f.write(f"# Exploration constant: {args.exploration_constant}\n")
            f.write(f"# Number of workers: {args.num_workers}\n")
            f.write(f"# Variant: {variant_name}\n")
            f.write(f"# Execution time: {elapsed_time:.2f}s\n")
            f.write(f"#\n")
            f.write(f"Path= {' '.join(map(str, best_state.path))}\n")
            f.write(f"Normalized_Reward= {best_state.reward_so_far}\n")
            f.write(f"Raw_Reward= {raw_reward}\n")
            f.write(f"Cost= {best_state.cost_so_far}\n")
            f.write(f"Valid= {best_state.is_terminal()}\n")
        
        print(f"Results saved to: {output_file}")
    except Exception as e:
        print(f"ERROR: Failed to save results to file: {e}")


def run_benchmark_comparison():
    """
    Run a comparison between different worker configurations.
    """
    print("Running Tree-Parallel MCTS Benchmark Comparison")
    print("=" * 60)
    
    # Test problem
    problem_file = "../OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    
    if not os.path.exists(problem_file):
        print(f"Benchmark problem file not found: {problem_file}")
        return
    
    configurations = [
        {"workers": 1, "iterations": 20000},
        {"workers": 2, "iterations": 20000},
        {"workers": 4, "iterations": 20000},
        {"workers": 8, "iterations": 20000},
    ]
    
    results = []
    
    for config in configurations:
        print(f"\nTesting {config['workers']} workers, {config['iterations']} iterations")
        print("-" * 40)
        
        best_state, execution_time = run_tree_parallel_mcts(
            problem_file=problem_file,
            max_iterations=config['iterations'],
            num_workers=config['workers'],
            exploration_constant=1.42,
            verbose=False,
            use_optimized=True,
            use_no_end=False
        )
        
        # Calculate actual reward
        from Tree.orienteering_adapter import OrienteeringProblem
        nodes, budget = OrienteeringProblem.load_problem(problem_file)
        problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
        actual_reward = sum(problem.nodes[node_id].score for node_id in best_state.path)
        
        results.append({
            **config,
            'normalized_reward': best_state.reward_so_far,
            'actual_reward': actual_reward,
            'cost': best_state.cost_so_far,
            'valid': best_state.is_terminal(),
            'time': execution_time,
            'iterations_per_second': config['iterations'] / execution_time
        })
        
        print(f"  Result: actual_reward={actual_reward}, time={execution_time:.2f}s, valid={best_state.is_terminal()}")
    
    # Print summary
    print(f"\nBenchmark Results Summary - Grid Sample 30")
    print("=" * 80)
    print(f"{'Workers':<10} {'Actual Reward':<15} {'Cost':<10} {'Valid':<8} {'Time(s)':<10} {'Iter/s':<10}")
    print("-" * 80)
    
    for result in results:
        print(f"{result['workers']:<10} {result['actual_reward']:<15} {result['cost']:<10.2f} "
              f"{result['valid']!s:<8} {result['time']:<10.2f} {result['iterations_per_second']:<10.1f}")


if __name__ == "__main__":
    # Check if benchmark mode is requested
    if len(sys.argv) > 1 and sys.argv[1] == "--benchmark":
        run_benchmark_comparison()
    else:
        main()
