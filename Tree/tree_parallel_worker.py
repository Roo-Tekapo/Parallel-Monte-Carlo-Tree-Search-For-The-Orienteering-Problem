"""
Tree Parallel Worker

Worker thread for tree-parallel MCTS.
Each worker performs complete MCTS iterations on the shared tree
using standard UCT without virtual loss.
"""

import threading
import math
import random
import time
from typing import Optional

from Tree.orienteering_adapter import OrienteeringProblem, OrienteeringState, END_NODE
from Tree.tree_parallel_node import TreeParallelNode


class TreeParallelWorker(threading.Thread):
    """
    Worker thread for tree-parallel MCTS.
    
    Performs complete MCTS iterations (selection, expansion, simulation, backpropagation)
    on a shared tree structure. Uses standard UCT formula for selection.
    """
    
    def __init__(self,
                 problem: OrienteeringProblem,
                 root: TreeParallelNode,
                 worker_id: int,
                 iterations_per_worker: int,
                 exploration_constant: float = math.sqrt(2),
                 tree_lock: Optional[threading.Lock] = None):
        """
        Initialize the tree parallel worker.
        
        Args:
            problem: The orienteering problem instance
            root: Shared root node of the search tree
            worker_id: Unique identifier for this worker
            iterations_per_worker: Number of MCTS iterations this worker should perform
            exploration_constant: UCT exploration parameter (default: √2)
            tree_lock: Optional global tree lock for synchronization
        """
        super().__init__()
        self.problem = problem
        self.root = root
        self.worker_id = worker_id
        self.iterations_per_worker = iterations_per_worker
        self.exploration_constant = exploration_constant
        self.tree_lock = tree_lock if tree_lock is not None else threading.Lock()
        
        # Worker statistics
        self.iterations_completed = 0
        self.simulations_completed = 0
        self.total_simulation_time = 0.0
        self.lock_contentions = 0  # Times we encountered lock contention (collisions)
        
        # Threading
        self.daemon = True
    
    def run(self):
        """Main worker loop performing MCTS iterations."""
        for iteration in range(self.iterations_per_worker):
            self._perform_iteration()
            self.iterations_completed += 1
    
    def _perform_iteration(self):
        """
        Perform one complete MCTS iteration.
        
        Steps:
        1. Selection: Traverse tree using UCT until leaf node
        2. Expansion: Add new child if possible
        3. Simulation: Perform random rollout
        4. Backpropagation: Update all nodes in path
        """
        # Phase 1: Selection - find leaf node using standard UCT
        path, leaf_node, leaf_state = self._select_leaf()
        
        # Phase 2: Expansion - create new child if possible
        expanded_node, expanded_state = self._expand_leaf(leaf_node, leaf_state)
        
        # Phase 3: Simulation - perform random rollout
        reward = self._simulate(expanded_state)
        self.simulations_completed += 1
        
        # Phase 4: Backpropagation - update all nodes in path
        final_path = path + [expanded_node] if expanded_node != leaf_node else path
        self._backpropagate(final_path, reward)
    
    def _select_leaf(self):
        """
        Select a leaf node using standard UCT policy.
        
        Returns:
            Tuple of (path, leaf_node, leaf_state) where path includes leaf_node
        """
        current_node = self.root
        current_state = OrienteeringState(self.problem)
        path = []
        
        while True:
            # Check if node is fully expanded
            if not current_node.is_fully_expanded():
                # Found a leaf node (not fully expanded)
                path.append(current_node)
                return path, current_node, current_state
            
            if not current_node.children:
                # Terminal node or node with no children
                path.append(current_node)
                return path, current_node, current_state
            
            # Select best child using standard UCT
            best_child = current_node.uct_select_child(self.exploration_constant)
            
            # Move to selected child
            path.append(current_node)
            child_action = best_child.state.path[-1]
            current_state = self._create_next_state(current_state, child_action)
            current_node = best_child
    
    def _expand_leaf(self, leaf_node: TreeParallelNode, leaf_state: OrienteeringState):
        """
        Expand the leaf node by adding a new child if possible.
        
        Args:
            leaf_node: The leaf node to expand
            leaf_state: The state corresponding to the leaf node
            
        Returns:
            Tuple of (expanded_node, expanded_state)
            If expansion occurs, returns (new_child, new_state)
            If no expansion, returns (leaf_node, leaf_state)
        """
        # Check if lock is available without blocking (fast check for collision detection)
        lock_available = self.tree_lock.acquire(blocking=False)
        if not lock_available:
            # Lock contention detected - count and then wait
            self.lock_contentions += 1
            self.tree_lock.acquire(blocking=True)
        
        try:
            # Double-check untried actions under lock
            with leaf_node._node_lock:
                if not leaf_node.untried_actions:
                    # No expansion possible
                    return leaf_node, leaf_state
                
                # Pop an untried action
                action_to_expand = leaf_node.untried_actions.pop()
            
            # Create new child node (outside inner lock)
            new_state = self._create_next_state(leaf_state, action_to_expand)
            new_child = TreeParallelNode(new_state, parent=leaf_node)
            
            # Add child to parent
            leaf_node.add_child(new_child)
            
            return new_child, new_state
        finally:
            self.tree_lock.release()
    
    def _simulate(self, state: OrienteeringState) -> float:
        """
        Perform a random simulation from the given state.
        
        Args:
            state: Starting state for simulation
            
        Returns:
            Reward obtained from the simulation
        """
        start_time = time.time()
        
        simulation_state = state.copy()
        max_steps = 1000  # Prevent infinite loops
        steps = 0
        
        while not simulation_state.is_terminal() and steps < max_steps:
            steps += 1
            available_actions = simulation_state.get_available_actions()
            
            if not available_actions:
                break
            
            # Random action selection
            action = random.choice(available_actions)
            simulation_state = self._create_next_state(simulation_state, action)
        
        # Calculate final reward
        reward = simulation_state.get_reward()
        
        # Add completion bonus/penalty
        if simulation_state.is_terminal():
            # Small bonus for completing the path
            reward += 0.05
        elif len(simulation_state.path) > 2:
            # Penalty for incomplete paths
            reward *= 0.9
        
        # Update timing statistics
        self.total_simulation_time += time.time() - start_time
        
        return reward
    
    def _backpropagate(self, path, reward: float):
        """
        Update all nodes in the path with the simulation result.
        
        Args:
            path: List of nodes from root to leaf
            reward: Reward to backpropagate
        """
        for node in path:
            node.update(reward)
    
    def _create_next_state(self, current_state: OrienteeringState, action: int) -> OrienteeringState:
        """
        Create the next state by taking the given action.
        
        Args:
            current_state: Current orienteering state
            action: Node ID to move to
            
        Returns:
            New orienteering state after taking the action
        """
        return current_state.apply_action(action)
    
    def get_statistics(self):
        """
        Get worker performance statistics.
        
        Returns:
            Dictionary with worker statistics
        """
        avg_simulation_time = (self.total_simulation_time / self.simulations_completed 
                              if self.simulations_completed > 0 else 0)
        
        collision_rate = (self.lock_contentions / self.iterations_completed
                         if self.iterations_completed > 0 else 0)
        
        return {
            'worker_id': self.worker_id,
            'iterations_completed': self.iterations_completed,
            'simulations_completed': self.simulations_completed,
            'total_simulation_time': self.total_simulation_time,
            'avg_simulation_time': avg_simulation_time,
            'lock_contentions': self.lock_contentions,
            'collision_rate': collision_rate
        }
