"""
Expansion Worker for WU-UCT

Handles tree traversal and node expansion.
After expanding a node, creates work units for simulation workers.
"""

import threading
import time
import random
from typing import Optional, List
from queue import Queue
import math

from WU_UCT.wu_uct_node import WUUCTNode


class WorkUnit:
    """
    Work unit passed from expansion workers to simulation workers.
    
    Contains:
    - Path from root to leaf (for backpropagation)
    - State to simulate from
    - Unique simulation ID
    """
    
    def __init__(self, simulation_id: str, path: List[WUUCTNode], 
                 state_to_simulate, selection_time: float):
        """
        Initialize work unit.
        
        Args:
            simulation_id: Unique identifier for this simulation
            path: List of nodes from root to leaf
            state_to_simulate: State to start simulation from
            selection_time: Time when selection phase started
        """
        self.simulation_id = simulation_id
        self.path = path
        self.state_to_simulate = state_to_simulate
        self.selection_time = selection_time
        self.creation_time = time.time()


class ExpansionWorker(threading.Thread):
    """
    Expansion worker for WU-UCT algorithm.
    
    Responsibilities:
    1. Lock-free tree traversal using WU-UCT selection
    2. Node expansion (when unexplored actions exist)
    3. Create work units for simulation workers
    4. Mark simulations as "started" (update-incomplete)
    
    Key feature: Selection is lock-free or minimally locked!
    """
    
    def __init__(self, worker_id: int, root: WUUCTNode, work_queue: Queue,
                 num_iterations: int, exploration_constant: float = math.sqrt(2),
                 problem=None, max_distance: float = 1.42):
        """
        Initialize expansion worker.
        
        Args:
            worker_id: Unique identifier for this worker
            root: Root node of the search tree
            work_queue: Queue to place work units for simulation workers
            num_iterations: Number of iterations to perform
            exploration_constant: UCT exploration parameter
            problem: Orienteering problem instance (for creating states)
            max_distance: Maximum travel distance constraint (default: 1.42)
        """
        super().__init__()
        self.worker_id = worker_id
        self.root = root
        self.work_queue = work_queue
        self.num_iterations = num_iterations
        self.exploration_constant = exploration_constant
        self.problem = problem
        self.max_distance = max_distance
        
        self.daemon = True
        
        # Statistics
        self.iterations_completed = 0
        self.expansions_performed = 0
        self.total_selection_time = 0.0
        self.lock_free_selections = 0  # Selections without needing locks
        
    def run(self):
        """Main worker loop."""
        for _ in range(self.num_iterations):
            self._perform_iteration()
            self.iterations_completed += 1
    
    def _perform_iteration(self):
        """
        Perform one expansion iteration.
        
        Steps:
        1. Lock-free selection: Traverse tree to leaf using WU-UCT
        2. Expansion: Add new child if possible
        3. Mark as started: Update-incomplete on path
        4. Create work unit: Send to simulation workers
        """
        selection_start = time.time()
        
        # Phase 1: Lock-free selection to find leaf node
        path, leaf_node, leaf_state = self._select_leaf()
        
        self.total_selection_time += time.time() - selection_start
        self.lock_free_selections += 1
        
        # Phase 2: Expansion (if possible)
        node_to_simulate, state_to_simulate = self._expand_if_possible(leaf_node, leaf_state)
        
        # Update path if we expanded
        if node_to_simulate != leaf_node:
            path = path + [node_to_simulate]
        
        # Phase 3: Mark simulation as started (Algorithm 2: Update-Incomplete)
        simulation_id = self._generate_simulation_id()
        self._mark_path_as_started(path, simulation_id)
        
        # Phase 4: Create work unit for simulation workers
        work_unit = WorkUnit(
            simulation_id=simulation_id,
            path=path,
            state_to_simulate=state_to_simulate,
            selection_time=selection_start
        )
        
        self.work_queue.put(work_unit)
    
    def _select_leaf(self):
        """
        Lock-free tree traversal to find a leaf node.
        
        This is the key innovation of WU-UCT: Selection happens WITHOUT
        holding locks. We read statistics optimistically and use predictions
        to account for ongoing simulations.
        
        Returns:
            Tuple of (path, leaf_node, leaf_state)
        """
        current_node = self.root
        current_state = self.problem.create_initial_state() if self.problem else self.root.state
        path = []
        
        while True:
            # Check if we've reached a leaf (no locks needed for read!)
            is_terminal = current_node.is_terminal()
            is_fully_expanded = current_node.is_fully_expanded()
            
            if is_terminal or not is_fully_expanded:
                # Found a leaf node
                path.append(current_node)
                return path, current_node, current_state
            
            if not current_node.children:
                # Node has no children despite being "fully expanded"
                path.append(current_node)
                return path, current_node, current_state
            
            # Select best child using WU-UCT (LOCK-FREE!)
            best_child = current_node.wu_uct_select_child(self.exploration_constant)
            
            if best_child is None:
                path.append(current_node)
                return path, current_node, current_state
            
            # Move to selected child
            path.append(current_node)
            current_node = best_child
            
            # Create next state (assuming state has path attribute)
            if hasattr(best_child.state, 'path') and hasattr(current_state, 'path'):
                action = best_child.state.path[-1]
                current_state = self._create_next_state(current_state, action)
            else:
                current_state = best_child.state
    
    def _expand_if_possible(self, node: WUUCTNode, state):
        """
        Expand node by adding a new child if possible.
        
        This may require brief locking for structural modification.
        
        Args:
            node: Node to potentially expand
            state: Current state
            
        Returns:
            Tuple of (node_to_simulate, state_to_simulate)
        """
        if node.is_fully_expanded() or node.is_terminal():
            return node, state
        
        # Get an untried action (thread-safe)
        action = node.get_untried_action()
        
        if action is None:
            return node, state
        
        # Create new state
        new_state = self._create_next_state(state, action)
        
        # Add child to tree (thread-safe)
        child_node = node.add_child(new_state, action)
        
        self.expansions_performed += 1
        
        return child_node, new_state
    
    def _mark_path_as_started(self, path: List[WUUCTNode], simulation_id: str):
        """
        Mark all nodes in path as having a started simulation.
        
        This is Algorithm 2 (Update-Incomplete) from the paper.
        Allows other workers to account for this ongoing simulation.
        
        Args:
            path: List of nodes from root to leaf
            simulation_id: Unique identifier for this simulation
        """
        for node in path:
            node.mark_simulation_started(simulation_id)
    
    def _create_next_state(self, current_state, action):
        """
        Create next state by applying action.
        
        Args:
            current_state: Current state
            action: Action to apply
            
        Returns:
            New state after applying action, or None if exceeds max_distance
        """
        if hasattr(current_state, 'apply_action'):
            return current_state.apply_action(action)
        elif hasattr(current_state, 'path'):
            # For orienteering-style states
            from orienteering.orienteering_optimized import OrienteeringState
            current_node = current_state.path[-1]
            cost = self.problem.get_distance(current_node, action)
            new_cost = current_state.cost_so_far + cost
            
            # Check max distance constraint
            if new_cost > self.max_distance:
                return None
            
            new_path = current_state.path + [action]
            new_reward = current_state.reward_so_far + self.problem.get_normalized_score(action)
            
            return OrienteeringState(
                self.problem,
                path=new_path,
                cost_so_far=new_cost,
                reward_so_far=new_reward
            )
        else:
            raise NotImplementedError("State must have apply_action or path attribute")
    
    def _generate_simulation_id(self) -> str:
        """
        Generate unique simulation ID.
        
        Returns:
            Unique string identifier
        """
        return f"exp{self.worker_id}_{time.time()}_{random.randint(10000, 99999)}"
    
    def get_statistics(self) -> dict:
        """
        Get worker statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        avg_selection_time = (self.total_selection_time / self.iterations_completed 
                             if self.iterations_completed > 0 else 0)
        
        return {
            'worker_id': self.worker_id,
            'worker_type': 'expansion',
            'iterations_completed': self.iterations_completed,
            'expansions_performed': self.expansions_performed,
            'avg_selection_time': avg_selection_time,
            'lock_free_selections': self.lock_free_selections,
        }
