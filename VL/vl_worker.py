"""
Virtual Loss Worker Implementation

This worker performs MCTS iterations using the Virtual Loss mechanism
for parallel coordination. Unlike WU-UCT which tracks pending simulations,
VL applies fixed penalties to discourage redundant exploration.
"""

import threading
import math
import time
import random
from typing import Optional, List

from VL.orienteering_adapter import OrienteeringProblem, OrienteeringState, END_NODE
from VL.vl_node import VLNode


class VLWorker(threading.Thread):
    """
    Worker thread that performs MCTS iterations with Virtual Loss coordination.
    
    Virtual Loss Mechanism:
    1. Selection: Traverse tree using standard UCT (affected by virtual loss)
    2. Apply VL: Add fixed penalty to all nodes in selected path
    3. Expansion: Create new child node if possible
    4. Simulation: Perform random rollout
    5. Remove VL & Backprop: Remove penalties and update with real results
    
    Key Difference from WU-UCT:
    - WU-UCT: Modifies UCT formula with pending simulation counts
    - VL: Uses standard UCT but temporarily penalizes node rewards
    """
    
    def __init__(self,
                 problem: OrienteeringProblem,
                 root: VLNode,
                 worker_id: int,
                 iterations_per_worker: int,
                 exploration_constant: float = math.sqrt(2),
                 virtual_loss_value: float = 1.0,
                 max_distance: Optional[float] = None):
        """
        Initialize the Virtual Loss worker.
        
        Args:
            problem: The orienteering problem instance
            root: Shared root node of the search tree
            worker_id: Unique identifier for this worker
            iterations_per_worker: Number of MCTS iterations to perform
            exploration_constant: UCT exploration parameter (default: √2)
            virtual_loss_value: Fixed penalty value to apply (default: 1.0)
            max_distance: Maximum distance constraint for simulations
        """
        super().__init__()
        self.problem = problem
        self.root = root
        self.worker_id = worker_id
        self.thread_id = f"worker_{worker_id}"
        self.iterations_per_worker = iterations_per_worker
        self.exploration_constant = exploration_constant
        self.virtual_loss_value = virtual_loss_value
        self.max_distance = max_distance
        
        # Worker statistics
        self.iterations_completed = 0
        self.simulations_completed = 0
        self.total_simulation_time = 0.0
        self.virtual_loss_collisions = 0  # Times we selected a path with existing VL
        
        # Threading
        self.daemon = True
        
        # For visualization
        self.last_selection_path = []
    
    def run(self):
        """
        Main worker loop performing MCTS iterations.
        """
        for iteration in range(self.iterations_per_worker):
            self._perform_iteration()
            self.iterations_completed += 1
    
    def _perform_iteration(self):
        """
        Perform one complete MCTS iteration with Virtual Loss.
        
        Virtual Loss Protocol:
        1. Select path using standard UCT (affected by existing VL)
        2. Apply fixed virtual loss to entire path
        3. Expand and simulate
        4. Remove virtual loss and backpropagate real result
        """
        # Phase 1: Selection - traverse tree to leaf node
        path, leaf_node, leaf_state = self._select_leaf()
        
        # Store path for visualization
        if leaf_state and hasattr(leaf_state, 'path'):
            self.last_selection_path = leaf_state.path[:]
        
        # Check for collisions (selecting nodes with existing VL)
        collision_count = sum(1 for node in path if node.get_virtual_loss_count() > 0)
        if collision_count > 0:
            self.virtual_loss_collisions += 1
        
        # Phase 2: Apply Virtual Loss to selected path
        self._apply_virtual_loss(path)
        
        try:
            # Phase 3: Expansion
            expanded_node, expanded_state = self._expand_leaf(leaf_node, leaf_state)
            
            # Update path if expansion occurred
            final_path = path
            if expanded_node != leaf_node:
                final_path = path + [expanded_node]
                # Apply virtual loss to expanded node too
                expanded_node.apply_virtual_loss(self.thread_id, self.virtual_loss_value)
            
            # Phase 4: Simulation
            reward = self._simulate(expanded_state)
            self.simulations_completed += 1
            
            # Phase 5: Remove Virtual Loss and Backpropagate
            self._remove_virtual_loss_and_backpropagate(final_path, reward)
            
        except Exception as e:
            # Ensure virtual loss is removed even if error occurs
            self._remove_virtual_loss(path)
            raise e
    
    def _select_leaf(self):
        """
        Traverse the tree from root to a leaf node using UCT selection.
        
        A leaf node is defined as:
        - A terminal state, OR
        - A node that is not fully expanded (has untried actions)
        
        Selection uses standard UCT formula, but the exploitation term
        is affected by any virtual losses currently applied to nodes.
        
        Returns:
            Tuple of (path, leaf_node, leaf_state)
            - path: List of nodes from root to leaf
            - leaf_node: The selected leaf node
            - leaf_state: The state at the leaf
        """
        path = []
        current_node = self.root
        current_state = current_node.state.copy()
        
        path.append(current_node)
        
        # Traverse until we reach a leaf node
        # Leaf = terminal OR not fully expanded (has untried actions)
        while current_node.is_fully_expanded() and not current_state.is_terminal():
            # Use standard UCT selection (affected by virtual loss)
            current_node = current_node.uct_select_child(self.exploration_constant)
            path.append(current_node)
            
            # Update state
            # Get the action that led to this child
            last_node_id = current_state.path[-1]
            next_node_id = current_node.state.path[-1]
            
            if next_node_id != last_node_id:
                current_state = self._create_next_state(current_state, next_node_id)
        
        return path, current_node, current_state
    
    def _apply_virtual_loss(self, path: List[VLNode]):
        """
        Apply virtual loss to all nodes in the path.
        
        This temporarily penalizes these nodes, making them less attractive
        to other threads until this simulation completes.
        
        Args:
            path: List of nodes to apply virtual loss to
        """
        for node in path:
            node.apply_virtual_loss(self.thread_id, self.virtual_loss_value)
    
    def _remove_virtual_loss(self, path: List[VLNode]):
        """
        Remove virtual loss from all nodes in the path.
        
        Args:
            path: List of nodes to remove virtual loss from
        """
        for node in path:
            node.remove_virtual_loss(self.thread_id)
    
    def _expand_leaf(self, leaf_node: VLNode, leaf_state: OrienteeringState):
        """
        Expand the leaf node by adding a new child if possible.
        
        Args:
            leaf_node: The leaf node to expand
            leaf_state: The state at the leaf
            
        Returns:
            Tuple of (node, state) - either (new_child, new_state) or (leaf, leaf_state)
        """
        with leaf_node._vl_lock:
            # Check if expansion is possible
            if not leaf_node.untried_actions:
                return leaf_node, leaf_state
            
            # Select random untried action
            action = leaf_node.untried_actions.pop()
            
            # Create new child
            new_state = self._create_next_state(leaf_state, action)
            new_child = VLNode(new_state, parent=leaf_node)
            
            # Add to parent
            leaf_node.children.append(new_child)
            
            return new_child, new_state
    
    def _simulate(self, state: OrienteeringState) -> float:
        """
        Perform random simulation from the given state.
        
        Args:
            state: Starting state for simulation
            
        Returns:
            Final reward from simulation
        """
        start_time = time.time()
        
        simulation_state = state.copy()
        
        # Random rollout until terminal or no actions
        while not simulation_state.is_terminal():
            available_actions = simulation_state.get_available_actions()
            
            if not available_actions:
                break
            
            # Random action
            action = random.choice(available_actions)
            simulation_state = self._create_next_state(simulation_state, action)
        
        # Calculate final reward with bonuses/penalties
        reward = simulation_state.reward_so_far
        
        if simulation_state.is_terminal():
            # Bonus for completing the path
            reward += 0.15  # 15% bonus for normalized rewards
        else:
            # Penalty for incomplete paths
            if len(simulation_state.path) > 2:
                reward *= 0.7  # 30% penalty
        
        self.total_simulation_time += time.time() - start_time
        
        return reward
    
    def _create_next_state(self, current_state: OrienteeringState, action: int) -> OrienteeringState:
        """
        Create next state by taking an action.
        
        Args:
            current_state: Current state
            action: Node ID to move to
            
        Returns:
            New state after taking the action
        """
        current_node = current_state.path[-1]
        cost_to_action = self.problem.get_distance(current_node, action)
        
        new_path = current_state.path + [action]
        new_cost = current_state.cost_so_far + cost_to_action
        new_reward = current_state.reward_so_far + self.problem.get_normalized_score(action)
        
        return OrienteeringState(
            self.problem,
            path=new_path,
            cost_so_far=new_cost,
            reward_so_far=new_reward
        )
    
    def _remove_virtual_loss_and_backpropagate(self, path: List[VLNode], reward: float):
        """
        Remove virtual loss from path and backpropagate the real simulation result.
        
        This is atomic for each node - virtual loss removal and update happen together.
        
        Args:
            path: List of nodes to update
            reward: Reward to backpropagate
        """
        for node in path:
            # Remove virtual loss for this thread
            node.remove_virtual_loss(self.thread_id)
            
            # Update with real result
            node.update(reward)
    
    def get_statistics(self):
        """
        Get worker performance statistics.
        
        Returns:
            Dictionary with worker stats
        """
        avg_sim_time = (self.total_simulation_time / self.simulations_completed
                       if self.simulations_completed > 0 else 0)
        
        collision_rate = (self.virtual_loss_collisions / self.iterations_completed
                         if self.iterations_completed > 0 else 0)
        
        return {
            'worker_id': self.worker_id,
            'iterations_completed': self.iterations_completed,
            'simulations_completed': self.simulations_completed,
            'total_simulation_time': self.total_simulation_time,
            'avg_simulation_time': avg_sim_time,
            'virtual_loss_collisions': self.virtual_loss_collisions,
            'collision_rate': collision_rate
        }
