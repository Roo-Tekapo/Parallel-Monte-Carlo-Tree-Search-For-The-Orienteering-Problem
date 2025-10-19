"""
Virtual Loss Node Implementation

This node class implements the standard Virtual Loss mechanism for parallel MCTS.
Unlike WU-UCT which tracks pending simulations, VL directly modifies node values
with temporary penalties.

Key Features:
- Thread-safe virtual loss application and removal
- Fixed penalty value (not a counter)
- Standard UCT selection (no formula modification)
- Per-thread virtual loss tracking
"""

import math
import random
import threading
from typing import Optional, Dict

from VL.orienteering_adapter import OrienteeringState
from UCT.uct_single_thread import UCTNode


class VLNode(UCTNode):
    """
    Node class for Virtual Loss parallel MCTS.
    
    The Virtual Loss approach applies a fixed penalty to nodes that are
    currently being explored by threads. This temporarily reduces their
    attractiveness to other threads without modifying the UCT formula.
    
    Key Differences from WU-UCT:
    - Uses fixed virtual loss value (not a counter)
    - Tracks which threads have applied virtual loss
    - Uses standard UCT formula (no modification needed)
    - Virtual loss directly affects total_reward temporarily
    """
    
    def __init__(self, state: OrienteeringState, parent: Optional['VLNode'] = None):
        super().__init__(state, parent)
        
        # Virtual Loss tracking
        # Maps thread_id -> virtual_loss_value applied by that thread
        self._virtual_losses: Dict[str, float] = {}
        
        # Lock for thread-safe virtual loss operations
        self._vl_lock = threading.Lock()
        
        # Total virtual loss currently applied (cached for performance)
        self._total_virtual_loss = 0.0
    
    def __repr__(self):
        try:
            last_node = self.state.path[-1] if self.state.path else None
        except Exception:
            last_node = None
        
        # Calculate effective reward (with virtual loss)
        effective_reward = self.total_reward - self._total_virtual_loss
        avg_reward = effective_reward / self.visits if self.visits > 0 else 0.0
        vl_count = len(self._virtual_losses)
        
        return (f"<VLNode node={last_node} N={self.visits} "
                f"VL={vl_count}×{self._total_virtual_loss:.2f} "
                f"V={avg_reward:.2f} children={len(self.children)}>")
    
    def apply_virtual_loss(self, thread_id: str, loss_value: float):
        """
        Apply virtual loss for a specific thread.
        
        Virtual loss is a temporary penalty that makes the node less attractive
        to other threads. Each thread can apply one virtual loss to a node.
        
        Args:
            thread_id: Unique identifier for the thread applying the loss
            loss_value: The virtual loss value (typically positive, representing a penalty)
        """
        with self._vl_lock:
            if thread_id not in self._virtual_losses:
                self._virtual_losses[thread_id] = loss_value
                self._total_virtual_loss += loss_value
    
    def remove_virtual_loss(self, thread_id: str) -> bool:
        """
        Remove virtual loss for a specific thread.
        
        Args:
            thread_id: Unique identifier for the thread removing the loss
            
        Returns:
            True if virtual loss was removed, False if thread had no virtual loss
        """
        with self._vl_lock:
            if thread_id in self._virtual_losses:
                loss_value = self._virtual_losses.pop(thread_id)
                self._total_virtual_loss -= loss_value
                return True
            return False
    
    def get_effective_reward(self) -> float:
        """
        Get the effective total reward including virtual loss penalties.
        
        Returns:
            Total reward minus all virtual losses currently applied
        """
        with self._vl_lock:
            return self.total_reward - self._total_virtual_loss
    
    def get_virtual_loss_count(self) -> int:
        """
        Get the number of threads that have applied virtual loss to this node.
        
        Returns:
            Number of active virtual losses
        """
        with self._vl_lock:
            return len(self._virtual_losses)
    
    def uct_select_child(self, exploration_constant: float = math.sqrt(2)) -> 'VLNode':
        """
        Select child using standard UCT formula with virtual loss.
        
        Uses the standard UCT formula:
        UCT = (Q/N) + c * sqrt(ln(N_parent) / N_child)
        
        Where Q is the EFFECTIVE reward (total_reward - virtual_loss).
        This is the key difference: virtual loss directly reduces Q,
        making the node less attractive without changing the formula.
        
        Args:
            exploration_constant: UCT exploration constant (default: √2)
            
        Returns:
            Selected child node
        """
        if not self.children:
            raise ValueError("Cannot select child from node with no children")
        
        # Handle unvisited children
        unvisited = [child for child in self.children if child.visits == 0]
        if unvisited:
            return random.choice(unvisited)
        
        # Standard UCT with virtual loss affecting exploitation term
        log_parent = math.log(self.visits)
        
        best_child = None
        best_uct_value = float('-inf')
        
        for child in self.children:
            # Exploitation: Use effective reward (includes virtual loss penalty)
            effective_reward = child.get_effective_reward()
            exploitation = effective_reward / child.visits
            
            # Exploration: Standard UCT exploration term
            exploration = exploration_constant * math.sqrt(log_parent / child.visits)
            
            uct_value = exploitation + exploration
            
            if uct_value > best_uct_value:
                best_uct_value = uct_value
                best_child = child
        
        return best_child
    
    def update(self, reward: float):
        """
        Update node with a simulation result.
        
        This is the standard update that affects the real statistics.
        Virtual loss is separate and temporary.
        
        Args:
            reward: The reward value to add
        """
        with self._vl_lock:
            self.visits += 1
            self.total_reward += reward
