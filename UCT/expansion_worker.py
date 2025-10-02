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
import time
from typing import Optional, Dict, Any

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from .uct_single_thread import UCTNode
from .work_units import WorkUnit, SimulationResult


class WUUCTExpansionWorker(threading.Thread):
    """
    The expansion worker manages the search tree structure.
    
    Key responsibilities:
    - Tree traversal using UCT selection
    - Node expansion when new actions are available
    - Work unit generation for simulation workers
    - Result processing and backpropagation
    - Thread-safe tree access coordination
    """
    
    def __init__(self, problem: OrienteeringProblem, worker_id: int = 0, 
                 exploration_constant: float = math.sqrt(2),
                 max_distance: Optional[float] = None,
                 work_queue: Optional[queue.Queue] = None,
                 result_queue: Optional[queue.Queue] = None,
                 max_iterations: Optional[int] = None,
                 max_time: Optional[float] = None):
        """
        Initialize the expansion worker.
        
        Args:
            problem: The orienteering problem instance
            worker_id: Unique identifier for this expansion worker
            exploration_constant: UCT exploration parameter (default: √2)
            max_distance: Maximum distance limit for simulations (optional)
            work_queue: Shared work queue for simulation tasks (optional)
            result_queue: Shared result queue for simulation results (optional)
            max_iterations: Maximum iterations for this worker (optional)
            max_time: Maximum time for this worker (optional)
        """
        super().__init__(daemon=True)
        self.problem = problem
        self.worker_id = worker_id
        self.exploration_constant = exploration_constant
        self.max_distance = max_distance
        self.max_iterations = max_iterations
        self.max_time = max_time
        self.root: Optional[UCTNode] = None
        self.work_counter = 0
        
        # Thread control
        self.running = False
        self.iterations_completed = 0
        self.start_time = 0
        
        # Thread safety lock for tree modifications
        self.lock = threading.Lock()
        
        # Communication queues with simulation workers (shared or create new)
        self.work_queue: queue.Queue[WorkUnit] = work_queue or queue.Queue()
        self.result_queue: queue.Queue[SimulationResult] = result_queue or queue.Queue()
        
        # Keep track of pending work units for THIS worker only
        self.pending_work: Dict[int, UCTNode] = {}
        
        # Per-thread statistics
        self.nodes_expanded = 0
        self.simulations_requested = 0
        self.simulations_processed = 0
        self.best_reward = 0.0
    
    def initialize_root(self) -> UCTNode:
        """
        Initialize the root node if it doesn't exist.
        
        Returns:
            The root node of the search tree
        """
        if self.root is None:
            # Apply max_distance constraint to the problem if specified
            if self.max_distance is not None:
                self.problem.max_edge_distance = self.max_distance
                
            root_state = OrienteeringState(self.problem)
            self.root = UCTNode(root_state)
        return self.root
    
    def run(self):
        """Main expansion worker thread loop."""
        self.running = True
        self.start_time = time.time()
        
        while self.should_continue():
            try:
                # Process any completed simulation results
                self._process_simulation_results()
                
                # Perform expansion iteration
                work_unit = self.selection_and_expansion()
                if work_unit is not None:
                    # Send work unit to simulation workers
                    self.work_queue.put(work_unit)
                    self.iterations_completed += 1
                else:
                    # No work available, small delay to prevent busy waiting
                    time.sleep(0.001)
                
                # Small delay to prevent overwhelming the simulation queue
                if self.work_queue.qsize() > 500:
                    time.sleep(0.001)
                    
            except Exception as e:
                print(f"Expansion Worker {self.worker_id} error: {e}")
                break
        
        self.running = False
    
    def should_continue(self) -> bool:
        """Check if worker should continue running."""
        if not self.running:
            return False
            
        # Check iteration limit
        if self.max_iterations and self.iterations_completed >= self.max_iterations:
            return False
            
        # Check time limit
        if self.max_time and (time.time() - self.start_time) >= self.max_time:
            return False
            
        return True
    
    def _process_simulation_results(self):
        """Process completed simulation results for this worker."""
        try:
            while True:
                try:
                    result = self.result_queue.get_nowait()
                    # Check if this result belongs to this worker
                    worker_id = result.work_id >> 16
                    if worker_id == self.worker_id and result.work_id in self.pending_work:
                        self.process_simulation_result(result)
                    elif worker_id != self.worker_id:
                        # Put it back for the correct worker
                        self.result_queue.put(result)
                        break
                except queue.Empty:
                    break
        except Exception as e:
            print(f"Error processing simulation results: {e}")
    
    def stop(self):
        """Stop the expansion worker."""
        self.running = False
    
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
                        self.nodes_expanded += 1
                        
                        # Create work unit for simulation workers
                        work_id = self._get_unique_work_id()
                        work_unit = WorkUnit(child_node, new_state, work_id)
                        self.pending_work[work_id] = child_node
                        self.simulations_requested += 1
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
                work_id = self._get_unique_work_id()
                work_unit = WorkUnit(current, current.state, work_id)
                self.pending_work[work_id] = current
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
                self.simulations_processed += 1
                
                # Track best reward seen by this worker
                if result.reward > self.best_reward:
                    self.best_reward = result.reward
                
                # Backpropagation - update all nodes in the path to root
                current = node
                while current is not None:
                    current.visits += 1
                    current.total_reward += result.reward
                    current = current.parent
    
    def get_thread_statistics(self) -> dict:
        """
        Get statistics for this expansion worker thread.
        
        Returns:
            Dictionary containing thread statistics
        """
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        return {
            'worker_id': self.worker_id,
            'iterations': self.iterations_completed,
            'nodes_expanded': self.nodes_expanded,
            'simulations_requested': self.simulations_requested,
            'simulations_processed': self.simulations_processed,
            'pending_simulations': len(self.pending_work),
            'best_reward': self.best_reward,
            'iterations_per_second': self.iterations_completed / elapsed_time if elapsed_time > 0 else 0
        }

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
    
    def _get_unique_work_id(self) -> int:
        """
        Generate a unique work ID by encoding worker ID in high bits.
        This prevents task ID conflicts between multiple expansion workers.
        
        Returns:
            Unique work ID combining worker_id and work_counter
        """
        self.work_counter += 1
        return (self.worker_id << 16) | self.work_counter
    
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