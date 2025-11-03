"""
Quick test to verify WU-UCT can now reach the END node on XL problems.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from WU_UCT.wu_uct_coordinator import WUUCTCoordinator
from WU_UCT.orienteering_adapter import OrienteeringAdapter


def test_xl_problem():
    """Test on a large problem to ensure END node is reachable."""
    
    # Try a sample problem first
    print("Testing WU-UCT with fixed simulation logic...")
    print("=" * 70)
    
    # Load a medium-sized problem
    problem_path = "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    
    if not os.path.exists(problem_path):
        print(f"Problem file not found: {problem_path}")
        print("Using sample instead...")
        problem_path = "OP_Benchmark_Set/sample/sample_30.txt"
    
    print(f"Loading: {problem_path}")
    problem = OrienteeringAdapter.load_problem(
        problem_path,
        normalize_rewards=True,
        max_edge_distance=1.42
    )
    
    print(f"Nodes: {problem.num_nodes}, Budget: {problem.budget}")
    
    # Run with more iterations to allow convergence
    coordinator = WUUCTCoordinator(
        problem=problem,
        num_expansion_workers=2,
        num_simulation_workers=4,
        exploration_constant=1.414,
        max_distance=problem.budget
    )
    
    print("\nRunning WU-UCT...")
    best_solution = coordinator.run(
        max_iterations=10000,  # More iterations for better convergence
        verbose=True
    )
    
    print("\n" + "=" * 70)
    print("RESULTS:")
    print("=" * 70)
    print(f"Path length: {len(best_solution.path)}")
    print(f"Path: {best_solution.path}")
    print(f"Reward: {best_solution.reward_so_far:.4f}")
    print(f"Cost: {best_solution.cost_so_far:.4f} / {problem.budget}")
    print(f"Terminal (reached END): {best_solution.is_terminal()}")
    
    if best_solution.is_terminal():
        print("\n✓ SUCCESS: Solution reaches the END node!")
        return True
    else:
        print("\n✗ FAILURE: Solution does not reach END node")
        print(f"   Last node: {best_solution.path[-1]}")
        return False


if __name__ == "__main__":
    success = test_xl_problem()
    sys.exit(0 if success else 1)
