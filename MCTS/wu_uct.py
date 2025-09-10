import threading
import math
import random
from typing import Dict, List, Optional, Set
from .mcts_node import MCTSNode
from orienteering.orienteering import OrienteeringProblem, OrienteeringState


class WUUCTNode(MCTSNode):
    """Extended MCTSNode for WU-UCT with unobserved sample tracking."""
    
    def __init__(self, state: OrienteeringState, parent=None):
        super().__init__(state, parent)
        
        # WU-UCT specific tracking
        self.children_completed_visit_count = [0 for _ in range(len(self.state.get_available_actions() or []))]
        self.traverse_history = {}  # Maps task_idx -> (action, reward)
        self.visited_node_count = 0
        self.updated_node_count = 0
    
    def select_action_wu_uct(self, exploration_constant: float = math.sqrt(2)) -> int:
        """WU-UCT selection using both completed and ongoing visit counts."""
        if not self.children:
            return None
            
        best_score = float('-inf')
        best_actions = []
        
        for i, child in enumerate(self.children):
            if child is None:
                continue
                
            # Get the action index that led to this child
            action_idx = i  # This assumes children are ordered by action
            
            if self.children_completed_visit_count[action_idx] == 0:
                # Prioritize unvisited children
                return action_idx
            
            # WU-UCT formula: uses completed visits for exploitation, total visits for exploration
            exploitation = child.total_reward / self.children_completed_visit_count[action_idx]
            exploration = exploration_constant * math.sqrt(
                math.log(self.visits) / child.visits  # Total visits for exploration
            )
            
            score = exploitation + exploration
            
            if score > best_score:
                best_score = score
                best_actions = [action_idx]
            elif abs(score - best_score) < 1e-10:
                best_actions.append(action_idx)
        
        return random.choice(best_actions) if best_actions else 0
    
    def update_incomplete(self, task_idx: int, action: int):
        """Incomplete update for tracking unobserved samples."""
        if self.visits == 0:
            self.visited_node_count += 1
        self.visits += 1
        
        # Track this as an ongoing simulation
        if action < len(self.children_completed_visit_count):
            if self.children_completed_visit_count[action] == 0:
                self.updated_node_count += 1
    
    def update_complete(self, task_idx: int, action: int, reward: float) -> float:
        """Complete update for tracking observed samples."""
        if task_idx in self.traverse_history:
            stored_action, stored_reward = self.traverse_history.pop(task_idx)
            reward = stored_reward + reward  # Combine rewards
        
        # Update completed visit count and Q-values
        if action < len(self.children_completed_visit_count):
            self.children_completed_visit_count[action] += 1
            # Update Q-value calculation here if needed
        
        return reward


