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

from orienteering.orienteering import OrienteeringState
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
        
        # Watch the Unobservable: Track pending simulations
        # O_n in the WU-UCT paper - number of unobserved samples
        self.pending_simulations = 0
        
        # Individual lock for atomic pending_simulations updates
        # This allows virtual loss operations without holding the global tree lock
        self._pending_lock = threading.Lock()
    
    def __repr__(self):
        try:
            last_node = self.state.path[-1] if self.state.path else None
        except Exception:
            last_node = None
        avg_reward = self.total_reward / self.visits if self.visits > 0 else 0.0
        return f"<WUUCTNode node={last_node} N={self.visits} O={self.pending_simulations} V={avg_reward:.2f} children={len(self.children)}>"
    
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
        O_parent = self.pending_simulations  # Unobserved samples for parent
        
        # Handle edge case: if parent has no visits yet, prefer unvisited children
        if N_parent + O_parent == 0:
            return random.choice(self.children)
        
        # Calculate log term once (numerator of exploration term)
        log_term = math.log(N_parent + O_parent)
        
        best_child = None
        best_uct_value = float('-inf')
        
        for child in self.children:
            N_child = child.visits  # Actual visits to child
            O_child = child.pending_simulations  # Unobserved samples for child
            
            # Denominator: actual visits + unobserved samples
            denominator = N_child + O_child
            
            if denominator == 0:
                # Unvisited child - give it maximum priority
                return child
            
            # Exploitation term: V_c = average reward (only use actual visits)
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
            with current._pending_lock:
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
            with current._pending_lock:
                current.pending_simulations -= 1
            current = current.parent
    
    def get_pending_count(self) -> int:
        """
        Thread-safe read of pending simulations count.
        
        Returns:
            Current number of unobserved samples (pending simulations)
        """
        with self._pending_lock:
            return self.pending_simulations
