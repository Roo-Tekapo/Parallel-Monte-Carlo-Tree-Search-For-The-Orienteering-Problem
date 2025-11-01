"""
Test script for Tree-Parallel MCTS

Demonstrates the basic tree-parallel MCTS implementation with standard UCT.
Uses orienteering adapter for flexible variant selection (defaults to optimized).
"""

import math
from Tree.orienteering_adapter import OrienteeringProblem, get_variant
from Tree.tree_parallel_coordinator import TreeParallelMCTS


def test_tree_parallel_mcts():
    """Test tree-parallel MCTS on a sample problem."""
    
    # Load a test problem
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    )
    
    problem = OrienteeringProblem(
        nodes, 
        budget, 
        max_edge_distance=1.42, 
        normalize_rewards=True
    )
    
    print("=" * 70)
    print("Tree-Parallel MCTS Test")
    print("=" * 70)
    print(f"Problem: {len(nodes)} nodes, budget={budget}")
    print(f"Normalize rewards: {problem.normalize_rewards}")
    
    # Test with different worker counts
    worker_counts = [1, 2, 4, 8]
    iterations = 10000
    
    for num_workers in worker_counts:
        print(f"\n{'=' * 70}")
        print(f"Testing with {num_workers} worker(s)")
        print(f"{'=' * 70}")
        
        # Create coordinator
        coordinator = TreeParallelMCTS(
            problem=problem,
            num_workers=num_workers,
            exploration_constant=math.sqrt(2)
        )
        
        # Run the algorithm
        best_solution = coordinator.run(
            max_iterations=iterations,
            verbose=True
        )
        
        # Get tree statistics
        tree_stats = coordinator.get_tree_statistics()
        print(f"\nTree Statistics:")
        print(f"  Max depth: {tree_stats['max_depth']}")
        print(f"  Total nodes: {tree_stats['total_nodes']}")
        print(f"  Average branching: {tree_stats['total_nodes'] / (tree_stats['max_depth'] + 1):.2f}")


def test_grid_sample_30():
    """Test on grid sample 30 problem (specific request)."""
    
    # Load the grid sample 30 problem
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    
    problem = OrienteeringProblem(
        nodes, 
        budget, 
        max_edge_distance=1.42, 
        normalize_rewards=True
    )
    
    print("=" * 70)
    print("Grid Sample 30 Test - Tree-Parallel MCTS with Optimized Orienteering")
    print("=" * 70)
    print(f"Problem: {len(nodes)} nodes, budget={budget}")
    print(f"Orienteering variant: {get_variant()}")
    print(f"Using optimized reachability checks (pre-computed shortest paths)")
    print()
    
    # Test with different worker counts
    worker_counts = [1, 2, 4, 8]
    iterations = 20000
    
    results = []
    
    for num_workers in worker_counts:
        print(f"\n{'=' * 70}")
        print(f"Testing with {num_workers} worker(s)")
        print(f"{'=' * 70}")
        
        # Create coordinator
        coordinator = TreeParallelMCTS(
            problem=problem,
            num_workers=num_workers,
            exploration_constant=1.42  # Good default for orienteering
        )
        
        # Run the algorithm
        best_solution = coordinator.run(
            max_iterations=iterations,
            verbose=True
        )
        
        # Calculate actual reward
        actual_reward = sum(problem.nodes[node_id].score for node_id in best_solution.path)
        
        results.append({
            'workers': num_workers,
            'path': best_solution.path,
            'path_length': len(best_solution.path),
            'actual_reward': actual_reward,
            'normalized_reward': best_solution.reward_so_far,
            'cost': best_solution.cost_so_far,
            'valid': best_solution.is_terminal()
        })
    
    # Print comparison summary
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY - Grid Sample 30")
    print("=" * 70)
    print(f"{'Workers':<10} {'Path Len':<12} {'Actual Reward':<15} {'Cost':<12} {'Valid':<8}")
    print("-" * 70)
    for r in results:
        print(f"{r['workers']:<10} {r['path_length']:<12} {r['actual_reward']:<15} {r['cost']:<12.2f} {r['valid']!s:<8}")
    print("=" * 70)


def compare_with_single_thread():
    """Compare tree-parallel MCTS with single-threaded version."""
    from MCTS.mcts_base import MCTSSingleThread
    
    # Load problem
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    )
    
    problem = OrienteeringProblem(
        nodes, 
        budget, 
        max_edge_distance=1.42, 
        normalize_rewards=True
    )
    
    iterations = 10000
    
    print("\n" + "=" * 70)
    print("Comparison: Single-Thread vs Tree-Parallel MCTS")
    print("=" * 70)
    
    # Single-threaded MCTS
    print("\nSingle-Threaded MCTS:")
    print("-" * 70)
    single_solver = MCTSSingleThread(
        problem=problem,
        iterations=iterations,
        exploration_constant=math.sqrt(2),
        soft_end_bias=True,
        bias_decay_factor=10
    )
    single_solution = single_solver.run()
    single_reward = sum(problem.nodes[node_id].score for node_id in single_solution.path)
    
    print(f"Path: {single_solution.path}")
    print(f"Path length: {len(single_solution.path)}")
    print(f"Actual reward: {single_reward}")
    print(f"Cost: {single_solution.cost_so_far:.2f} / {budget:.2f}")
    print(f"Valid: {single_solution.is_terminal()}")
    
    # Tree-parallel MCTS with 4 workers
    print("\nTree-Parallel MCTS (4 workers):")
    print("-" * 70)
    parallel_solver = TreeParallelMCTS(
        problem=problem,
        num_workers=4,
        exploration_constant=math.sqrt(2)
    )
    parallel_solution = parallel_solver.run(
        max_iterations=iterations,
        verbose=True
    )


def test_small_problem():
    """Test on a small problem for quick verification."""
    
    # Load a small problem
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    
    problem = OrienteeringProblem(
        nodes, 
        budget, 
        max_edge_distance=1.42, 
        normalize_rewards=True
    )
    
    print("=" * 70)
    print("Small Problem Test (Quick Verification)")
    print("=" * 70)
    print(f"Problem: {len(nodes)} nodes, budget={budget}")
    
    # Quick test with 4 workers
    coordinator = TreeParallelMCTS(
        problem=problem,
        num_workers=4,
        exploration_constant=1.42
    )
    
    best_solution = coordinator.run(
        max_iterations=5000,
        verbose=True
    )


if __name__ == "__main__":
    # Run grid sample 30 test (specific request)
    test_grid_sample_30()
    
    # Run small test first (uncomment if needed)
    # test_small_problem()
    
    # Run main test (uncomment if needed)
    # test_tree_parallel_mcts()
    
    # Run comparison (uncomment to compare with single-threaded)
    # compare_with_single_thread()
