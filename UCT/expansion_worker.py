"""
Expansion worker for WU-UCT algorithm.

The expansion worker is responsible for:
1. Managing the search tree structure
2. Performing selection and expansion phases
3. Coordinating with simulation workers
4. Processing simulation results and backpropagating rewards

This is the "brain" of the WU-UCT algorithm that maintains the tree
while simulation workers handle the computationally intensive rollouts.
"""

import threading
import queue
import math
from typing import Optional, Dict, Any

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from .uct_single_thread import UCTNode
from .work_units import WorkUnit, SimulationResult


class WUUCTExpansionWorker:
    """
    The expansion worker manages the search tree structure.
    
    Key responsibilities:
    - Tree traversal using UCT selection
    - Node expansion when new actions are available
    - Work unit generation for simulation workers
    - Result processing and backpropagation
    - Thread-safe tree access coordination
    """
    
    def __init__(self, problem: OrienteeringProblem, exploration_constant: float = math.sqrt(2)):
        """
        Initialize the expansion worker.
        
        Args:
            problem: The orienteering problem instance
            exploration_constant: UCT exploration parameter (default: √2)
        """
        self.problem = problem
        self.exploration_constant = exploration_constant
        self.root: Optional[UCTNode] = None
        self.work_counter = 0
        
        # Thread safety lock for tree modifications
        self.lock = threading.Lock()
        
        # Communication queues with simulation workers
        self.work_queue: queue.Queue[WorkUnit] = queue.Queue()
        self.result_queue: queue.Queue[SimulationResult] = queue.Queue()
        
        # Keep track of pending work units to match results with nodes
        self.pending_work: Dict[int, UCTNode] = {}
    
    def initialize_root(self) -> UCTNode:
        """
        Initialize the root node if it doesn't exist.
        
        Returns:
            The root node of the search tree
        """
        if self.root is None:
            root_state = OrienteeringState(self.problem)
            self.root = UCTNode(root_state)
        return self.root
    
    def selection_and_expansion(self) -> Optional[WorkUnit]:
        """
        Perform selection and expansion to find a node that needs simulation.
        
        This is the core method that:
        1. Traverses the tree using UCT selection
        2. Expands a node by adding a new child
        3. Creates a work unit for simulation
        
        Returns:
            WorkUnit for simulation if successful, None if tree is exhausted
        """
        with self.lock:
            root = self.initialize_root()
            
            # Selection phase - traverse tree to find a leaf node
            current = root
            while not current.is_terminal():
                if not current.is_fully_expanded():
                    # Expansion phase - this node has untried actions
                    if current.untried_actions:
                        # Select an untried action and create new child
                        action = current.untried_actions.pop()
                        new_state = current.state.apply_action(action)
                        child_node = UCTNode(new_state, parent=current)
                        current.add_child(child_node)
                        
                        # Create work unit for simulation workers
                        self.work_counter += 1
                        work_unit = WorkUnit(child_node, new_state, self.work_counter)
                        self.pending_work[self.work_counter] = child_node
                        return work_unit
                    else:
                        # This shouldn't happen - node claims to not be fully expanded
                        # but has no untried actions
                        break
                elif current.children:
                    # Node is fully expanded, select best child using UCT
                    current = current.uct_select_child(self.exploration_constant)
                else:
                    # Dead end - no children and no untried actions
                    break
            
            # If we reach here, we found a terminal node or dead end
            if current.is_terminal():
                # Create work unit for direct evaluation of terminal state
                self.work_counter += 1
                work_unit = WorkUnit(current, current.state, self.work_counter)
                self.pending_work[self.work_counter] = current
                return work_unit
            
            # No work available (shouldn't happen in practice)
            return None
    
    def process_simulation_result(self, result: SimulationResult):
        """
        Process a simulation result by performing backpropagation.
        
        This method:
        1. Finds the node corresponding to the work unit
        2. Backpropagates the reward up the tree
        3. Updates visit counts and total rewards
        
        Args:
            result: The simulation result to process
        """
        with self.lock:
            if result.work_id in self.pending_work:
                # Find the node that corresponds to this result
                node = self.pending_work.pop(result.work_id)
                
                # Backpropagation - update all nodes in the path to root
                current = node
                while current is not None:
                    current.visits += 1
                    current.total_reward += result.reward
                    current = current.parent
    
    def get_best_path(self) -> Optional[OrienteeringState]:
        """
        Get the best path found so far by following highest reward children.
        
        Returns:
            The best state found, or None if no search has been performed
        """
        with self.lock:
            if self.root is None:
                return None
            
            # Follow the path of children with highest average rewards
            current = self.root
            while current.children:
                best_child = max(current.children, 
                               key=lambda child: child.get_average_reward())
                current = best_child
            
            return current.state
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current statistics about the search tree.
        
        Returns:
            Dictionary with tree statistics including node count, visits, etc.
        """
        with self.lock:
            if self.root is None:
                return {
                    'nodes': 0, 
                    'root_visits': 0, 
                    'root_children': 0,
                    'pending_work': 0,
                    'work_counter': 0
                }
            
            def count_nodes(node):
                """Recursively count all nodes in the subtree."""
                count = 1
                for child in node.children:
                    count += count_nodes(child)
                return count
            
            return {
                'nodes': count_nodes(self.root),
                'root_visits': self.root.visits,
                'root_children': len(self.root.children),
                'pending_work': len(self.pending_work),
                'work_counter': self.work_counter
            }
    
    def reset(self):
        """
        Reset the expansion worker for a new search.
        Clears the tree and all tracking data.
        """
        with self.lock:
            self.root = None
            self.work_counter = 0
            self.pending_work.clear()
            
            # Clear queues
            while not self.work_queue.empty():
                try:
                    self.work_queue.get_nowait()
                except queue.Empty:
                    break
            
            while not self.result_queue.empty():
                try:
                    self.result_queue.get_nowait()
                except queue.Empty:
                    break