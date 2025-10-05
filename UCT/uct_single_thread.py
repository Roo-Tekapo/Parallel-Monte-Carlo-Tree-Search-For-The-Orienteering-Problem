"""
UCT (Upper Confidence bounds applied to Trees) implementation for single-threaded MCTS.
Based on the MCTS base implementation but structured for UCT-specific algorithms.
"""

import random
import math
from typing import Optional, List

from orienteering.orienteering import OrienteeringProblem, OrienteeringState, END_NODE


class UCTNode:
    """
    Node class for UCT algorithm.
    Each node represents a state in the search tree.
    """
    
    def __init__(self, state: OrienteeringState, parent: Optional['UCTNode'] = None):
        self.state = state
        self.parent = parent
        self.children: List['UCTNode'] = []
        self.visits = 0
        self.total_reward = 0.0
        
        # Copy and shuffle available actions to avoid aliasing and add randomness
        self.untried_actions = list(state.get_available_actions() or [])
        if self.untried_actions:
            random.shuffle(self.untried_actions)
    
    def __repr__(self):
        try:
            last_node = self.state.path[-1] if self.state.path else None
        except Exception:
            last_node = None
        avg_reward = self.total_reward / self.visits if self.visits > 0 else 0.0
        return f"<UCTNode node={last_node} visits={self.visits} avg_reward={avg_reward:.2f} children={len(self.children)}>"
    
    def is_fully_expanded(self) -> bool:
        """Check if all available actions have been tried."""
        return len(self.untried_actions) == 0
    
    def is_terminal(self) -> bool:
        """Check if this node represents a terminal state."""
        return self.state.is_terminal()
    
    def add_child(self, child_node: 'UCTNode') -> 'UCTNode':
        """Add a child node and maintain parent-child relationship."""
        child_node.parent = self
        self.children.append(child_node)
        return child_node
    
    def find_child_by_action(self, action) -> Optional['UCTNode']:
        """Find child node that corresponds to taking the given action."""
        for child in self.children:
            try:
                if child.state.path and child.state.path[-1] == action:
                    return child
            except Exception:
                continue
        return None
    
    def uct_select_child(self, exploration_constant: float = math.sqrt(2)) -> 'UCTNode':
        """
        Select child using UCT (Upper Confidence Bounds for Trees) formula.
        UCT = exploitation + exploration
        UCT = (reward/visits) + c * sqrt(ln(parent_visits) / child_visits)
        """
        if not self.children:
            raise ValueError("Cannot select child from node with no children")
        
        # Prefer unvisited children first
        unvisited = [child for child in self.children if child.visits == 0]
        if unvisited:
            return random.choice(unvisited)
        
        # Calculate UCT values for all children
        parent_visits = max(1, self.visits)  # Prevent division by zero
        ln_parent_visits = math.log(parent_visits)
        
        best_child = None
        best_uct_value = float('-inf')
        
        for child in self.children:
            if child.visits == 0:
                # This shouldn't happen due to the check above, but just in case
                return child
            
            exploitation = child.total_reward / child.visits
            exploration = exploration_constant * math.sqrt(ln_parent_visits / child.visits)
            uct_value = exploitation + exploration
            
            if uct_value > best_uct_value:
                best_uct_value = uct_value
                best_child = child
        
        return best_child
    
    def get_average_reward(self) -> float:
        """Get the average reward for this node."""
        return self.total_reward / self.visits if self.visits > 0 else 0.0