class WUUCTSolver:
    """
    Worker-UCT (WU-UCT) solver for the Orienteering Problem.
    Implements parallel MCTS with multiple workers sharing a global tree.
    """
    
    def __init__(self, problem: OrienteeringProblem, iterations: int, num_workers: int = 4, 
                 exploration_constant: float = math.sqrt(2), epsilon: float = 0.05):
        self.problem = problem
        self.iterations = iterations
        self.num_workers = num_workers
        self.exploration_constant = exploration_constant
        self.epsilon = epsilon
        
        # Shared global tree and synchronization
        self.root: Optional[WUUCTNode] = None
        self.global_tree_lock = threading.RLock()
        
        # Worker management
        self.workers: List[threading.Thread] = []
        self.worker_stats: Dict[int, Dict] = {}
        self.stop_flag = threading.Event()
        
        # Task tracking (simplified version of WU-UCT)
        self.task_counter = 0
        self.task_lock = threading.Lock()
        
        # Performance tracking
        self.total_simulations = 0
        self.simulation_lock = threading.Lock()
        
    def initialize_root(self) -> WUUCTNode:
        """Initialize the root node if not already done."""
        if self.root is None:
            root_state = OrienteeringState(self.problem)
            self.root = WUUCTNode(root_state)
        return self.root
    
    def get_task_id(self) -> int:
        """Generate unique task ID."""
        with self.task_lock:
            self.task_counter += 1
            return self.task_counter
    
    def wu_uct_selection(self, node: WUUCTNode, worker_id: int) -> tuple[WUUCTNode, List[WUUCTNode], int]:
        """
        WU-UCT selection: traverse tree until finding a node to expand.
        Returns the selected node, path taken, and task ID.
        """
        current = node
        path = [current]
        task_id = self.get_task_id()
        
        while not current.state.is_terminal():
            with self.global_tree_lock:
                # Apply incomplete update (track unobserved sample)
                if hasattr(current, 'update_incomplete'):
                    current.update_incomplete(task_id, -1)  # -1 for selection
                else:
                    current.visits += 1
                
                if not current.is_fully_expanded():
                    # Found expandable node
                    return current, path, task_id
                elif current.children:
                    # Select best child using WU-UCT formula
                    action_idx = current.select_action_wu_uct(self.exploration_constant)
                    if action_idx is not None and action_idx < len(current.children):
                        current = current.children[action_idx]
                        path.append(current)
                    else:
                        break
                else:
                    break
        
        return current, path, task_id
    
    def _select_best_child(self, node: MCTSNode, worker_id: int) -> MCTSNode:
        """Select best child using UCT formula with worker adaptations."""
        best_value = float('-inf')
        best_children = []
        
        for child in node.children:
            if child.visits == 0:
                # Prioritize unvisited children
                return child
            
            # Standard UCT formula
            exploitation = child.total_reward / child.visits
            exploration = self.exploration_constant * math.sqrt(
                math.log(node.visits) / child.visits
            )
            
            # Add small random component for tie-breaking
            epsilon_term = self.epsilon * random.random()
            
            uct_value = exploitation + exploration + epsilon_term
            
            if uct_value > best_value:
                best_value = uct_value
                best_children = [child]
            elif abs(uct_value - best_value) < 1e-10:
                best_children.append(child)
        
        return random.choice(best_children) if best_children else node.children[0]
    
    def safe_expand(self, node: MCTSNode) -> MCTSNode:
        """Thread-safe expansion of a node."""
        with self.global_tree_lock:
            # Double-check that expansion is still needed
            if node.is_fully_expanded():
                # Another worker already expanded, select child instead
                if node.children:
                    return random.choice(node.children)
                return node
            
            # Get available actions and expand
            if not node.untried_actions:
                # Initialize untried actions if needed
                available_actions = node.state.get_available_actions()
                node.untried_actions = [action.path[-1] for action in available_actions 
                                      if action.path[-1] not in [child.state.path[-1] for child in node.children]]
            
            if node.untried_actions:
                action = node.untried_actions.pop()
                new_state = node.state.apply_action(action)
                child_node = MCTSNode(new_state, parent=node)
                node.children.append(child_node)
                return child_node
            
            return node
    
    def simulate(self, state: OrienteeringState) -> float:
        """
        Simulation phase - random rollout from given state.
        This can remain similar to single-threaded version.
        """
        current = state.copy()
        steps = 0
        max_steps = 1000  # Prevent infinite loops
        
        while not current.is_terminal() and steps < max_steps:
            actions = current.get_available_actions()
            if not actions:
                break
            
            # Random action selection for simulation
            action = random.choice(actions)
            current = current.apply_action(action.path[-1])
            steps += 1
        
        return current.get_reward()
    
    def safe_backpropagate(self, path: List[MCTSNode], reward: float):
        """
        Thread-safe backpropagation up the tree.
        Removes virtual losses and adds real reward.
        """
        for node in reversed(path):
            with self.global_tree_lock:
                # Remove virtual loss (visits was incremented during selection)
                # and add real reward and visit
                node.total_reward += reward
                # visits already incremented during selection (virtual loss)
    
    def remove_virtual_losses(self, path: List[MCTSNode]):
        """Remove virtual losses if simulation fails."""
        for node in reversed(path):
            with self.global_tree_lock:
                node.visits -= 1  # Remove virtual loss
    
    def worker_iteration(self, worker_id: int):
        """Single MCTS iteration for a worker with proper virtual loss handling."""
        root = self.initialize_root()
        
        # Selection with virtual loss application
        leaf, selection_path = self.wu_uct_selection(root, worker_id)
        
        # Expansion
        expanded_node = self.safe_expand(leaf)
        if expanded_node != leaf:
            # New node was created, add to path
            selection_path.append(expanded_node)
        
        try:
            # Simulation
            reward = self.simulate(expanded_node.state)
            
            # Backpropagation (removes virtual losses and adds real reward)
            self.safe_backpropagate(selection_path, reward)
            
        except Exception as e:
            # If simulation fails, remove virtual losses
            self.remove_virtual_losses(selection_path)
            raise e
        
        # Update statistics
        with self.simulation_lock:
            self.total_simulations += 1
            if worker_id not in self.worker_stats:
                self.worker_stats[worker_id] = {'simulations': 0, 'total_reward': 0.0}
            self.worker_stats[worker_id]['simulations'] += 1
            self.worker_stats[worker_id]['total_reward'] += reward
    
    def get_best_path(self) -> OrienteeringState:
        """Extract the best path from the tree."""
        if not self.root or not self.root.children:
            return OrienteeringState(self.problem)
        
        # Find child with highest average reward
        best_child = max(
            self.root.children,
            key=lambda c: c.total_reward / c.visits if c.visits > 0 else float('-inf')
        )
        
        # Follow the path of best children to get full solution
        current = best_child
        while current.children:
            current = max(
                current.children,
                key=lambda c: c.total_reward / c.visits if c.visits > 0 else float('-inf')
            )
        
        return current.state