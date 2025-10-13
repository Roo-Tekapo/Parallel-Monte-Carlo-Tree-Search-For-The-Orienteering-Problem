#!/usr/bin/env python3
"""
Debug script to check if simulations are reaching the terminal node
"""

import sys
import os
import math

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.extend([project_root, current_dir])

from orienteering.orienteering import OrienteeringProblem, OrienteeringState, END_NODE
from simple_wu_coordinator import SimpleWUUCT


def debug_terminal_reaching():
    """Test if the algorithm reaches terminal states."""
    
    print("🔍 Debug: Terminal Node Reaching Test")
    print("=" * 70)
    
    # Load the long grid problem
    problem_path = "../OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt"
    nodes, budget = OrienteeringProblem.load_problem(problem_path)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)
    
    print(f"Problem: {len(nodes)} nodes, budget={budget}")
    print(f"END_NODE = {END_NODE}")
    print(f"START_NODE = 0")
    print()
    
    # Run WU-UCT for a short time
    wu_uct = SimpleWUUCT(
        problem=problem,
        num_workers=4,
        exploration_constant=math.sqrt(2),
        max_distance=1.42
    )
    
    print(f"Running WU-UCT with 4 workers, 2000 iterations...")
    best_solution = wu_uct.run(max_iterations=2000, verbose=True)
    
    print("\n" + "=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    
    print(f"\n✓ Best solution found:")
    print(f"   Path: {best_solution.path}")
    print(f"   Reward: {best_solution.reward_so_far}")
    print(f"   Cost: {best_solution.cost_so_far:.2f} / {budget}")
    print(f"   Reaches END_NODE ({END_NODE})? {best_solution.path[-1] == END_NODE}")
    
    # Check tree for terminal paths
    def count_terminal_paths(node, depth=0):
        """Count how many paths in the tree reach END_NODE."""
        if depth > 20:  # Prevent deep recursion
            return 0
        
        count = 0
        
        # Check if this node's state reaches END
        if hasattr(node, 'state') and hasattr(node.state, 'path'):
            if node.state.path[-1] == END_NODE:
                count = 1
        
        # Check children
        if hasattr(node, 'children'):
            for child in node.children:
                count += count_terminal_paths(child, depth + 1)
        
        return count
    
    terminal_count = count_terminal_paths(wu_uct.root)
    print(f"\n📈 Tree Statistics:")
    print(f"   Nodes in tree that reach END_NODE: {terminal_count}")
    
    if terminal_count == 0:
        print(f"   ⚠️  NO paths in the tree reach END_NODE!")
        print(f"   This suggests the conservative check might be too restrictive,")
        print(f"   or there's an issue with how END_NODE is being added to actions.")
    else:
        print(f"   ✓ Found {terminal_count} paths reaching END_NODE in the tree")


if __name__ == "__main__":
    try:
        debug_terminal_reaching()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
