"""
Test WU-UCT on grid_sample problems with various iteration counts.

This script runs the True WU-UCT implementation on the grid_sample dataset
with different iteration counts to evaluate performance and scalability.
"""

import sys
import time
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from WU_UCT.wu_uct_coordinator import WUUCTCoordinator
from WU_UCT.orienteering_adapter import OrienteeringAdapter


def run_single_test(problem_file: str, max_iterations: int, 
                   num_expansion_workers: int = 4,
                   num_simulation_workers: int = 8,
                   max_distance: float = 1.42):
    """
    Run a single test on a problem file.
    
    Args:
        problem_file: Path to problem file
        max_iterations: Number of iterations to run
        num_expansion_workers: Number of expansion workers
        num_simulation_workers: Number of simulation workers
        max_distance: Maximum travel distance
        
    Returns:
        Dictionary with results
    """
    # Load problem
    problem = OrienteeringAdapter.load_problem(problem_file, normalize_rewards=True)
    
    # Create coordinator
    coordinator = WUUCTCoordinator(
        problem=problem,
        num_expansion_workers=num_expansion_workers,
        num_simulation_workers=num_simulation_workers,
        exploration_constant=1.414,
        max_distance=max_distance
    )
    
    # Run algorithm
    start_time = time.time()
    best_state = coordinator.run(
        max_iterations=max_iterations,
        verbose=False
    )
    execution_time = time.time() - start_time
    
    # Collect statistics
    total_expansions = sum(w.expansions_performed for w in coordinator.expansion_workers)
    total_simulations = sum(w.simulations_completed for w in coordinator.simulation_workers)
    tree_stats = coordinator._get_tree_statistics()
    
    # Calculate actual reward
    actual_reward = sum(problem.nodes[node_id].score for node_id in best_state.path) if hasattr(best_state, 'path') else 0
    
    return {
        'problem_file': Path(problem_file).name,
        'max_iterations': max_iterations,
        'execution_time': execution_time,
        'iterations_per_sec': max_iterations / execution_time if execution_time > 0 else 0,
        'path_length': len(best_state.path) if hasattr(best_state, 'path') else 0,
        'normalized_reward': best_state.reward_so_far if hasattr(best_state, 'reward_so_far') else 0,
        'actual_reward': actual_reward,
        'cost': best_state.cost_so_far if hasattr(best_state, 'cost_so_far') else 0,
        'total_expansions': total_expansions,
        'total_simulations': total_simulations,
        'tree_nodes': tree_stats['total_nodes'],
        'tree_depth': tree_stats['max_depth'],
        'expansion_workers': num_expansion_workers,
        'simulation_workers': num_simulation_workers,
    }


