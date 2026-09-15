"""
Test script to demonstrate reward normalization in Simple WU-UCT.

This script compares the behavior with and without reward normalization
on a small orienteering problem to show the impact of normalization.
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Simple_WU.orienteering_adapter import OrienteeringProblem
from Simple_WU.simple_wu_coordinator import SimpleWUUCT


def run_comparison_test():
    """Run a comparison test with and without normalization."""
    
    # Load a test problem
    candidate_files = [
        "OP_Benchmark_Set/sample/sample_30.txt",
        "OP_Benchmark_Set/grid_sample/grid_sample_30.txt",
        "OP_Benchmark_Set/sample/p1.2.a.txt"
    ]
    problem_file = next((f for f in candidate_files if os.path.exists(f)), None)
    if not problem_file:
        print("Error: No test problem file found")
        return
    
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=None)
    
    print("=" * 80)
    print("Testing Simple WU-UCT with Reward Normalization")
    print("=" * 80)
    print(f"\nProblem: {problem_file}")
    print(f"Number of nodes: {len(problem.nodes)}")
    print(f"Maximum distance (budget): {problem.budget}")
    
    # Calculate total possible reward
    total_reward = sum(node.score for node in problem.nodes)
    print(f"Total node scores: {total_reward}")
    print(f"Min node score: {min(node.score for node in problem.nodes)}")
    print(f"Max node score: {max(node.score for node in problem.nodes)}")
    
    # Test parameters
    num_workers = 4
    max_iterations = 1000
    
    print("\n" + "=" * 80)
    print("Test 1: WITHOUT Reward Normalization")
    print("=" * 80)
    
    solver_no_norm = SimpleWUUCT(
        problem=problem,
        num_workers=num_workers,
        use_reward_normalization=False
    )
    
    solution_no_norm = solver_no_norm.run(max_iterations=max_iterations, verbose=True)
    stats_no_norm = solver_no_norm.get_tree_statistics()
    
    print(f"\nSolution without normalization:")
    print(f"  Path: {solution_no_norm.path}")
    print(f"  Reward: {solution_no_norm.reward_so_far}")
    print(f"  Cost: {solution_no_norm.cost_so_far:.2f} / {problem.budget:.2f}")
    print(f"  Tree nodes created: {stats_no_norm['nodes']}")
    print(f"  Max tree depth: {stats_no_norm['max_depth']}")
    
    print("\n" + "=" * 80)
    print("Test 2: WITH Reward Normalization (Discovered Bounds)")
    print("=" * 80)
    
    solver_norm_discovered = SimpleWUUCT(
        problem=problem,
        num_workers=num_workers,
        use_reward_normalization=True,
        use_estimated_bounds=False  # Discover bounds during search
    )
    
    solution_norm_discovered = solver_norm_discovered.run(max_iterations=max_iterations, verbose=True)
    stats_norm_discovered = solver_norm_discovered.get_tree_statistics()
    
    print(f"\nSolution with normalization (discovered bounds):")
    print(f"  Path: {solution_norm_discovered.path}")
    print(f"  Reward: {solution_norm_discovered.reward_so_far}")
    print(f"  Cost: {solution_norm_discovered.cost_so_far:.2f} / {problem.budget:.2f}")
    print(f"  Tree nodes created: {stats_norm_discovered['nodes']}")
    print(f"  Max tree depth: {stats_norm_discovered['max_depth']}")
    
    if 'reward_normalization' in stats_norm_discovered:
        norm_stats = stats_norm_discovered['reward_normalization']
        print(f"\nNormalization statistics:")
        print(f"  Min reward observed: {norm_stats['min_reward']:.2f}")
        print(f"  Max reward observed: {norm_stats['max_reward']:.2f}")
        print(f"  Reward range: {norm_stats['reward_range']:.2f}")
        print(f"  Updates: {norm_stats['num_updates']}")
    
    print("\n" + "=" * 80)
    print("Test 3: WITH Reward Normalization (Estimated Bounds)")
    print("=" * 80)
    
    solver_norm_estimated = SimpleWUUCT(
        problem=problem,
        num_workers=num_workers,
        use_reward_normalization=True,
        use_estimated_bounds=True  # Use problem-based bounds
    )
    
    solution_norm_estimated = solver_norm_estimated.run(max_iterations=max_iterations, verbose=True)
    stats_norm_estimated = solver_norm_estimated.get_tree_statistics()
    
    print(f"\nSolution with normalization (estimated bounds):")
    print(f"  Path: {solution_norm_estimated.path}")
    print(f"  Reward: {solution_norm_estimated.reward_so_far}")
    print(f"  Cost: {solution_norm_estimated.cost_so_far:.2f} / {problem.budget:.2f}")
    print(f"  Tree nodes created: {stats_norm_estimated['nodes']}")
    print(f"  Max tree depth: {stats_norm_estimated['max_depth']}")
    
    if 'reward_normalization' in stats_norm_estimated:
        norm_stats = stats_norm_estimated['reward_normalization']
        print(f"\nNormalization statistics:")
        print(f"  Min reward (estimated): {norm_stats['min_reward']:.2f}")
        print(f"  Max reward (estimated): {norm_stats['max_reward']:.2f}")
        print(f"  Reward range: {norm_stats['reward_range']:.2f}")
        print(f"  Updates: {norm_stats['num_updates']}")
    
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    
    print(f"\n{'Configuration':<40} {'Reward':<10} {'Nodes':<10} {'Depth':<10}")
    print("-" * 80)
    print(f"{'No normalization':<40} {solution_no_norm.reward_so_far:<10.0f} "
          f"{stats_no_norm['nodes']:<10} {stats_no_norm['max_depth']:<10}")
    print(f"{'Normalization (discovered)':<40} {solution_norm_discovered.reward_so_far:<10.0f} "
          f"{stats_norm_discovered['nodes']:<10} {stats_norm_discovered['max_depth']:<10}")
    print(f"{'Normalization (estimated)':<40} {solution_norm_estimated.reward_so_far:<10.0f} "
          f"{stats_norm_estimated['nodes']:<10} {stats_norm_estimated['max_depth']:<10}")
    
    print("\n" + "=" * 80)
    print("Analysis:")
    print("=" * 80)
    print("""
Reward normalization ensures that the exploitation term in the UCT formula
is scaled to [0, 1], providing consistent exploration-exploitation balance
regardless of the problem's reward scale.

Benefits:
1. Exploration constant (√2) works as intended across different problems
2. More stable behavior across problems with different reward ranges
3. Better theoretical grounding (UCT was designed for [0, 1] rewards)

Estimated bounds use the problem structure (sum of all scores) as an upper
bound, while discovered bounds adapt during search. Estimated bounds can
provide better normalization early in search when few rewards have been observed.
    """)


if __name__ == "__main__":
    run_comparison_test()
