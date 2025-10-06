"""
Quick diagnostic to understand WU-UCT performance on grid problems.
"""

import time
import math
from orienteering.orienteering import OrienteeringProblem
from UCT.uct_single_thread import UCTSingleThread
from UCT.wu_uct import run_wu_uct

# Test with smaller problem first
test_file = "OP_Benchmark_Set/parallel_friendly_v2/dense_grid/dense_15x15_r0_15.txt"

print(f"Diagnostic Test: {test_file}")
print("="*70)

# Load problem
nodes, budget = OrienteeringProblem.load_problem(test_file)
problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)

print(f"Problem: {len(nodes)} nodes, budget={budget}")
print(f"Max edge distance: {problem.max_edge_distance}")

# Check connectivity
print("\nChecking connectivity...")
neighbors_sample = problem.get_neighbors(50)  # Check a middle node
print(f"Node 50 has {len(neighbors_sample)} neighbors")

# Test single-threaded (fewer iterations for speed)
print("\n1. Single-threaded UCT (1000 iterations)")
print("-"*70)
uct_st = UCTSingleThread(problem, iterations=1000, exploration_constant=math.sqrt(2))
start = time.time()
solution_st = uct_st.run()
time_st = time.time() - start

print(f"Result: {solution_st.get_reward():.0f} reward")
print(f"Path: {solution_st.get_path()}")
print(f"Path length: {len(solution_st.get_path())} nodes")
print(f"Cost: {solution_st.get_cost():.2f} / {budget}")
print(f"Time: {time_st:.2f}s")
stats_st = uct_st.get_statistics()
print(f"Tree stats: {stats_st}")

# Test WU-UCT
print("\n2. WU-UCT with 4 workers (1000 iterations)")
print("-"*70)
start = time.time()
solution_wu = run_wu_uct(problem, max_iterations=1000, simulation_workers=4, 
                        exploration_constant=math.sqrt(2), verbose=True)
time_wu = time.time() - start

print(f"\nResult: {solution_wu.get_reward():.0f} reward")
print(f"Path: {solution_wu.get_path()}")
print(f"Path length: {len(solution_wu.get_path())} nodes")
print(f"Cost: {solution_wu.get_cost():.2f} / {budget}")
print(f"Time: {time_wu:.2f}s")

# Compare
print("\n" + "="*70)
print("COMPARISON")
print("="*70)
print(f"Single-thread: {solution_st.get_reward():.0f} reward in {time_st:.2f}s")
print(f"WU-UCT:        {solution_wu.get_reward():.0f} reward in {time_wu:.2f}s")
if time_wu > 0:
    speedup = time_st / time_wu
    print(f"Speedup:       {speedup:.2f}x")
    
    if speedup < 0.5:
        print("\n⚠️ WARNING: WU-UCT is significantly SLOWER")
        print("Possible issues:")
        print("  - Thread overhead dominating")
        print("  - Iteration count may be split incorrectly")
        print("  - Simulation workers not getting enough work")
    elif solution_wu.get_reward() < solution_st.get_reward() * 0.7:
        print(f"\n⚠️ WARNING: WU-UCT finding much worse solutions")
        print("Possible issues:")
        print("  - Not enough iterations per worker")
        print("  - Tree not being shared properly")
        print("  - Simulations not being backpropagated correctly")
