import threading
import math
import random
import time
from typing import Dict, List, Optional, Set
from .mcts_node import MCTSNode
from orienteering.orienteering import OrienteeringProblem, OrienteeringState


class WUUCTNode(MCTSNode):
    """Extended MCTSNode for WU-UCT with unobserved sample tracking."""
    
    def __init__(self, state: OrienteeringState, parent=None):
        super().__init__(state, parent)
        
        # WU-UCT specific tracking - start with empty lists, expand as needed
        self.children_completed_visit_count = []
        self.traverse_history = {}  # Maps task_idx -> (action, reward)
        self.visited_node_count = 0
        self.updated_node_count = 0
        self.ongoing_tasks = set()  # Track which tasks have incomplete updates on this node
    
    def _ensure_tracking_lists_size(self, min_size: int):
        """Ensure tracking lists are at least min_size."""
        while len(self.children_completed_visit_count) < min_size:
            self.children_completed_visit_count.append(0)
    
    def select_action_wu_uct(self, exploration_constant: float = math.sqrt(2)) -> int:
        """WU-UCT selection using both completed and ongoing visit counts."""
        if not self.children:
            return None
        
        # Ensure tracking lists are properly sized
        self._ensure_tracking_lists_size(len(self.children))
            
        best_score = float('-inf')
        best_actions = []
        
        for i, child in enumerate(self.children):
            if child is None:
                continue
                
            if self.children_completed_visit_count[i] == 0:
                # Prioritize unvisited children
                return i
            
            # WU-UCT formula: uses completed visits for exploitation, total visits for exploration
            exploitation = child.total_reward / self.children_completed_visit_count[i]
            exploration = exploration_constant * math.sqrt(
                math.log(max(self.visits, 1)) / max(child.visits, 1)  # Prevent division by zero
            )
            
            score = exploitation + exploration
            
            if score > best_score:
                best_score = score
                best_actions = [i]
            elif abs(score - best_score) < 1e-10:
                best_actions.append(i)
        
        return random.choice(best_actions) if best_actions else 0
        # TODO: see how paper does the return of best action in ties
    
    def update_incomplete(self, task_id: int, action: int):
        """Incomplete update for tracking unobserved samples."""
        if self.visits == 0:
            self.visited_node_count += 1
        self.visits += 1
        
        # Track this task as having an incomplete update on this node
        self.ongoing_tasks.add(task_id)
        
        # Track this as an ongoing simulation
        if action >= 0:  # Only for valid actions
            self._ensure_tracking_lists_size(action + 1)
            if self.children_completed_visit_count[action] == 0:
                self.updated_node_count += 1
    
    def update_complete(self, task_idx: int, action: int, reward: float) -> float:
        """Complete update for tracking observed samples."""
        action_to_update = action  # Default to passed action
        
        # Remove this task from ongoing tasks since it's now complete
        self.ongoing_tasks.discard(task_idx)
        
        if task_idx in self.traverse_history:
            stored_action, stored_reward = self.traverse_history.pop(task_idx)
            reward = stored_reward + reward  # Combine rewards
            action_to_update = stored_action  # Use the stored action for updates
        
        # Update completed visit count and Q-values
        if action_to_update >= 0:  # Only for valid actions
            self._ensure_tracking_lists_size(action_to_update + 1)
            self.children_completed_visit_count[action_to_update] += 1
            # Update Q-value calculation here if needed
        
        return reward


