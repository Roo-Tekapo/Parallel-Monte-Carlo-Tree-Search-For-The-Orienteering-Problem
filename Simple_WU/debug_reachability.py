#!/usr/bin/env python3
"""
Debug script to check reachability logic
"""

import sys
import os

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.extend([project_root, current_dir])

from orienteering.orienteering import OrienteeringProblem, OrienteeringState, END_NODE


def debug_reachability():
    """Test the reachability logic."""
    
    print("🔍 Debug: Reachability Check")
    print("=" * 70)
    
    # Load the long grid problem
    problem_path = "../OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt"
    nodes, budget = OrienteeringProblem.load_problem(problem_path)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)
    
    print(f"Problem: {len(nodes)} nodes, budget={budget}")
    print(f"END_NODE = {END_NODE}")
    print(f"Max edge distance: {problem.max_edge_distance}")
    print()
    
    # Check precomputed structures
    print(f"Precomputed _end_reachable_nodes: {problem._end_reachable_nodes}")
    print(f"Precomputed _can_reach_end_structure: {problem._can_reach_end_structure is not None}")
    print()
    
    # Test from start node
    initial_state = OrienteeringState(problem)
    print(f"Starting from node 0:")
    print(f"  Current cost: {initial_state.cost_so_far}")
    print(f"  Neighbors of node 0: {problem.get_neighbors(0)}")
    print()
    
    # Check available actions from start
    actions = initial_state.get_available_actions(traditional_mcts=False)
    print(f"Available actions from start (conservative): {actions}")
    print(f"  Number of actions: {len(actions)}")
    print(f"  END_NODE ({END_NODE}) in actions? {END_NODE in actions}")
    print()
    
    # Check if END_NODE is a neighbor of start
    if END_NODE in problem.get_neighbors(0):
        cost_to_end = problem.get_distance(0, END_NODE)
        print(f"END_NODE is a direct neighbor of start!")
        print(f"  Distance from 0 to {END_NODE}: {cost_to_end}")
        print(f"  Can afford? {cost_to_end <= budget}")
    else:
        print(f"END_NODE is NOT a direct neighbor of start")
        print(f"  Distance from 0 to {END_NODE}: {problem.get_distance(0, END_NODE)}")
    print()
    
    # Test reachability check for each neighbor
    print("Testing _can_reach_end_from() for each neighbor:")
    for neighbor in problem.get_neighbors(0):
        if neighbor == 0:  # Skip start
            continue
        cost_to_neighbor = problem.get_distance(0, neighbor)
        new_cost = cost_to_neighbor
        can_reach = initial_state._can_reach_end_from(neighbor, new_cost)
        print(f"  Node {neighbor}: cost={new_cost:.2f}, can_reach_end={can_reach}")
    print()
    
    # Try traditional MCTS to see difference
    actions_traditional = initial_state.get_available_actions(traditional_mcts=True)
    print(f"Available actions from start (traditional): {actions_traditional}")
    print(f"  Number of actions: {len(actions_traditional)}")
    print(f"  END_NODE ({END_NODE}) in actions? {END_NODE in actions_traditional}")


if __name__ == "__main__":
    try:
        debug_reachability()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
