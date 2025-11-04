"""
Main entry point for True WU-UCT implementation.

Demonstrates how to use the WU-UCT algorithm with proper separation
of expansion and simulation workers, following Chen et al. (2018).
"""

import argparse
import sys
import time
import math
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from WU_UCT.wu_uct_coordinator import WUUCTCoordinator
from WU_UCT.orienteering_adapter import OrienteeringAdapter


def run_wu_uct(problem_file: str,
               max_iterations: int = 10000,
               num_expansion_workers: int = 4,
               num_simulation_workers: int = 8,
               max_time: float = None,
               max_distance: float = 1.42,
               use_no_end: bool = False,
               verbose: bool = True):
    """
    Run true WU-UCT on an orienteering problem.
    
    Args:
        problem_file: Path to problem file
        max_iterations: Total number of iterations
        num_expansion_workers: Number of expansion workers
        num_simulation_workers: Number of simulation workers
        max_time: Optional time limit in seconds
        max_distance: Maximum travel distance constraint (default: 1.42)
        use_no_end: If True, path can end anywhere. If False, must end at END node.
        verbose: Whether to print detailed output
        
    Returns:
        Tuple of (best_state, execution_time)
    """
    # Load problem
    print(f"Loading problem from: {problem_file}")
    problem = OrienteeringAdapter.load_problem(problem_file, normalize_rewards=True,
                                               max_edge_distance=max_distance,
                                               use_no_end=use_no_end)
    
    if verbose:
        print(f"Problem: {problem.num_nodes} nodes, budget: {problem.budget}")
        print(f"Reward normalization: {problem.normalize_rewards}")
        print(f"Max distance constraint: {max_distance}")
        print(f"Orienteering variant: {'No-end' if use_no_end else 'Traditional'}")
    
    # Create coordinator
    coordinator = WUUCTCoordinator(
        problem=problem,
        num_expansion_workers=num_expansion_workers,
        num_simulation_workers=num_simulation_workers,
        exploration_constant=math.sqrt(2),
        max_distance=max_distance
    )
    
    # Run algorithm
    start_time = time.time()
    
    best_state = coordinator.run(
        max_iterations=max_iterations,
        max_time=max_time,
        verbose=verbose
    )
    
    execution_time = time.time() - start_time
    
    # Print solution
    if verbose:
        print(f"\n{'='*70}")
        print(f"Best Solution Found:")
        print(f"{'='*70}")
        if hasattr(best_state, 'path'):
            print(f"Path: {' -> '.join(map(str, best_state.path))}")
            print(f"Path length: {len(best_state.path)} nodes")
        if hasattr(best_state, 'reward_so_far'):
            print(f"Normalized reward: {best_state.reward_so_far:.6f}")
            # Calculate actual reward
            actual_reward = sum(problem.nodes[node_id].score for node_id in best_state.path)
            print(f"Actual reward: {actual_reward}")
        if hasattr(best_state, 'cost_so_far'):
            print(f"Cost: {best_state.cost_so_far:.2f} / {problem.budget:.2f}")
        print(f"Execution time: {execution_time:.2f}s")
    
    return best_state, execution_time


def main():
    """Main function with command-line argument parsing."""
    parser = argparse.ArgumentParser(
        description='True WU-UCT algorithm for the Orienteering Problem',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--problem-file', '-p', type=str, required=True,
                       help='Path to the orienteering problem file')
    parser.add_argument('--max-iterations', type=int, default=10000,
                       help='Maximum number of iterations')
    parser.add_argument('--max-time', type=float, default=None,
                       help='Maximum time in seconds (optional)')
    parser.add_argument('--expansion-workers', '-e', type=int, default=2,
                       help='Number of expansion workers')
    parser.add_argument('--simulation-workers', '-s', type=int, default=4,
                       help='Number of simulation workers')
    parser.add_argument('--max-distance', '-d', type=float, default=1.42,
                       help='Maximum travel distance constraint')
    parser.add_argument('--no-end-node', action='store_true',
                       help='Allow paths to end at any node (not required to return to END node)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--output-file', '-o', type=str, default=None,
                       help='Output file to save results')
    
    args = parser.parse_args()
    
    # Run WU-UCT
    try:
        best_state, execution_time = run_wu_uct(
            problem_file=args.problem_file,
            max_iterations=args.max_iterations,
            num_expansion_workers=args.expansion_workers,
            num_simulation_workers=args.simulation_workers,
            max_time=args.max_time,
            max_distance=args.max_distance,
            use_no_end=args.no_end_node,
            verbose=args.verbose
        )
        
        # Save results if requested
        if args.output_file:
            with open(args.output_file, 'w') as f:
                f.write(f"# True WU-UCT Results\n")
                f.write(f"# Problem: {args.problem_file}\n")
                f.write(f"# Iterations: {args.max_iterations}\n")
                f.write(f"# Expansion workers: {args.expansion_workers}\n")
                f.write(f"# Simulation workers: {args.simulation_workers}\n")
                f.write(f"# Max distance: {args.max_distance}\n")
                f.write(f"# No-end mode: {args.no_end_node}\n")
                f.write(f"# Execution time: {execution_time:.2f}s\n")
                f.write(f"#\n")
                if hasattr(best_state, 'path'):
                    f.write(f"Path= {' '.join(map(str, best_state.path))}\n")
                if hasattr(best_state, 'reward_so_far'):
                    f.write(f"Reward= {best_state.reward_so_far}\n")
                if hasattr(best_state, 'cost_so_far'):
                    f.write(f"Cost= {best_state.cost_so_far}\n")
            
            print(f"\nResults saved to: {args.output_file}")
    
    except FileNotFoundError:
        print(f"ERROR: Problem file not found: {args.problem_file}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_comparison():
    """Run a comparison of different worker configurations."""
    print("True WU-UCT Worker Configuration Comparison")
    print("="*70)
    
    problem_file = "../OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    
    # Check if file exists
    from pathlib import Path
    if not Path(problem_file).exists():
        print(f"Benchmark file not found: {problem_file}")
        return
    
    configurations = [
        # (expansion_workers, simulation_workers)
        (2, 4),
        (4, 8),
        (4, 12),
        (8, 16),
    ]
    
    max_iterations = 5000
    results = []
    
    for exp_workers, sim_workers in configurations:
        print(f"\nTesting: {exp_workers} expansion + {sim_workers} simulation workers")
        print("-"*70)
        
        best_state, exec_time = run_wu_uct(
            problem_file=problem_file,
            max_iterations=max_iterations,
            num_expansion_workers=exp_workers,
            num_simulation_workers=sim_workers,
            verbose=False
        )
        
        reward = best_state.reward_so_far if hasattr(best_state, 'reward_so_far') else 0
        
        results.append({
            'exp_workers': exp_workers,
            'sim_workers': sim_workers,
            'reward': reward,
            'time': exec_time,
            'iter_per_sec': max_iterations / exec_time
        })
        
        print(f"Result: reward={reward:.4f}, time={exec_time:.2f}s")
    
    # Print summary
    print(f"\n{'='*70}")
    print("Comparison Summary")
    print(f"{'='*70}")
    print(f"{'Exp Workers':<12} {'Sim Workers':<12} {'Reward':<10} {'Time(s)':<10} {'Iter/s':<10}")
    print("-"*70)
    
    for result in results:
        print(f"{result['exp_workers']:<12} "
              f"{result['sim_workers']:<12} "
              f"{result['reward']:<10.4f} "
              f"{result['time']:<10.2f} "
              f"{result['iter_per_sec']:<10.1f}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--compare":
        run_comparison()
    else:
        main()
