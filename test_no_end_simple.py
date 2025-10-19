"""
Simple test to verify the no-end orienteering variant works with MCTS Base.
"""

from orienteering.orienteering_no_end import (
    OrienteeringProblemNoEnd, 
    OrienteeringStateNoEnd
)
from MCTS.mcts_base import MCTSSingleThread
from MCTS.mcts_node import MCTSNode

# Load problem
print("Loading problem...")
nodes, budget = OrienteeringProblemNoEnd.load_problem(
    "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
)

problem = OrienteeringProblemNoEnd(
    nodes, 
    budget, 
    max_edge_distance=1.42, 
    normalize_rewards=True
)

print(f"Problem: {problem.num_nodes} nodes, budget={budget}")

# Create initial state
initial_state = OrienteeringStateNoEnd(problem)
print(f"Initial state: {initial_state}")
print(f"Available actions: {len(initial_state.get_available_actions())}")

# Run MCTS
print("\nRunning MCTS with 10 iterations...")  # Reduced for debugging
mcts = MCTSSingleThread(
    problem, 
    iterations=10,  # Reduced for debugging
    soft_end_bias=False
)
mcts.root = MCTSNode(initial_state)

print("Starting MCTS.run()...")
try:
    # Add timeout mechanism
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("MCTS took too long")
    
    # Set a timeout (only works on Unix, will skip on Windows)
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)  # 5 second timeout
    except AttributeError:
        print("(Timeout not available on Windows, running without timeout)")
        pass
    
    mcts.run()
    
    try:
        signal.alarm(0)  # Cancel the alarm
    except AttributeError:
        pass
        
    print("✓ MCTS search completed")
    
    # Get best solution
    best_node = mcts.best_child(mcts.root)
    if best_node:
        solution = best_node.state
        print(f"\n✓ Solution found:")
        print(f"  Path length: {len(solution.path)} nodes")
        print(f"  Total reward: {solution.reward_so_far:.4f}")
        print(f"  Budget used: {solution.cost_so_far:.2f}/{problem.budget}")
        print(f"  Terminal: {solution.is_terminal()}")
        print(f"  Path: {solution.path}")
    else:
        print("✗ No solution found")
except Exception as e:
    print(f"✗ Error during search: {e}")
    import traceback
    traceback.print_exc()