class WUUCTSolver:
    """
    Worker-UCT (WU-UCT) solver for the Orienteering Problem.
    Implements parallel MCTS with multiple workers sharing a global tree.
    """
    
    def __init__(self, problem: OrienteeringProblem, iterations: int, num_workers: int = 4, 
                 exploration_constant: float = math.sqrt(2), epsilon: float = 0.00):
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
        
        OPTIMIZATION: Release lock between nodes to allow parallel tree traversal.
        """
        current = node
        path = [current]
        task_id = self.get_task_id()
        
        while not current.state.is_terminal():
            # Lock only for operations on current node, then release
            with self.global_tree_lock:
                # Apply incomplete update (track unobserved sample)
                if hasattr(current, 'update_incomplete'):
                    current.update_incomplete(task_id, -1)  # -1 for selection
                else:
                    current.visits += 1
                
                if not current.is_fully_expanded():
                    # Found expandable node
                    return current, path, task_id
                
                if not current.children:
                    break
                
                # Select best child using WU-UCT formula
                action_idx = current.select_action_wu_uct(self.exploration_constant)
                if action_idx is None or action_idx >= len(current.children):
                    break
                
                # Get reference to next child while we have the lock
                next_child = current.children[action_idx]
            
            # Move to next node OUTSIDE the lock (allows other workers to traverse)
            current = next_child
            path.append(current)
        
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
    
    def safe_expand(self, node: WUUCTNode, task_id: int) -> tuple[WUUCTNode, int]:
        """Thread-safe expansion of a node. Returns (expanded_node, action)."""
        with self.global_tree_lock:
            # Double-check that expansion is still needed
            if node.is_fully_expanded():
                # Another worker already expanded, select child instead
                if node.children:
                    return random.choice(node.children), -1
                return node, -1
            
            # Get available actions and expand
            if not node.untried_actions:
                # Initialize untried actions if needed
                available_actions = node.state.get_available_actions()
                if available_actions:
                    node.untried_actions = [action.path[-1] for action in available_actions 
                                          if action.path[-1] not in [child.state.path[-1] for child in node.children]]
            
            if node.untried_actions:
                action = node.untried_actions.pop()
                new_state = node.state.apply_action(action)
                child_node = WUUCTNode(new_state, parent=node)
                node.children.append(child_node)
                
                # Store the action in traverse history for later updates
                node.traverse_history[task_id] = (action, 0.0)  # Initial reward is 0
                
                return child_node, action
            
            return node, -1
    
    def simulate(self, state: OrienteeringState) -> float:
        """
        Simulation phase - random rollout from given state.
        This can remain similar to single-threaded version.
        """
        current = state.copy()
        steps = 0
        max_steps = 10000  # Prevent infinite loops
        
        while not current.is_terminal() and steps < max_steps:
            actions = current.get_available_actions()
            if not actions:
                break
            
            # Random action selection for simulation
            action = random.choice(actions)
            # Extract the node ID from the action object
            if hasattr(action, 'path') and action.path:
                node_id = action.path[-1]
            else:
                # Fallback: action might already be a node ID
                node_id = action
            
            current = current.apply_action(node_id)
            steps += 1
        
        return current.get_reward()
    
    def wu_uct_backpropagate(self, path: List[tuple[WUUCTNode, int]], reward: float):
        """
        WU-UCT backpropagation: complete updates for observed samples.
        path contains tuples of (node, task_id) for proper tracking.
        
        OPTIMIZATION: Single lock for entire backpropagation instead of per-node.
        """
        accumulated_reward = reward
        
        # Acquire lock once for entire backpropagation
        with self.global_tree_lock:
            for node, task_id in reversed(path):
                if hasattr(node, 'update_complete'):
                    # Complete update for WU-UCT nodes
                    accumulated_reward = node.update_complete(task_id, -1, accumulated_reward)
                else:
                    # Fallback for regular MCTS nodes
                    node.visits += 1
                    node.total_reward += accumulated_reward
    
    def wu_uct_incomplete_update(self, path: List[tuple[WUUCTNode, int]]):
        """Apply incomplete updates along the path."""
        for node, task_id in path:
            with self.global_tree_lock:
                if hasattr(node, 'update_incomplete'):
                    node.update_incomplete(task_id, -1)  # -1 for path traversal
                else:
                    node.visits += 1  # Fallback
    
    def worker_iteration(self, worker_id: int):
        """Single MCTS iteration for a worker with proper WU-UCT handling."""
        root = self.initialize_root()
        
        # Selection phase
        leaf, selection_path, task_id = self.wu_uct_selection(root, worker_id)
        
        # Create path with task IDs for tracking
        wu_uct_path = [(node, task_id) for node in selection_path]
        
        # Apply incomplete updates (track unobserved samples)
        self.wu_uct_incomplete_update(wu_uct_path)
        
        # Expansion phase
        expanded_node, action = self.safe_expand(leaf, task_id)
        if expanded_node != leaf:
            # New node was created
            wu_uct_path.append((expanded_node, task_id))
        
        try:
            # Simulation phase
            reward = self.simulate(expanded_node.state)
            
            # Backpropagation (complete updates for observed samples)
            self.wu_uct_backpropagate(wu_uct_path, reward)
            
        except Exception as e:
            # If simulation fails, we need to handle cleanup
            # In WU-UCT, incomplete updates stay but we don't add complete updates
            print(f"Worker {worker_id} simulation failed: {e}")
            raise e
        
        # Update statistics
        with self.simulation_lock:
            self.total_simulations += 1
            if worker_id not in self.worker_stats:
                self.worker_stats[worker_id] = {'simulations': 0, 'total_reward': 0.0}
            self.worker_stats[worker_id]['simulations'] += 1
            self.worker_stats[worker_id]['total_reward'] += reward
    
    def run_parallel(self) -> OrienteeringState:
        """Run WU-UCT with multiple workers."""
        # Create and start worker threads
        iterations_per_worker = self.iterations // self.num_workers
        
        def worker_loop(worker_id: int):
            for _ in range(iterations_per_worker):
                if self.stop_flag.is_set():
                    break
                try:
                    self.worker_iteration(worker_id)
                except Exception as e:
                    print(f"Worker {worker_id} error: {e}")
        
        # Start all workers
        self.workers = []
        for i in range(self.num_workers):
            worker = threading.Thread(target=worker_loop, args=(i,))
            worker.start()
            self.workers.append(worker)
        
        # Wait for all workers to complete
        for worker in self.workers:
            worker.join()
        
        return self.get_best_path()
    
    def run(self) -> OrienteeringState:
        """
        Main entry point to run WU-UCT algorithm.
        Returns the best solution found.
        """
        print(f"Starting WU-UCT with {self.num_workers} workers, {self.iterations} iterations")
        print(f"Exploration constant: {self.exploration_constant}")
        
        
        start_time = time.time()
        
        try:
            # Run the parallel WU-UCT algorithm
            best_solution = self.run_parallel()
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Print results
            print(f"\nWU-UCT completed in {elapsed_time:.2f} seconds")
            print(f"Total simulations performed: {self.total_simulations}")
            print(f"Simulations per second: {self.total_simulations / elapsed_time:.1f}")
            
            # Print worker statistics
            print(f"\nWorker Statistics:")
            for worker_id, stats in self.worker_stats.items():
                avg_reward = stats['total_reward'] / stats['simulations'] if stats['simulations'] > 0 else 0
                print(f"  Worker {worker_id}: {stats['simulations']} simulations, avg reward: {avg_reward:.2f}")
            
            return best_solution
            
        except KeyboardInterrupt:
            print("\nWU-UCT interrupted by user")
            self.stop_flag.set()
            return self.get_best_path()
        except Exception as e:
            print(f"Error during WU-UCT execution: {e}")
            self.stop_flag.set()
            raise
    
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


if __name__ == "__main__":
    """Main function to run WU-UCT directly."""
    print("WU-UCT Orienteering Problem Solver")
    print("=" * 40)
    
    # Load a sample problem
    try:
        nodes, budget = OrienteeringProblem.load_problem(
            "OP_Benchmark_Set/sample/sample_30.txt"
            # "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
        )
        print(f"Loaded problem with {len(nodes)} nodes and budget {budget}")
    except Exception as e:
        print(f"Could not load sample problem: {e}")
        print("Please ensure problem files exist in OP_Benchmark_Set/sample/")
        exit(1)
    
    # Create problem instance
    problem = OrienteeringProblem(nodes, budget)
    
    # Create WU-UCT solver
    solver = WUUCTSolver(
        problem=problem,
        iterations=10000,  # Number of MCTS simulations
        num_workers=4,    # Number of parallel workers
        exploration_constant=math.sqrt(2),
        epsilon=0.00
    )
    
    # Run the solver
    best_solution = solver.run()
    
    # Display results
    print(f"\nBest Solution Found:")
    print(f"Path: {best_solution.get_path()}")
    print(f"Total reward: {best_solution.get_reward()}")
    print(f"Total cost: {best_solution.get_cost()}")
    print(f"Budget utilization: {best_solution.get_cost()}/{budget} ({100*best_solution.get_cost()/budget:.1f}%)")
    
    # Validate solution
    if best_solution.get_cost() <= budget:
        print("✓ Solution is feasible (within budget)")
    else:
        print("✗ Solution is infeasible (exceeds budget)")
    
    print(f"\nSolution quality: {best_solution.get_reward():.2f} reward per unit cost: {best_solution.get_reward()/max(best_solution.get_cost(), 1):.3f}")


# python3 -m MCTS.wu_uct