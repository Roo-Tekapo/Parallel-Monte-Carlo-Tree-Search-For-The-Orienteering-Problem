#!/usr/bin/env python3
"""
Debug script to visualize end node connectivity
"""

import sys
import os

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.extend([project_root, current_dir])

from orienteering.orienteering import OrienteeringProblem, END_NODE


def debug_end_connectivity():
    """Check how well END_NODE is connected to the graph."""
    
    print("🔍 Debug: END_NODE Connectivity")
    print("=" * 70)
    
    # Load the long grid problem
    problem_path = "../OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt"
    nodes, budget = OrienteeringProblem.load_problem(problem_path)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)
    
    print(f"Problem: {len(nodes)} nodes, budget={budget}")
    print(f"END_NODE = {END_NODE}")
    print(f"END_NODE position: {problem.nodes[END_NODE]}")
    print(f"Max edge distance: {problem.max_edge_distance}")
    print()
    
    # Check END_NODE's neighbors
    end_neighbors = problem.get_neighbors(END_NODE)
    print(f"END_NODE has {len(end_neighbors)} neighbors: {sorted(end_neighbors)[:20]}...")
    print()
    
    # Check who can reach END_NODE
    can_reach_end_directly = []
    for i in range(len(nodes)):
        if i != END_NODE and END_NODE in problem.get_neighbors(i):
            dist = problem.get_distance(i, END_NODE)
            can_reach_end_directly.append((i, dist))
    
    print(f"Nodes that can reach END_NODE directly: {len(can_reach_end_directly)}")
    for node_id, dist in sorted(can_reach_end_directly, key=lambda x: x[1])[:10]:
        print(f"  Node {node_id}: distance={dist:.3f}, position={problem.nodes[node_id]}")
    print()
    
    # Check structural reachability
    can_reach_structure = problem._can_reach_end_structure
    print(f"Nodes that can structurally reach END (any path): {len(can_reach_structure)}/{len(nodes)}")
    print(f"  This is {100*len(can_reach_structure)/len(nodes):.1f}% of all nodes")
    print()
    
    # Check if START_NODE can structurally reach END
    if 0 in can_reach_structure:
        print("✓ START_NODE (0) CAN structurally reach END_NODE")
    else:
        print("❌ START_NODE (0) CANNOT structurally reach END_NODE!")
        print("   This is a MAJOR PROBLEM - the graph is disconnected!")
    
    # Find shortest path from START to END
    from collections import deque
    
    def find_shortest_path(start, end):
        """BFS to find shortest path."""
        queue = deque([(start, [start])])
        visited = {start}
        
        while queue:
            current, path = queue.popleft()
            
            if current == end:
                return path
            
            for neighbor in problem.get_neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    print()
    shortest_path = find_shortest_path(0, END_NODE)
    if shortest_path:
        print(f"✓ Shortest path from START to END: {shortest_path}")
        print(f"  Path length (hops): {len(shortest_path) - 1}")
        
        # Calculate total distance
        total_dist = 0
        for i in range(len(shortest_path) - 1):
            total_dist += problem.get_distance(shortest_path[i], shortest_path[i+1])
        print(f"  Total distance: {total_dist:.2f}")
        print(f"  Within budget ({budget})? {total_dist <= budget}")
    else:
        print(f"❌ NO PATH from START to END in the graph!")
        print(f"   The graph is DISCONNECTED!")


if __name__ == "__main__":
    try:
        debug_end_connectivity()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