def run_grid_sample_tests():
    """
    Run tests on all grid_sample problems with various iteration counts.
    """
    print("="*80)
    print("WU-UCT Grid Sample Tests")
    print("="*80)
    print()
    
    # Find grid_sample problems
    grid_sample_dir = project_root / "OP_Benchmark_Set" / "grid_sample"
    
    if not grid_sample_dir.exists():
        print(f"ERROR: Grid sample directory not found: {grid_sample_dir}")
        return
    
    problem_files = sorted(grid_sample_dir.glob("*.txt"))
    
    if not problem_files:
        print(f"ERROR: No problem files found in {grid_sample_dir}")
        return
    
    print(f"Found {len(problem_files)} problem files:")
    for pf in problem_files:
        print(f"  - {pf.name}")
    print()
    
    # Iteration counts to test
    iteration_counts = [500, 1000, 2000, 5000, 10000]
    
    # Worker configuration
    expansion_workers = 4
    simulation_workers = 8
    max_distance = 1.42
    
    print(f"Configuration:")
    print(f"  Expansion workers: {expansion_workers}")
    print(f"  Simulation workers: {simulation_workers}")
    print(f"  Max distance: {max_distance}")
    print(f"  Iteration counts: {iteration_counts}")
    print()
    print("="*80)
    print()
    
    # Store all results
    all_results = []
    
    # Run tests
    for problem_file in problem_files:
        problem_name = problem_file.name
        print(f"\n{'='*80}")
        print(f"Testing: {problem_name}")
        print(f"{'='*80}")
        
        for iterations in iteration_counts:
            print(f"\n  Running with {iterations} iterations...", end=' ', flush=True)
            
            try:
                result = run_single_test(
                    str(problem_file),
                    iterations,
                    expansion_workers,
                    simulation_workers,
                    max_distance
                )
                
                all_results.append(result)
                
                print(f"✓")
                print(f"    Time: {result['execution_time']:.2f}s")
                print(f"    Reward: {result['actual_reward']} (normalized: {result['normalized_reward']:.4f})")
                print(f"    Path length: {result['path_length']}")
                print(f"    Cost: {result['cost']:.2f} / {max_distance}")
                print(f"    Tree nodes: {result['tree_nodes']}")
                print(f"    Throughput: {result['iterations_per_sec']:.1f} iter/s")
                
            except Exception as e:
                print(f"✗ FAILED")
                print(f"    Error: {e}")
                import traceback
                traceback.print_exc()
    
    # Print summary table
    print("\n" + "="*80)
    print("Summary Results")
    print("="*80)
    print()
    
    # Group by problem
    from collections import defaultdict
    by_problem = defaultdict(list)
    for result in all_results:
        by_problem[result['problem_file']].append(result)
    
    for problem_name in sorted(by_problem.keys()):
        print(f"\n{problem_name}:")
        print(f"  {'Iterations':<12} {'Time(s)':<10} {'Reward':<10} {'Path Len':<10} {'Tree Nodes':<12} {'Iter/s':<10}")
        print(f"  {'-'*70}")
        
        for result in by_problem[problem_name]:
            print(f"  {result['max_iterations']:<12} "
                  f"{result['execution_time']:<10.2f} "
                  f"{result['actual_reward']:<10} "
                  f"{result['path_length']:<10} "
                  f"{result['tree_nodes']:<12} "
                  f"{result['iterations_per_sec']:<10.1f}")
    
    # Save results to JSON
    results_file = project_root / "WU_UCT" / "grid_sample_test_results.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Results saved to: {results_file}")
    print(f"{'='*80}")
    
    # Performance analysis
    print("\n" + "="*80)
    print("Performance Analysis")
    print("="*80)
    
    # Average throughput by iteration count
    from collections import defaultdict
    throughput_by_iters = defaultdict(list)
    for result in all_results:
        throughput_by_iters[result['max_iterations']].append(result['iterations_per_sec'])
    
    print("\nAverage Throughput by Iteration Count:")
    print(f"  {'Iterations':<12} {'Avg Iter/s':<12} {'Samples':<10}")
    print(f"  {'-'*40}")
    for iters in sorted(throughput_by_iters.keys()):
        avg_throughput = sum(throughput_by_iters[iters]) / len(throughput_by_iters[iters])
        print(f"  {iters:<12} {avg_throughput:<12.1f} {len(throughput_by_iters[iters]):<10}")
    
    # Best rewards per problem
    print("\nBest Rewards per Problem:")
    print(f"  {'Problem':<35} {'Best Reward':<12} {'At Iterations':<15}")
    print(f"  {'-'*70}")
    for problem_name in sorted(by_problem.keys()):
        results = by_problem[problem_name]
        best = max(results, key=lambda r: r['actual_reward'])
        print(f"  {problem_name:<35} {best['actual_reward']:<12} {best['max_iterations']:<15}")


def run_worker_comparison():
    """
    Compare different worker configurations on a single problem.
    """
    print("\n" + "="*80)
    print("Worker Configuration Comparison")
    print("="*80)
    print()
    
    # Use one problem file
    grid_sample_dir = project_root / "OP_Benchmark_Set" / "grid_sample"
    problem_file = grid_sample_dir / "grid_10x10_medium_30.txt"
    
    if not problem_file.exists():
        print(f"Test problem not found: {problem_file}")
        return
    
    print(f"Testing on: {problem_file.name}")
    print()
    
    # Worker configurations to test
    configs = [
        (2, 4),   # 2 expansion, 4 simulation
        (4, 8),   # 4 expansion, 8 simulation
        (4, 12),  # 4 expansion, 12 simulation
        (8, 8),   # 8 expansion, 8 simulation
        (8, 16),  # 8 expansion, 16 simulation
    ]
    
    iterations = 5000
    results = []
    
    for exp_workers, sim_workers in configs:
        print(f"Testing {exp_workers} expansion + {sim_workers} simulation workers...", end=' ', flush=True)
        
        try:
            result = run_single_test(
                str(problem_file),
                iterations,
                exp_workers,
                sim_workers,
                max_distance=1.42
            )
            results.append(result)
            print(f"✓ ({result['execution_time']:.2f}s, reward={result['actual_reward']})")
        except Exception as e:
            print(f"✗ {e}")
    
    # Print comparison table
    print("\nComparison:")
    print(f"  {'Exp':<5} {'Sim':<5} {'Total':<7} {'Time(s)':<10} {'Reward':<10} {'Iter/s':<10} {'Efficiency':<12}")
    print(f"  {'-'*70}")
    
    for result in results:
        total_workers = result['expansion_workers'] + result['simulation_workers']
        efficiency = result['iterations_per_sec'] / total_workers
        print(f"  {result['expansion_workers']:<5} "
              f"{result['simulation_workers']:<5} "
              f"{total_workers:<7} "
              f"{result['execution_time']:<10.2f} "
              f"{result['actual_reward']:<10} "
              f"{result['iterations_per_sec']:<10.1f} "
              f"{efficiency:<12.1f}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--workers":
        run_worker_comparison()
    else:
        run_grid_sample_tests()
        
        # Optionally run worker comparison too
        if "--with-workers" in sys.argv:
            run_worker_comparison()