class UCTSingleThread:
    """
    Single-threaded UCT (Upper Confidence bounds applied to Trees) implementation.
    This serves as the base for the parallel WU-UCT algorithm.
    """
    
    def __init__(self, problem: OrienteeringProblem, iterations: int, 
                 exploration_constant: float = math.sqrt(2),
                 max_distance: Optional[float] = None):
        self.problem = problem
        self.iterations = iterations
        self.exploration_constant = exploration_constant
        self.max_distance = max_distance
        
        self.root: Optional[UCTNode] = None
        self.current_iteration = 0
    
    def initialize_root(self) -> UCTNode:
        """Initialize the root node if it doesn't exist."""
        if self.root is None:
            root_state = OrienteeringState(self.problem)
            self.root = UCTNode(root_state)
            self.current_iteration = 0
        return self.root
    
    def reset(self):
        """Reset the search tree."""
        self.root = None
        self.current_iteration = 0
    
    def selection(self, node: UCTNode) -> UCTNode:
        """
        Selection phase: Traverse tree using UCT until reaching a leaf node.
        Returns a leaf node (either not fully expanded or terminal).
        """
        current = node
        
        while not current.is_terminal():
            if not current.is_fully_expanded():
                # Found a node that can be expanded
                return current
            elif current.children:
                # Select best child using UCT
                current = current.uct_select_child(self.exploration_constant)
            else:
                # Dead end - no children and no untried actions
                # Return this node so expansion/simulation can handle it
                return current
        
        return current
    
    def expansion(self, node: UCTNode) -> UCTNode:
        """
        Expansion phase: Add a new child node by trying an untried action.
        Returns the newly created child node.
        """
        if not node.untried_actions:
            # Node is fully expanded, return itself
            return node
        
        # Select a random untried action
        action = node.untried_actions.pop()
        new_state = node.state.apply_action(action)
        child_node = UCTNode(new_state, parent=node)
        node.add_child(child_node)
        
        return child_node
    
    def simulation(self, state: OrienteeringState) -> float:
        """
        Simulation phase: Run a random simulation from the given state to terminal.
        Returns the reward obtained from the simulation.
        """
        current = state.copy()
        
        while not current.is_terminal():
            actions = current.get_available_actions()
            if not actions:
                # Dead-end: try to force completion to END_NODE if possible
                current_node = current.path[-1]
                if current_node != END_NODE:
                    # Check if we can reach END_NODE directly within budget
                    cost_to_end = current.problem.get_distance(current_node, END_NODE)
                    if current.cost_so_far + cost_to_end <= current.problem.budget:
                        # Force move to END_NODE to complete the path
                        try:
                            current = current.apply_action(END_NODE)
                            break
                        except ValueError:
                            # Can't apply action, return penalized reward
                            pass
                # Dead end - apply penalty for incomplete path
                return current.get_reward() * 0.8  # 20% penalty
            
            # Random action selection
            action = random.choice(actions)
            current = current.apply_action(action)
        
        return current.get_reward()
    
    def backpropagation(self, node: UCTNode, reward: float):
        """
        Backpropagation phase: Update visit counts and rewards up the tree.
        """
        current = node
        while current is not None:
            current.visits += 1
            current.total_reward += reward
            current = current.parent
    
    def get_best_child(self, node: UCTNode) -> Optional[UCTNode]:
        """Get the child with the highest average reward."""
        if not node.children:
            return None
        
        return max(node.children, key=lambda child: child.get_average_reward())
    
    def get_best_path(self) -> OrienteeringState:
        """
        Get the best path by following children with highest average rewards.
        """
        if self.root is None:
            raise ValueError("No search has been performed yet")
        
        current = self.root
        while current.children:
            current = self.get_best_child(current)
        
        return current.state
    
    def run_iteration(self) -> dict:
        """
        Run a single MCTS iteration and return information about it.
        Returns a dictionary with iteration details for debugging/visualization.
        """
        root = self.initialize_root()
        
        # Selection: Find leaf node
        leaf = self.selection(root)
        
        # Track selection path for debugging
        selection_path = []
        current = leaf
        while current is not None:
            selection_path.append(current)
            current = current.parent
        selection_path.reverse()
        
        # Expansion: Add new child if possible
        if not leaf.is_terminal():
            leaf = self.expansion(leaf)
        
        # Simulation: Random rollout
        reward = self.simulation(leaf.state)
        
        # Backpropagation: Update statistics
        self.backpropagation(leaf, reward)
        
        self.current_iteration += 1
        
        # Return iteration information
        return {
            'iteration': self.current_iteration,
            'leaf': leaf,
            'reward': reward,
            'selection_path': selection_path,
            'best_child': self.get_best_child(root)
        }
    
    def run(self) -> OrienteeringState:
        """
        Run the complete UCT algorithm for the specified number of iterations.
        Returns the best state found.
        """
        self.initialize_root()
        
        for _ in range(self.iterations):
            self.run_iteration()
        
        return self.get_best_path()
    
    def get_statistics(self) -> dict:
        """Get statistics about the current search tree."""
        if self.root is None:
            return {'nodes': 0, 'iterations': 0}
        
        def count_nodes(node):
            count = 1
            for child in node.children:
                count += count_nodes(child)
            return count
        
        return {
            'nodes': count_nodes(self.root),
            'iterations': self.current_iteration,
            'root_visits': self.root.visits,
            'root_children': len(self.root.children)
        }


if __name__ == "__main__":
    # Test the UCT implementation
    nodes, budget = OrienteeringProblem.load_problem(
        "../OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    )
    
    problem = OrienteeringProblem(nodes, budget)
    uct = UCTSingleThread(problem, iterations=10000)
    
    print("Running UCT algorithm...")
    best_state = uct.run()
    
    print(f"Best path: {best_state.get_path()}")
    print(f"Total reward: {best_state.get_reward()}")
    print(f"Total cost: {best_state.get_cost()}")
    print(f"Statistics: {uct.get_statistics()}")