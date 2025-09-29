"""
Debug True WU-UCT Implementation
"""
import sys
import os
import time

# Add the parent directory to path to import orienteering module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from orienteering.orienteering import OrienteeringProblem, OrienteeringState, Node

# Import WU-UCT components
from wu_orienteering_tree import WUOrienteeringTree
from wu_specialized_workers import WUCoordinatedSolver


def debug_root_state():
    """Debug the root state and available actions"""
    print("Debugging root state...")
    
    # Create test problem
    nodes = [
        Node(0, 0, 0, 0),      # Start node
        Node(1, 10, 10, 0),    # End node  
        Node(2, 5, 5, 10),     # High reward node
        Node(3, 3, 7, 5),      # Medium reward node
        Node(4, 7, 3, 8)       # Good reward node
    ]
    budget = 50  # Increase budget to be more permissive
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=None)  # Remove edge constraint
    
    print(f"Problem nodes: {len(problem.nodes)}")
    print(f"Budget: {problem.budget}")
    print(f"Max edge distance: {problem.max_edge_distance}")
    
    # Create initial state
    root_state = OrienteeringState(problem)
    print(f"Root state path: {root_state.path}")
    print(f"Root state visited: {root_state.visited}")
    print(f"Root state cost so far: {root_state.cost_so_far}")
    print(f"Root state reward so far: {root_state.reward_so_far}")
    print(f"Root state is terminal: {root_state.is_terminal()}")
    
    available_actions = root_state.get_available_actions()
    print(f"Available actions from root: {available_actions}")
    
    # Debug neighbors
    current_node = root_state.path[-1]  # Should be 0
    neighbors = problem.get_neighbors(current_node)
    print(f"Neighbors of node {current_node}: {neighbors}")
    
    # Check distances
    for i in range(len(nodes)):
        if i != current_node:
            dist = problem.get_distance(current_node, i)
            print(f"Distance from {current_node} to {i}: {dist}")
    
    # Check budget constraints for potential moves
    for neighbor in neighbors:
        if neighbor != current_node:
            dist = problem.get_distance(current_node, neighbor)
            can_go = root_state.cost_so_far + dist <= problem.budget
            print(f"Can go to {neighbor}? Distance: {dist}, Budget needed: {root_state.cost_so_far + dist}, Available: {problem.budget}, OK: {can_go}")
    
    # Try taking actions
    for action in available_actions[:3]:  # Try first 3 actions
        try:
            next_state = root_state.apply_action(action)
            print(f"Action {action} -> path {next_state.path}, reward: {next_state.get_reward()}")
            print(f"  Terminal: {next_state.is_terminal()}")
            print(f"  Available from there: {next_state.get_available_actions()}")
        except Exception as e:
            print(f"Action {action} failed: {e}")


def debug_simple_expansion():
    """Debug simple expansion without parallel workers"""
    print("\nDebugging simple expansion...")
    
    nodes = [
        Node(0, 0, 0, 0),      # Start node
        Node(1, 10, 10, 0),    # End node  
        Node(2, 5, 5, 10),     # High reward node
    ]
    budget = 50  # Increase budget to be more permissive
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=None)  # Remove edge constraint
    
    tree = WUOrienteeringTree(
        problem=problem,
        max_steps=50,  # Small number for debugging
        max_depth=5,
        expansion_worker_num=1,
        simulation_worker_num=1
    )
    
    print(f"Initial root children: {len(tree.root_node.children)}")
    print(f"Root available actions: {tree.root_node.available_actions}")
    
    # Do a few manual iterations
    for i in range(5):
        print(f"\nIteration {i+1}:")
        tree._perform_wu_uct_iteration()
        print(f"  Root children: {len(tree.root_node.children)}")
        print(f"  Root visits: {tree.root_node.visit_count}")
        print(f"  Simulation count: {tree.simulation_count}")
        
        # Show children
        for action, child in tree.root_node.children.items():
            print(f"    Child {action}: visits={child.visit_count}, reward={child.total_reward}")
    
    # Try to extract best path
    try:
        best_path, best_reward = tree._extract_best_complete_path()
        print(f"\nBest path found: {best_path} with reward {best_reward}")
    except Exception as e:
        print(f"Error extracting best path: {e}")


if __name__ == "__main__":
    print("Debugging True WU-UCT Implementation")
    print("=" * 50)
    
    debug_root_state()
    debug_simple_expansion()