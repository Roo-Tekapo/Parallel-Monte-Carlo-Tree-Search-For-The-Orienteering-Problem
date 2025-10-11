#!/usr/bin/env python3
"""
Debug _can_reach_end_from() in detail
"""

import sys
import os

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.extend([project_root, current_dir])

from orienteering.orienteering import OrienteeringProblem, OrienteeringState, END_NODE


def debug_can_reach_end():
    """Debug the _can_reach_end_from() method in detail."""
    
    print("🔍 Debug: _can_reach_end_from() Method")
    print("=" * 70)
    
    # Load the long grid problem
    problem_path = "../OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt"
    nodes, budget = OrienteeringProblem.load_problem(problem_path)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)
    
    print(f"Problem: {len(nodes)} nodes, budget={budget}")
    print(f"END_NODE = {END_NODE}")
    print()
    
    # Test from start
    initial_state = OrienteeringState(problem)
    print(f"Testing from START_NODE (0):")
    print(f"  Current path: {initial_state.path}")
    print(f"  Current cost: {initial_state.cost_so_far}")
    print(f"  Visited: {initial_state.visited}")
    print()
    
    # Test first hop
    first_neighbors = problem.get_neighbors(0)
    print(f"First hop options from START:")
    for neighbor in first_neighbors[:5]:  # Just first 5
        cost_to_neighbor = problem.get_distance(0, neighbor)
        new_cost = initial_state.cost_so_far + cost_to_neighbor
        can_reach = initial_state._can_reach_end_from(neighbor, new_cost)
        print(f"  Node {neighbor}: new_cost={new_cost:.2f}, can_reach_end={can_reach}")
    print()
    
    # Try simulating taking the first step
    print("Taking first step to node 47 (on shortest path to END):")
    next_state = initial_state.apply_action(47)
    print(f"  New path: {next_state.path}")
    print(f"  New cost: {next_state.cost_so_far:.2f}")
    print(f"  Visited: {next_state.visited}")
    print()
    
    # Check available actions from there
    actions_from_47 = next_state.get_available_actions()
    print(f"  Available actions from node 47: {len(actions_from_47)} actions")
    print(f"  Actions: {actions_from_47[:10]}...")
    print()
    
    # Check if node 37 (next on shortest path) is available
    if 37 in actions_from_47:
        print("  ✓ Node 37 (next on shortest path) IS available")
    else:
        print("  ❌ Node 37 (next on shortest path) is NOT available")
        # Check why
        cost_to_37 = problem.get_distance(47, 37)
        new_cost_37 = next_state.cost_so_far + cost_to_37
        can_reach_37 = next_state._can_reach_end_from(37, new_cost_37)
        print(f"     Cost to 37: {cost_to_37:.2f}")
        print(f"     New cost: {new_cost_37:.2f}")
        print(f"     Can reach end from 37? {can_reach_37}")


if __name__ == "__main__":
    try:
        debug_can_reach_end()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
