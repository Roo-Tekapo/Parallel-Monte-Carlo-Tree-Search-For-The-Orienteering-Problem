"""
Unified Worker for Simple WU-UCT Implementation

This worker combines both expansion and simulation responsibilities,
eliminating the need for separate worker types and work unit coordination.
Each worker performs complete MCTS iterations on the shared tree.
"""

import threading
import math
import time
import random
from typing import Optional

from Simple_WU.orienteering_adapter import OrienteeringProblem, OrienteeringState, END_NODE
from .wu_uct_node import WUUCTNode


class SimpleWUWorker(threading.Thread):
    """
    Unified worker that handles both tree expansion and simulation.
    
    This worker performs complete MCTS iterations:
    1. Selection: Traverse tree using UCT until leaf node
    2. Expansion: Add new child if possible  
    3. Simulation: Perform random rollout from new/leaf node
    4. Backpropagation: Update all nodes in path with result
    
    Multiple workers share the same tree with proper synchronization.
    """
    
    def __init__(self, 
                 problem: OrienteeringProblem,
                 root: WUUCTNode,
                 worker_id: int,
                 iterations_per_worker: int,
                 exploration_constant: float = math.sqrt(2),
                 max_distance: Optional[float] = None):
        """
        Initialize the unified worker.
        
        Args:
            problem: The orienteering problem instance
            root: Shared root node of the search tree
            worker_id: Unique identifier for this worker
            iterations_per_worker: Number of MCTS iterations this worker should perform
            exploration_constant: UCT exploration parameter (default: √2)
            max_distance: Maximum distance constraint for simulations
        """
        super().__init__()
        self.problem = problem
        self.root = root
        self.worker_id = worker_id
        self.iterations_per_worker = iterations_per_worker
        self.exploration_constant = exploration_constant
        self.max_distance = max_distance
        
        # Worker statistics
        self.iterations_completed = 0
        self.simulations_completed = 0
        self.total_simulation_time = 0.0
        
        # Threading
        self.daemon = True
        
        # Track action -> child mapping for easier access
        self.action_to_child_cache = {}
        
        # For visualization: track the current selection path
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
        Perform one complete MCTS iteration with WU-UCT virtual loss.
        
        This includes selection, expansion, simulation, and backpropagation
        with proper virtual loss tracking for coordination between workers.
        """
        # Phase 1: Selection - find leaf node using WU-UCT
        path, leaf_node, leaf_state = self._select_leaf()
        
        # Store the selection path for visualization
        if leaf_state and hasattr(leaf_state, 'path'):
            self.last_selection_path = leaf_state.path[:]
        else:
            self.last_selection_path = []
        
        # Phase 2: Apply virtual loss to selected path (for coordination)
        simulation_id = self._apply_virtual_loss(path)
        
        # Phase 3: Expansion - create new child if possible
        expanded_node, expanded_state = self._expand_leaf(leaf_node, leaf_state)
        
        # Phase 4: Simulation - perform random rollout
        reward = self._simulate(expanded_state)
        self.simulations_completed += 1
        
        # Phase 5: Backpropagation - update all nodes in path and remove virtual loss
        final_path = path + [expanded_node] if expanded_node != leaf_node else path
        self._backpropagate_and_remove_virtual_loss(final_path, reward, simulation_id)
        
    def _select_leaf(self):
        """
        Select a leaf node using UCT policy.
        
        Returns:
            Tuple of (path, leaf_node, leaf_state) where path includes leaf_node
        """
        current_node = self.root
        current_state = OrienteeringState(self.problem)
        path = []
        
        while True:
            # Thread-safe access to node properties  
            with current_node._node_lock:
                if not current_node.is_fully_expanded():
                    # Found a leaf node (not fully expanded)
                    path.append(current_node)
                    return path, current_node, current_state
                
                if not current_node.children:
                    # Terminal node with no children
                    path.append(current_node)
                    return path, current_node, current_state
                
                # Select best child using UCT - work with list structure
                best_child = self._select_best_child(current_node)
                
            # Move to selected child
            path.append(current_node)
            # Get the action that leads to this child
            child_action = best_child.state.path[-1]
            current_state = self._create_next_state(current_state, child_action)
            current_node = best_child
            
    def _select_best_child(self, node: WUUCTNode):
        """
        Select the best child using WU-UCT formula (Watch the Unobservable).
        
        This implements the WU-UCT formula from the paper:
        a_n = arg max { V_c + β * sqrt(2*log(N_n + O_n) / (N_c + O_c)) }
        
        Where:
        - N_n = actual visits to parent node n
        - O_n = unobserved samples (pending simulations) for parent node n  
        - N_c = actual visits to child c
        - O_c = unobserved samples (pending simulations) for child c
        - V_c = average reward of child c = total_reward / N_c
        
        Args:
            node: Current node (must be called with node._node_lock held)
            
        Returns:
            Best child node to move to
        """
        if not node.children:
            return None
            
        # Get parent counts: actual visits + unobserved samples
        N_parent = node.visits  # Actual visits to parent
        O_parent = node.pending_simulations  # Unobserved samples for parent
        
        # Handle edge case: if parent has no visits yet, prefer unvisited children
        if N_parent + O_parent == 0:
            return random.choice(node.children)
        
        # Calculate log term once (numerator of exploration term)
        log_term = math.log(N_parent + O_parent)
        
        best_child = None
        best_value = float('-inf')
        
        for child in node.children:
            N_child = child.visits  # Actual visits to child
            O_child = child.pending_simulations  # Unobserved samples for child
            
            # Denominator: actual visits + unobserved samples
            denominator = N_child + O_child
            
            if denominator == 0:
                # Unvisited child - give it maximum priority
                return child
            
            # Exploitation term: V_c = average reward (only use actual visits)
            # Rewards are already normalized in the problem if enabled
            if N_child > 0:
                exploitation = child.total_reward / N_child
            else:
                exploitation = 0.0
            
            # Exploration term: β * sqrt(2*log(N_n + O_n) / (N_c + O_c))
            exploration = self.exploration_constant * math.sqrt(2 * log_term / denominator)
            
            # WU-UCT value
            wu_uct_value = exploitation + exploration
            
            if wu_uct_value > best_value:
                best_value = wu_uct_value
                best_child = child
                
        return best_child
        
    def _expand_leaf(self, leaf_node: WUUCTNode, leaf_state: OrienteeringState):
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
        with leaf_node._node_lock:
            # Check if we can expand by using untried actions
            if not leaf_node.untried_actions:
                # No expansion possible
                return leaf_node, leaf_state
                
            # Select a random unexplored action for expansion
            action_to_expand = leaf_node.untried_actions.pop()
            
            # Create new child node
            new_state = self._create_next_state(leaf_state, action_to_expand)
            new_child = WUUCTNode(new_state, parent=leaf_node)
            
            # Add child to parent
            leaf_node.children.append(new_child)
            
            return new_child, new_state
            
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
        
        while not simulation_state.is_terminal():
            available_actions = simulation_state.get_available_actions()
            
            if not available_actions:
                break
                
            # Random action selection
            action = random.choice(available_actions)
            simulation_state = self._create_next_state(simulation_state, action)
            
        # Calculate final reward with completion bonus/penalty
        reward = simulation_state.reward_so_far
        
        if simulation_state.is_terminal():
            # Completion bonus for finishing the path
            if self.problem.normalize_rewards:
                # Meaningful bonus - 15% of typical collected reward
                # With avg node ~0.5, this is ~30% of a typical node value
                reward += 0.15
            else:
                reward += 100  # Larger bonus for unnormalized rewards
        else:
            # Penalty for incomplete paths (only if path is non-trivial)
            if len(simulation_state.path) > 2:
                if self.problem.normalize_rewards:
                    # Moderate penalty - allows good incomplete exploration
                    # Still penalizes but not so harsh it discourages risk-taking
                    reward *= 0.7  # 30% penalty (was 70%)
                else:
                    reward *= 0.1  # 90% penalty
        
        # Update timing statistics
        self.total_simulation_time += time.time() - start_time
        
        return reward
        
    def _create_next_state(self, current_state: OrienteeringState, action: int) -> OrienteeringState:
        """
        Create the next state by taking the given action.
        
        Args:
            current_state: Current orienteering state
            action: Node ID to move to
            
        Returns:
            New orienteering state after taking the action
        """
        # Calculate cost to move to the action node
        current_node = current_state.path[-1]
        cost_to_action = self.problem.get_distance(current_node, action)
        
        # Create new state (use normalized score if enabled in problem)
        new_path = current_state.path + [action]
        new_cost = current_state.cost_so_far + cost_to_action
        new_reward = current_state.reward_so_far + self.problem.get_normalized_score(action)
        
        return OrienteeringState(
            self.problem, 
            path=new_path, 
            cost_so_far=new_cost, 
            reward_so_far=new_reward
        )

    def get_statistics(self):
        """
        Get worker performance statistics.
        
        Returns:
            Dictionary with worker statistics
        """
        avg_simulation_time = (self.total_simulation_time / self.simulations_completed 
                              if self.simulations_completed > 0 else 0)
        
        return {
            'worker_id': self.worker_id,
            'iterations_completed': self.iterations_completed,
            'simulations_completed': self.simulations_completed,
            'total_simulation_time': self.total_simulation_time,
            'avg_simulation_time': avg_simulation_time
        }
        
    def _apply_virtual_loss(self, path):
        """
        Apply virtual loss to the selected path for WU-UCT coordination.
        
        Virtual loss temporarily increments pending simulation counts
        to prevent other workers from selecting the same path.
        
        Args:
            path: List of nodes in the selected path
            
        Returns:
            Unique simulation ID for tracking this virtual loss
        """
        simulation_id = f"{self.worker_id}_{time.time()}_{random.randint(1000, 9999)}"
        
        for node in path:
            with node._node_lock:
                # Increment pending simulation count (virtual loss)
                node.pending_simulations += 1
        
        return simulation_id
        
    def _backpropagate_and_remove_virtual_loss(self, path, reward: float, simulation_id: str):
        """
        Update all nodes in the path with the simulation result and remove virtual loss.
        
        Args:
            path: List of nodes from root to leaf
            reward: Reward to backpropagate
            simulation_id: ID of the simulation to remove from virtual loss tracking
        """
        for node in path:
            with node._node_lock:
                # Update actual statistics
                node.visits += 1
                node.total_reward += reward
                
                # Remove virtual loss (decrement pending simulations)
                if node.pending_simulations > 0:
                    node.pending_simulations -= 1