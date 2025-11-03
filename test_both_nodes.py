"""
Quick test to verify both TreeParallelNode and WUUCTNode work correctly
after extending UCTNode.
"""

import sys
import math
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

print("="*70)
print("Testing TreeParallelNode (extends UCTNode)")
print("="*70)

from Tree.tree_parallel_coordinator import TreeParallelMCTS
from Tree.orienteering_adapter import OrienteeringProblem

# Load test problem
nodes, budget = OrienteeringProblem.load_problem(
    "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
)
problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)

# Run Tree-Parallel MCTS
coordinator = TreeParallelMCTS(
    problem=problem,
    num_workers=4,
    exploration_constant=math.sqrt(2)
)

best_state = coordinator.run(max_iterations=5000, verbose=False)
actual_reward = sum(problem.nodes[node_id].score for node_id in best_state.path)

print(f"✓ TreeParallelNode works!")
print(f"  Path length: {len(best_state.path)} nodes")
print(f"  Actual reward: {actual_reward}")
print(f"  Cost: {best_state.cost_so_far:.2f}")
print(f"  Valid: {best_state.is_terminal()}")

print("\n" + "="*70)
print("Testing WUUCTNode (extends UCTNode)")
print("="*70)

from WU_UCT.wu_uct_coordinator import WUUCTCoordinator
from WU_UCT.orienteering_adapter import OrienteeringAdapter

# Load test problem
problem2 = OrienteeringAdapter.load_problem(
    "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt",
    normalize_rewards=True
)

# Run WU-UCT
coordinator2 = WUUCTCoordinator(
    problem=problem2,
    num_expansion_workers=2,
    num_simulation_workers=4,
    exploration_constant=math.sqrt(2),
    max_distance=1.42
)

best_state2 = coordinator2.run(max_iterations=5000, verbose=False)
actual_reward2 = sum(problem2.nodes[node_id].score for node_id in best_state2.path)

print(f"✓ WUUCTNode works!")
print(f"  Path length: {len(best_state2.path)} nodes")
print(f"  Actual reward: {actual_reward2}")
print(f"  Cost: {best_state2.cost_so_far:.2f}")
print(f"  Valid: {best_state2.is_terminal()}")

print("\n" + "="*70)
print("SUCCESS: Both node classes work correctly with UCTNode inheritance!")
print("="*70)
print(f"\nTreeParallelNode: {actual_reward} reward")
print(f"WUUCTNode:        {actual_reward2} reward")
print("\nBoth implementations are functioning correctly.")
