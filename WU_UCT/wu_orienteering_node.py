"""
WU-UCT Node implementation for Orienteering Problem
"""
import math
import random
from typing import List, Optional, Dict, Set
from copy import deepcopy
import sys
import os

# Add the parent directory to path to import orienteering module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from orienteering.orienteering import OrienteeringState, OrienteeringProblem


class WUOrienteeringNode:
    """Node for WU-UCT algorithm adapted for Orienteering Problem"""
    
    def __init__(self, state: OrienteeringState, parent: Optional['WUOrienteeringNode'] = None, 
                 action: Optional[int] = None, checkpoint_idx: int = 0, tree=None):
        self.state = state
        self.parent = parent
        self.action = action  # The action (node_id) that led to this state
        self.checkpoint_idx = checkpoint_idx
        self.tree = tree
        
        # MCTS statistics
        self.visit_count = 0
        self.total_reward = 0.0
        self.children: Dict[int, 'WUOrienteeringNode'] = {}
        
        # WU-UCT specific - track children statistics
        self.children_visit_count: Dict[int, int] = {}
        self.children_completed_visit_count: Dict[int, int] = {}
        self.Q_values: Dict[int, float] = {}
        self.rewards: Dict[int, float] = {}
        self.dones: Dict[int, bool] = {}
        
        # For tracking available actions
        self.available_actions = self.state.get_available_actions()
        self._initialize_action_tracking()
        
        # Record traverse history for WU-UCT updates
        self.traverse_history = dict()
        
        # Visited and updated node counts
        self.visited_node_count = 0
        self.updated_node_count = 0
        
        if tree is not None:
            self.max_width = getattr(tree, 'max_width', 10)
        else:
            self.max_width = 10
    
    def _initialize_action_tracking(self):
        """Initialize tracking dictionaries for available actions"""
        for action in self.available_actions:
            self.children_visit_count[action] = 0
            self.children_completed_visit_count[action] = 0
            self.Q_values[action] = 0.0
            self.rewards[action] = 0.0
            self.dones[action] = False
    
    def is_terminal_node(self) -> bool:
        """Check if this is a terminal node"""
        return self.state.is_terminal()
    
    def is_fully_expanded(self) -> bool:
        """Check if all possible actions have been tried"""
        return len(self.children) >= len(self.available_actions)
    
    def no_child_available(self):
        """All child nodes have not been expanded."""
        return self.updated_node_count == 0

    def all_child_visited(self):
        """All child nodes have been visited (not necessarily updated)."""
        if not self.available_actions:
            return True
        return self.visited_node_count >= min(len(self.available_actions), self.max_width)

    def all_child_updated(self):
        """All child nodes have been updated."""
        if not self.available_actions:
            return True
        return self.updated_node_count >= min(len(self.available_actions), self.max_width)
    
    def get_untried_action(self) -> Optional[int]:
        """Get an action that hasn't been expanded yet"""
        for action in self.available_actions:
            if action not in self.children:
                return action
        return None
    
    def add_child(self, action: int, child_state: OrienteeringState) -> 'WUOrienteeringNode':
        """Add a child node for the given action"""
        child_node = WUOrienteeringNode(child_state, parent=self, action=action, tree=self.tree)
        self.children[action] = child_node
        return child_node
    
    def select_action(self):
        """Select action according to the UCT tree policy"""
        best_score = -float('inf')
        best_action = None
        
        if not self.available_actions:
            return None

        for action in self.available_actions:
            if self.children_visit_count[action] == 0:
                # Unvisited action gets priority
                return action
                
                        # UCT formula with standard exploration constant
            if self.children_completed_visit_count[action] > 0:
                exploitation = self.Q_values[action] / self.children_completed_visit_count[action]
                # Standard UCB1 exploration constant sqrt(2)
                exploration = math.sqrt(2 * math.log(self.visit_count) / self.children_visit_count[action])
                score = exploitation + exploration
            else:
                score = float('inf')  # Prioritize unvisited nodes

            if score > best_score:
                best_score = score
                best_action = action

        return best_action

    def max_utility_action(self):
        """Return the action with maximum utility."""
        best_score = -float('inf')
        best_action = None
        
        if not self.available_actions:
            return None

        for action in self.available_actions:
            if action not in self.children or self.children[action] is None:
                continue

            if self.children_completed_visit_count[action] == 0:
                continue
                
            score = self.Q_values[action] / self.children_completed_visit_count[action]

            if score > best_score:
                best_score = score
                best_action = action

        return best_action

    def select_expand_action(self):
        """Choose an action to expand"""
        if not self.available_actions:
            return None
            
        # Only return unvisited actions (actions not in children)
        unvisited = [a for a in self.available_actions if a not in self.children]
        if unvisited:
            return random.choice(unvisited)
            
        # If all actions have been expanded, return None
        return None
    
    def update_history(self, idx, action_taken, reward):
        """Update traverse history, used to perform update"""
        if idx in self.traverse_history:
            return False
        else:
            self.traverse_history[idx] = (action_taken, reward)
            return True

    def update_incomplete(self, idx):
        """Incomplete update, called by WU_UCT.py"""
        if idx not in self.traverse_history:
            return
            
        action_taken = self.traverse_history[idx][0]

        if self.children_visit_count[action_taken] == 0:
            self.visited_node_count += 1

        self.children_visit_count[action_taken] += 1
        self.visit_count += 1

    def update_complete(self, idx, accu_reward):
        """Complete update, called by WU_UCT.py"""
        if idx not in self.traverse_history:
            raise RuntimeError("idx {} should be in traverse_history".format(idx))
        
        item = self.traverse_history.pop(idx)
        action_taken = item[0]
        reward = item[1]

        if self.children_completed_visit_count[action_taken] == 0:
            self.updated_node_count += 1

        self.Q_values[action_taken] += accu_reward
        self.children_completed_visit_count[action_taken] += 1
        self.rewards[action_taken] = reward

    def shallow_clone(self):
        """Shallowly clone itself, contains necessary data only."""
        node = WUOrienteeringNode(
            state=deepcopy(self.state),
            checkpoint_idx=self.checkpoint_idx,
            parent=None,
            tree=None
        )

        # Copy children information
        for action in self.children:
            if self.children[action] is not None:
                node.children[action] = 1  # Placeholder to indicate child exists

        node.children_visit_count = deepcopy(self.children_visit_count)
        node.children_completed_visit_count = deepcopy(self.children_completed_visit_count)
        node.Q_values = deepcopy(self.Q_values)
        node.rewards = deepcopy(self.rewards)
        node.dones = deepcopy(self.dones)

        node.visited_node_count = self.visited_node_count
        node.updated_node_count = self.updated_node_count
        node.max_width = self.max_width
        node.available_actions = self.available_actions[:]

        return node
    
    def get_average_reward(self) -> float:
        """Get average reward for this node"""
        return self.total_reward / self.visit_count if self.visit_count > 0 else 0.0
    
    def get_path(self) -> List[int]:
        """Get path from root to this node"""
        return self.state.get_path()
    
    def __str__(self):
        avg_reward = self.get_average_reward()
        return f"WUOrienteeringNode(path={self.get_path()}, visits={self.visit_count}, avg_reward={avg_reward:.3f})"