"""
WU-UCT Node class - Extends UCTNode with Watch the Unobservable mechanism.

This node class is specifically designed for parallel WU-UCT algorithm and implements
the "Watch the Unobservable" mechanism from the WU-UCT paper.

Includes optimizations for atomic virtual loss operations using fine-grained locking.
"""

import random
import math
import threading
from typing import Optional, List

from UCT.orienteering_adapter import OrienteeringState
from .uct_single_thread import UCTNode


class WUUCTNode(UCTNode):
    """
    Node class for WU-UCT algorithm with Watch the Unobservable mechanism.
    
    Extends the base UCTNode with tracking for pending simulations (unobserved samples).
    This allows the parallel WU-UCT algorithm to account for in-flight simulations
    when making selection decisions.
    
    Includes optimizations:
    - Atomic virtual loss operations via per-node locking
    - Thread-safe pending simulation tracking
    - Reduced lock contention for parallel traversal
    """
    
    def __init__(self, state: OrienteeringState, parent: Optional['WUUCTNode'] = None):
        super().__init__(state, parent)
        
        # WU-UCT Core: Dual visit counters for tracking unobserved samples
        # children_visit_count: ALL simulations (including ongoing) - corresponds to N_c + O_c
        # children_completed_visit_count: ONLY finished simulations - corresponds to N_c  
        self.children_visit_count = []  # Total visits (including ongoing)
        self.children_completed_visit_count = []  # Only completed simulations
        
        # Initialize counters for each possible action
        actions = state.get_available_actions() or []
        self.children_visit_count = [0] * len(actions)
        self.children_completed_visit_count = [0] * len(actions)
        
        # Task tracking for unobserved samples (maps simulation_id -> (action, reward))
        self.traverse_history = {}  # Maps simulation_id -> (action, reward, start_time)
        
        # Track visited vs updated children (from original paper)
        self.visited_node_count = 0  # Number of children that have been visited
        self.updated_node_count = 0  # Number of children that have been updated with results
        
        # Watch the Unobservable: Track pending simulations
        # O_n in the WU-UCT paper - number of unobserved samples
        self.pending_simulations = 0
        
        # Individual lock for atomic operations
        # This allows operations without holding the global tree lock
        self._node_lock = threading.Lock()
    
    def __repr__(self):
        try:
            last_node = self.state.path[-1] if self.state.path else None
        except Exception:
            last_node = None
        avg_reward = self.total_reward / self.visits if self.visits > 0 else 0.0
        return f"<WUUCTNode node={last_node} N={self.visits} O={self.get_pending_count()} V={avg_reward:.2f} " \
               f"visited={self.visited_node_count} updated={self.updated_node_count} children={len(self.children)}>"
    
    def wu_uct_select_child(self, exploration_constant: float = math.sqrt(2)) -> 'WUUCTNode':
        """
        Select child using WU-UCT formula (Watch the Unobservable).
        
        This implements the modified UCT formula from the WU-UCT paper:
        a_n = arg max { V_c + β * sqrt(2*log(N_n + O_n) / (N_c + O_c)) }
        
        Where:
        - N_n = actual visits to parent node n
        - O_n = unobserved samples (pending simulations) for parent node n
        - N_c = actual visits to child c
        - O_c = unobserved samples (pending simulations) for child c
        - V_c = average reward of child c = total_reward / N_c
        - β = exploration constant (typically sqrt(2))
        
        The key difference from standard UCT: both numerator and denominator
        include pending simulations, which prevents workers from repeatedly
        selecting the same promising nodes.
        
        Args:
            exploration_constant: Exploration parameter β (default: sqrt(2))
        
        Returns:
            Selected child node
        """
        if not self.children:
            raise ValueError("Cannot select child from node with no children")
        
        # WU-UCT formula: parent term includes actual visits + unobserved samples
        N_parent = self.visits  # Actual visits to parent
        O_parent = self.get_pending_count()  # Unobserved samples for parent
        
        # Handle edge case: if parent has no visits yet, prefer unvisited children
        if N_parent + O_parent == 0:
            return random.choice(self.children)
        
        # Calculate log term once (numerator of exploration term)
        log_term = math.log(N_parent + O_parent)
        
        best_child = None
        best_uct_value = float('-inf')
        
        for child in self.children:
            N_child = child.visits  # Actual visits to child
            O_child = child.get_pending_count()  # Unobserved samples for child
            
            # Denominator: actual visits + unobserved samples
            denominator = N_child + O_child
            
            if denominator == 0:
                # Unvisited child - give it maximum priority
                return child
            
            # Exploitation term: V_c = average reward (only use actual visits)
            # Rewards are already normalized if enabled in the problem
            if N_child > 0:
                exploitation = child.total_reward / N_child
            else:
                exploitation = 0.0
            
            # Exploration term: β * sqrt(2*log(N_n + O_n) / (N_c + O_c))
            exploration = exploration_constant * math.sqrt(2 * log_term / denominator)
            
            # WU-UCT value
            uct_value = exploitation + exploration
            
            if uct_value > best_uct_value:
                best_uct_value = uct_value
                best_child = child
        
        return best_child
    
    def no_child_available(self) -> bool:
        """Check if all child nodes have not been expanded."""
        return self.updated_node_count == 0

    def all_child_visited(self) -> bool:
        """Check if all child nodes have been visited (not necessarily updated)."""
        available_actions = self.state.get_available_actions() or []
        return self.visited_node_count == len(available_actions)

    def all_child_updated(self) -> bool:
        """Check if all child nodes have been updated with simulation results."""
        available_actions = self.state.get_available_actions() or []
        return self.updated_node_count == len(available_actions)

    def update_history(self, simulation_id: int, action: int, reward: float) -> bool:
        """
        Update traverse history for tracking unobserved samples.
        
        Args:
            simulation_id: Unique identifier for this simulation
            action: Action taken for this simulation
            reward: Immediate reward from taking the action
            
        Returns:
            True if successfully added, False if simulation_id already exists
        """
        with self._node_lock:
            if simulation_id in self.traverse_history:
                return False
            self.traverse_history[simulation_id] = (action, reward, 0.0)  # (action, reward, start_time)
            return True

    def update_incomplete(self, simulation_id: int) -> None:
        """
        Incomplete update: Called when simulation STARTS.
        
        This is Algorithm 2 from the WU-UCT paper.
        Tracks the unobserved samples by incrementing visit counts
        but NOT updating Q-values (since simulation isn't complete).
        
        Args:
            simulation_id: Unique identifier for this simulation
        """
        if simulation_id not in self.traverse_history:
            return
            
        action = self.traverse_history[simulation_id][0]
        
        with self._node_lock:
            # Increment total visit count (including ongoing simulations)
            if action < len(self.children_visit_count):
                if self.children_visit_count[action] == 0:
                    self.visited_node_count += 1
                self.children_visit_count[action] += 1
            
            # Increment overall visit count
            self.visits += 1

    def update_complete(self, simulation_id: int, accumulated_reward: float) -> float:
        """
        Complete update: Called when simulation FINISHES.
        
        This is Algorithm 3 from the WU-UCT paper.
        Updates Q-values and completed visit counts with the actual simulation result.
        
        Args:
            simulation_id: Unique identifier for this simulation
            accumulated_reward: Total discounted reward from simulation
            
        Returns:
            Updated accumulated reward (with immediate reward added)
        """
        if simulation_id not in self.traverse_history:
            return accumulated_reward
            
        with self._node_lock:
            # Remove from history and get action/reward
            action, immediate_reward, _ = self.traverse_history.pop(simulation_id)
            
            # Add immediate reward to accumulated reward
            accumulated_reward = immediate_reward + accumulated_reward
            
            # Update completed visit count
            if action < len(self.children_completed_visit_count):
                if self.children_completed_visit_count[action] == 0:
                    self.updated_node_count += 1
                self.children_completed_visit_count[action] += 1
            
            # Update Q-values (total reward)
            self.total_reward += accumulated_reward
            
        return accumulated_reward

    def apply_virtual_loss(self):
        """
        Apply virtual loss atomically up the tree without holding tree lock.
        
        This method increments pending_simulations for this node and all ancestors.
        Uses per-node locks to avoid contention with the global tree modification lock.
        This allows multiple workers to apply virtual losses simultaneously while
        other workers are traversing the tree.
        """
        current = self
        while current is not None:
            with current._node_lock:
                current.pending_simulations += 1
            current = current.parent
    
    def remove_virtual_loss(self):
        """
        Remove virtual loss atomically up the tree without holding tree lock.
        
        This method decrements pending_simulations for this node and all ancestors.
        Called after a simulation completes and before backpropagation begins.
        Uses per-node locks for thread safety without blocking tree traversal.
        """
        current = self
        while current is not None:
            with current._node_lock:
                current.pending_simulations -= 1
            current = current.parent
    
    def get_pending_count(self) -> int:
        """
        Thread-safe read of pending simulations count.
        
        Returns:
            Current number of unobserved samples (pending simulations)
        """
        with self._node_lock:
            # Pending simulations = simulations in traverse_history (started but not completed)
            return len(self.traverse_history)

    def select_expand_action(self) -> Optional[int]:
        """
        Select an action for expansion based on WU-UCT logic.
        
        Returns:
            Action index to expand, or None if no actions available
        """
        available_actions = self.state.get_available_actions()
        if not available_actions:
            return None
            
        # Try to find an unvisited action first
        for i, action in enumerate(available_actions):
            if i < len(self.children_visit_count) and self.children_visit_count[i] == 0:
                return action
                
        # If all actions visited, select one based on some heuristic
        # For now, just select randomly among available actions
        return random.choice(available_actions)
