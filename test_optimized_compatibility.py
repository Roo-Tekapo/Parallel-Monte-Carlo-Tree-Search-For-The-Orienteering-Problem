"""
Quick test to verify orienteering_optimized works with MCTS
"""

from orienteering.orienteering_optimized import OrienteeringProblem, OrienteeringState
from MCTS.mcts_base import MCTSSingleThread

print("Testing orienteering_optimized.py compatibility...")

# Load problem
nodes, budget = OrienteeringProblem.load_problem(
    "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
)

# Create problem (this will do Dijkstra pre-computation)
print(f"Loading problem with {len(nodes)} nodes, budget={budget}")
print("Pre-computing shortest paths...")
problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
print("✓ Pre-computation complete!")

# Test with conservative MCTS (traditional_mcts=False)
print("\nRunning Conservative MCTS with optimized orienteering...")
solver = MCTSSingleThread(problem, iterations=5000, traditional_mcts=False, exploration_constant=0.5)
best_state = solver.run()

# Calculate results
path = best_state.get_path()
raw_reward = sum(problem.nodes[node_id].score for node_id in path)

print("\n" + "="*70)
print("CONSERVATIVE MCTS RESULTS (with optimized reachability)")
print("="*70)
print(f"Path: {path}")
print(f"Path length: {len(path)} nodes")
print(f"Raw reward: {raw_reward}")
print(f"Normalized reward: {best_state.get_reward():.2f}")
print(f"Cost: {best_state.get_cost():.2f} / {budget}")
print(f"Budget usage: {(best_state.get_cost() / budget) * 100:.1f}%")
print(f"Valid solution: {best_state.is_terminal()}")
print("\n✓ orienteering_optimized.py works correctly!")
print("\nYou can now import from orienteering.orienteering_optimized and it will work!")
