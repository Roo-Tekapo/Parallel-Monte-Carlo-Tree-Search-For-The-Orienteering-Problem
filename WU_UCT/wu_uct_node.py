"""
WU-UCT Node Implementation

True WU-UCT node following Chen et al. (2018) with:
- Minimal locking (only for atomic writes)
- Local buffering through traverse_history
- Separate tracking of completed vs unobserved samples
"""

import threading
import math
import random
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass
import time

from UCT.uct_single_thread import UCTNode


@dataclass
class LocalStatistics:
    """Local view of node statistics for lock-free reading."""
    visits: int
    total_reward: float
    unobserved_count: int  # Number of pending simulations
    
    @property
    def effective_visits(self) -> int:
        """Total visits including unobserved samples (N + O)."""
        return self.visits + self.unobserved_count
    
    @property
    def average_reward(self) -> float:
        """Average reward from completed simulations."""
        return self.total_reward / self.visits if self.visits > 0 else 0.0


class WUUCTNode(UCTNode):
    """
    WU-UCT Node with lock-free selection and asynchronous updates.
    
    Following Algorithm 1, 2, 3 from Chen et al. (2018):
    - Algorithm 1: WU-UCT Selection (lock-free with predictions)
    - Algorithm 2: Update-Incomplete (marks simulation as started)
    - Algorithm 3: Update-Complete (commits final results)
    
    Key insight: Workers read statistics without locks, use predictions to
    account for unobserved samples, and only lock briefly during commits.
    """
    
    def __init__(self, state, parent: Optional['WUUCTNode'] = None):
        """
        Initialize WU-UCT node.
        
        Args:
            state: The game/problem state at this node
            parent: Parent node (None for root)
        """
        # Call parent constructor to initialize base UCT node
        super().__init__(state, parent)
        
        # WU-UCT Core: Traverse History for tracking unobserved samples
        # Maps simulation_id -> (action, immediate_reward, start_time)
        self.traverse_history: Dict[str, Tuple[int, float, float]] = {}
        self._history_lock = threading.Lock()  # Only for history modifications
        
        # Minimal atomic write lock (only held during result commits)
        self._write_lock = threading.Lock()
        
        # For expansion coordination
        self._expansion_lock = threading.Lock()
        
        # Note: The parent UCTNode already initializes:
        # - self.state
        # - self.parent
        # - self.children (as a List)
        # - self.visits = 0
        # - self.total_reward = 0.0
        # - self.untried_actions (with shuffled actions)
        
    def get_local_statistics(self) -> LocalStatistics:
        """
        Get local view of node statistics WITHOUT locking.
        
        This is the key to WU-UCT's lock-free selection:
        Workers read statistics optimistically without blocking.
        
        Returns:
            LocalStatistics with current visits, reward, and unobserved count
        """
        # Quick, non-locked reads (may be slightly stale, but that's OK!)
        current_visits = self.visits
        current_reward = self.total_reward
        
        # Count unobserved samples from traverse history
        with self._history_lock:
            unobserved = len(self.traverse_history)
        
        return LocalStatistics(
            visits=current_visits,
            total_reward=current_reward,
            unobserved_count=unobserved
        )
    
    def wu_uct_select_child(self, exploration_constant: float = math.sqrt(2)) -> Optional['WUUCTNode']:
        """
        WU-UCT child selection (Algorithm 1 from paper).
        
        Key difference from standard UCT: Uses predicted visit counts that
        include unobserved samples (N + O) in both numerator and denominator.
        
        This is LOCK-FREE during selection - only reads statistics.
        
        Args:
            exploration_constant: UCT exploration parameter (β)
            
        Returns:
            Selected child node, or None if no children
        """
        if not self.children:
            return None
        
        # Get local statistics for parent (lock-free read)
        parent_stats = self.get_local_statistics()
        
        if parent_stats.effective_visits == 0:
            # Parent has no visits yet - select random child
            return random.choice(self.children)
        
        # Calculate log term once (numerator of exploration)
        log_term = math.log(parent_stats.effective_visits)
        
        best_child = None
        best_value = float('-inf')
        
        for child in self.children:
            # Get child statistics (lock-free read)
            child_stats = child.get_local_statistics()
            
            if child_stats.effective_visits == 0:
                # Unvisited child - give it highest priority
                return child
            
            # WU-UCT Formula:
            # UCT(c) = Q(c)/N(c) + β * sqrt(log(N_parent + O_parent) / (N_child + O_child))
            
            # Exploitation: Use only completed visits for Q-value
            exploitation = child_stats.average_reward
            
            # Exploration: Use effective visits (N + O) for both parent and child
            exploration = exploration_constant * math.sqrt(
                2 * log_term / child_stats.effective_visits
            )
            
            uct_value = exploitation + exploration
            
            if uct_value > best_value:
                best_value = uct_value
                best_child = child
        
        return best_child
    
    def mark_simulation_started(self, simulation_id: str, action: Optional[int] = None, 
                               immediate_reward: float = 0.0):
        """
        Algorithm 2: Update-Incomplete from WU-UCT paper.
        
        Called when a simulation STARTS to mark it as "unobserved".
        This allows other workers to account for it during selection.
        
        Args:
            simulation_id: Unique identifier for this simulation
            action: Action taken (child index), None if simulating from this node
            immediate_reward: Immediate reward from the action
        """
        with self._history_lock:
            self.traverse_history[simulation_id] = (action, immediate_reward, time.time())
    
    def commit_simulation_result(self, simulation_id: str, accumulated_reward: float) -> float:
        """
        Algorithm 3: Update-Complete from WU-UCT paper.
        
        Called when simulation COMPLETES to commit the final result.
        This is the only place where we update visits and total_reward.
        
        Uses brief atomic write lock to ensure consistency.
        
        Args:
            simulation_id: Unique identifier for this simulation
            accumulated_reward: Total discounted reward from simulation
            
        Returns:
            Updated accumulated reward (with immediate reward added)
        """
        # Remove from history first
        with self._history_lock:
            if simulation_id not in self.traverse_history:
                return accumulated_reward
            
            action, immediate_reward, start_time = self.traverse_history.pop(simulation_id)
        
        # Calculate total reward
        total_reward = immediate_reward + accumulated_reward
        
        # Brief atomic update of node statistics
        with self._write_lock:
            self.visits += 1
            self.total_reward += total_reward
        
        return total_reward
    
    def get_untried_action(self) -> Optional[int]:
        """
        Get an untried action for expansion (thread-safe).
        
        Returns:
            Action to try, or None if all actions tried
        """
        with self._expansion_lock:
            if not self.untried_actions:
                return None
            
            # Pop random action (parent already shuffled the list)
            return self.untried_actions.pop()
    
    def add_child(self, child_state, action: int) -> 'WUUCTNode':
        """
        Add a child node (thread-safe).
        
        Args:
            child_state: State for the new child
            action: Action that leads to this child
            
        Returns:
            The newly created child node
        """
        with self._expansion_lock:
            child = WUUCTNode(child_state, parent=self)
            self.children.append(child)
            return child
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        stats = self.get_local_statistics()
        try:
            last_action = self.state.path[-1] if hasattr(self.state, 'path') and self.state.path else None
        except:
            last_action = None
        
        return (f"<WUUCTNode action={last_action} "
                f"N={stats.visits} O={stats.unobserved_count} "
                f"Q={stats.average_reward:.3f} children={len(self.children)}>")
