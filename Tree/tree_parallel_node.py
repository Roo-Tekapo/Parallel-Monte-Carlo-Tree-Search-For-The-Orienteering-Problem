"""
Tree Parallel MCTS Node

Node class for tree-parallel MCTS with standard UCT formula.
Uses thread-safe operations but does NOT implement WU-UCT virtual loss.
"""

import random
import math
import threading
from typing import Optional

from Tree.orienteering_adapter import OrienteeringState
from UCT.uct_single_thread import UCTNode


class TreeParallelNode(UCTNode):
    """
    Node class for tree-parallel MCTS with standard UCT.
    
    Extends UCTNode with thread-safety for parallel execution.
    Multiple workers share the same tree and use standard UCT formula
    for selection. Thread safety is ensured via locks, but no virtual
    loss mechanism is used (unlike WU-UCT).
    """
    
    def __init__(self, state: OrienteeringState, parent: Optional['TreeParallelNode'] = None):
        """
        Initialize a tree parallel node.
        
        Args:
            state: The orienteering state at this node
            parent: Parent node in the tree (None for root)
        """
        # Call parent constructor
        super().__init__(state, parent)
        
        # Thread safety - lock for this node's statistics
        self._node_lock = threading.Lock()
    
    def __repr__(self):
        try:
            last_node = self.state.path[-1] if self.state.path else None
        except Exception:
            last_node = None
        with self._node_lock:
            avg_reward = self.total_reward / self.visits if self.visits > 0 else 0.0
            visits = self.visits
            num_children = len(self.children)
        return f"<TreeParallelNode node={last_node} visits={visits} avg_reward={avg_reward:.2f} children={num_children}>"
    
    def is_fully_expanded(self) -> bool:
        """Check if all actions have been tried (thread-safe override)."""
        with self._node_lock:
            return len(self.untried_actions) == 0
    
    def uct_select_child(self, exploration_constant: float = math.sqrt(2)) -> 'TreeParallelNode':
        """
        Select best child using standard UCT formula.
        
        Standard UCT formula:
        UCT = V_i + c * sqrt(ln(N_parent) / N_i)
        
        Where:
        - V_i = average reward of child i = Q_i / N_i
        - N_parent = visit count of parent
        - N_i = visit count of child i
        - c = exploration constant (typically sqrt(2))
        
        Args:
            exploration_constant: Exploration parameter c (default: sqrt(2))
        
        Returns:
            Selected child node
        """
        with self._node_lock:
            if not self.children:
                raise ValueError("Cannot select child from node with no children")
            children = list(self.children)
            parent_visits = self.visits
        
        # If parent hasn't been visited yet, select randomly
        if parent_visits == 0:
            return random.choice(children)
        
        # Check for unvisited children across all children and choose randomly among them
        unvisited = []
        child_stats = []
        for child in children:
            with child._node_lock:
                c_visits = child.visits
                c_reward = child.total_reward
            if c_visits == 0:
                unvisited.append(child)
            else:
                child_stats.append((child, c_visits, c_reward))
        
        if unvisited:
            return random.choice(unvisited)
        
        log_parent = math.log(parent_visits)
        best_child = None
        best_value = float('-inf')
        
        for child, child_visits, child_reward in child_stats:
            # Standard UCT formula
            exploitation = child_reward / child_visits
            exploration = exploration_constant * math.sqrt(log_parent / child_visits)
            uct_value = exploitation + exploration
            
            if uct_value > best_value:
                best_value = uct_value
                best_child = child
        
        return best_child
    
    def add_child(self, child_node: 'TreeParallelNode'):
        """
        Add a child node to this node.
        
        Args:
            child_node: The child node to add
        """
        with self._node_lock:
            child_node.parent = self
            self.children.append(child_node)
    
    def update(self, reward: float):
        """
        Update this node's statistics with a simulation result.
        
        Args:
            reward: The reward to add
        """
        with self._node_lock:
            self.visits += 1
            self.total_reward += reward
    
    def get_best_child_by_visits(self) -> Optional['TreeParallelNode']:
        """
        Get the child with the most visits.
        
        Returns:
            Child with highest visit count, or None if no children
        """
        if not self.children:
            return None
        
        best_child = None
        best_visits = -1
        
        for child in self.children:
            with child._node_lock:
                child_visits = child.visits
            
            if child_visits > best_visits:
                best_visits = child_visits
                best_child = child
        
        return best_child
    
    def get_statistics(self):
        """
        Get thread-safe statistics for this node.
        
        Returns:
            Dictionary with node statistics
        """
        with self._node_lock:
            return {
                'visits': self.visits,
                'total_reward': self.total_reward,
                'avg_reward': self.total_reward / self.visits if self.visits > 0 else 0.0,
                'num_children': len(self.children),
                'num_untried_actions': len(self.untried_actions)
            }
