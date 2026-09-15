"""
Optimized WU-UCT implementation with reduced lock contention.

Key optimizations:
1. Fine-grained locking (lock only when necessary)
2. Batch backpropagation updates
3. Virtual loss for worker coordination
4. Per-node locks for updates
"""

import threading
import math
import random
import time
from typing import Dict, List, Optional, Set, Tuple
from MCTS.mcts_node import MCTSNode
from orienteering.orienteering import OrienteeringProblem, OrienteeringState


class OptimizedWUUCTNode(MCTSNode):
    """Optimized WU-UCT node with per-node locking."""
    
    def __init__(self, state: OrienteeringState, parent=None):
        super().__init__(state, parent)
        
        # Per-node lock for fine-grained concurrency
        self._node_lock = threading.Lock()
        
        # Virtual loss tracking
        self.virtual_losses = 0
        
    def select_action_wu_uct(self, exploration_constant: float = math.sqrt(2)) -> int:
        """Thread-safe WU-UCT selection."""
        if not self.children:
            return None
        
        with self._node_lock:
            best_score = float('-inf')
            best_actions = []
            unvisited_actions = []
            
            real_parent_visits = max(self.visits - self.virtual_losses, 1)
            log_parent = math.log(real_parent_visits)
            
            for i, child in enumerate(self.children):
                if child is None:
                    continue
                
                with child._node_lock:
                    real_child_visits = child.visits - child.virtual_losses
                    if real_child_visits == 0 and child.virtual_losses == 0:
                        unvisited_actions.append(i)
                        continue
                    
                    effective_visits = max(child.visits, 1)
                    exploitation = child.total_reward / effective_visits
                    exploration = exploration_constant * math.sqrt(
                        log_parent / effective_visits
                    )
                    score = exploitation + exploration
                    
                    if score > best_score:
                        best_score = score
                        best_actions = [i]
                    elif abs(score - best_score) < 1e-10:
                        best_actions.append(i)
            
            if unvisited_actions:
                return random.choice(unvisited_actions)
            return random.choice(best_actions) if best_actions else 0
    
    def apply_virtual_loss(self, loss_value: int = 3):
        """Apply virtual loss to discourage other workers."""
        with self._node_lock:
            self.virtual_losses += loss_value
            self.visits += loss_value
    
    def remove_virtual_loss(self, loss_value: int = 3):
        """Remove virtual loss after simulation completes."""
        with self._node_lock:
            self.virtual_losses -= loss_value
            self.visits -= loss_value
    
    def update_result(self, reward: float):
        """Thread-safe update with actual simulation result."""
        with self._node_lock:
            self.visits += 1
            self.total_reward += reward


class OptimizedWUUCTSolver:
    """
    Optimized Worker-UCT (WU-UCT) solver with reduced lock contention.
    """
    
    def __init__(self, problem: OrienteeringProblem, iterations: int, num_workers: int = 4,
                 exploration_constant: float = math.sqrt(2), virtual_loss: int = 3):
        self.problem = problem
        self.iterations = iterations
        self.num_workers = num_workers
        self.exploration_constant = exploration_constant
        self.virtual_loss = virtual_loss
        
        # Shared tree with minimal global locking
        self.root: Optional[OptimizedWUUCTNode] = None
        self.tree_structure_lock = threading.RLock()  # Only for structural changes
        
        # Worker management
        self.workers: List[threading.Thread] = []
        self.worker_stats: Dict[int, Dict] = {}
        self.stop_flag = threading.Event()
        
        # Performance tracking
        self.total_simulations = 0
        self.simulation_lock = threading.Lock()
    
    def initialize_root(self) -> OptimizedWUUCTNode:
        """Initialize the root node."""
        if self.root is None:
            root_state = OrienteeringState(self.problem)
            self.root = OptimizedWUUCTNode(root_state)
        return self.root
    
    def selection_with_virtual_loss(self, node: OptimizedWUUCTNode) -> Tuple[OptimizedWUUCTNode, List[OptimizedWUUCTNode]]:
        """
        Selection phase with virtual loss.
        Uses fine-grained locking - only locks when reading/modifying nodes.
        """
        path = [node]
        current = node
        
        while not current.state.is_terminal():
            # Apply virtual loss to this node
            current.apply_virtual_loss(self.virtual_loss)
            
            # Check if node needs expansion (lock only for read)
            is_fully_expanded = current.is_fully_expanded()
            
            if not is_fully_expanded:
                # Found node to expand
                return current, path
            
            if not current.children:
                # No children despite being "fully expanded"
                return current, path
            
            # Select best child using UCT (locks internally)
            action_idx = current.select_action_wu_uct(self.exploration_constant)
            
            if action_idx is None:
                return current, path
            
            # Get child reference (quick read, no lock needed)
            if action_idx < len(current.children):
                child = current.children[action_idx]
                if child is not None:
                    current = child
                    path.append(current)
                else:
                    return current, path
            else:
                return current, path
        
        return current, path
    
    def expand_node(self, node: OptimizedWUUCTNode) -> Optional[OptimizedWUUCTNode]:
        """
        Expand a node by adding one child.
        Only locks for structural modification.
        """
        # Check if we need to expand (quick read)
        if node.is_fully_expanded():
            return None
        
        # Get available actions outside lock
        if not node.untried_actions:
            available_actions = node.state.get_available_actions()
            if not available_actions:
                return None
            
            # Initialize untried actions (lock for write)
            with self.tree_structure_lock:
                if not node.untried_actions:  # Double-check
                    node.untried_actions = [
                        action.path[-1] for action in available_actions
                        if action.path[-1] not in [child.state.path[-1] for child in node.children]
                    ]
        
        # Select action to expand
        with self.tree_structure_lock:
            if not node.untried_actions:
                return None
            action = node.untried_actions.pop()
        
        # Create child state (outside lock - can be slow)
        new_state = node.state.apply_action(action)
        child_node = OptimizedWUUCTNode(new_state, parent=node)
        
        # Add child to tree (lock for structural change)
        with self.tree_structure_lock:
            node.children.append(child_node)
        
        return child_node
    
    def simulate(self, state: OrienteeringState) -> float:
        """Simulation phase - no locking needed."""
        current = state.copy()
        steps = 0
        max_steps = 10000
        
        while not current.is_terminal() and steps < max_steps:
            actions = current.get_available_actions()
            if not actions:
                break
            
            action = random.choice(actions)
            if hasattr(action, 'path') and action.path:
                node_id = action.path[-1]
            else:
                node_id = action
            
            current = current.apply_action(node_id)
            steps += 1
        
        return current.get_reward()
    
    def backpropagate_batch(self, path: List[OptimizedWUUCTNode], reward: float):
        """
        Batch backpropagation with virtual loss removal.
        Each node locks only itself (no global lock).
        """
        # First, remove virtual losses in reverse order
        for node in reversed(path):
            node.remove_virtual_loss(self.virtual_loss)
        
        # Then update with actual results
        accumulated_reward = reward
        for node in reversed(path):
            node.update_result(accumulated_reward)
    
    def worker_iteration(self, worker_id: int):
        """Single MCTS iteration for a worker."""
        root = self.initialize_root()
        
        try:
            # Selection with virtual loss
            leaf, selection_path = self.selection_with_virtual_loss(root)
            
            # Expansion
            expanded_node = self.expand_node(leaf)
            if expanded_node is not None:
                # Apply virtual loss to new node
                expanded_node.apply_virtual_loss(self.virtual_loss)
                selection_path.append(expanded_node)
                simulation_node = expanded_node
            else:
                simulation_node = leaf
            
            # Simulation (no locking)
            reward = self.simulate(simulation_node.state)
            
            # Backpropagation (batch update with per-node locks)
            self.backpropagate_batch(selection_path, reward)
            
            # Update statistics
            with self.simulation_lock:
                self.total_simulations += 1
                if worker_id not in self.worker_stats:
                    self.worker_stats[worker_id] = {'simulations': 0, 'total_reward': 0.0}
                self.worker_stats[worker_id]['simulations'] += 1
                self.worker_stats[worker_id]['total_reward'] += reward
        
        except Exception as e:
            # On error, still need to remove virtual losses
            if 'selection_path' in locals():
                for node in reversed(selection_path):
                    node.remove_virtual_loss(self.virtual_loss)
            print(f"Worker {worker_id} error: {e}")
            raise
    
    def run_parallel(self) -> OrienteeringState:
        """Run optimized WU-UCT with multiple workers."""
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
        
        # Wait for completion
        for worker in self.workers:
            worker.join()
        
        return self.get_best_path()
    
    def run(self) -> OrienteeringState:
        """Main entry point."""
        print(f"Starting Optimized WU-UCT with {self.num_workers} workers, {self.iterations} iterations")
        print(f"Exploration constant: {self.exploration_constant}, Virtual loss: {self.virtual_loss}")
        
        start_time = time.time()
        
        try:
            best_solution = self.run_parallel()
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            print(f"\nOptimized WU-UCT completed in {elapsed_time:.2f} seconds")
            print(f"Total simulations: {self.total_simulations}")
            print(f"Simulations per second: {self.total_simulations / elapsed_time:.1f}")
            
            print(f"\nWorker Statistics:")
            for worker_id, stats in self.worker_stats.items():
                avg_reward = stats['total_reward'] / stats['simulations'] if stats['simulations'] > 0 else 0
                print(f"  Worker {worker_id}: {stats['simulations']} simulations, avg reward: {avg_reward:.2f}")
            
            return best_solution
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            self.stop_flag.set()
            return self.get_best_path()
        except Exception as e:
            print(f"Error: {e}")
            self.stop_flag.set()
            raise
    
    def get_best_path(self) -> OrienteeringState:
        """Extract best path from tree."""
        if not self.root or not self.root.children:
            return OrienteeringState(self.problem)
        
        best_child = max(
            self.root.children,
            key=lambda c: c.total_reward / max(c.visits - c.virtual_losses, 1) if c.visits > 0 else float('-inf')
        )
        
        current = best_child
        while current.children:
            current = max(
                current.children,
                key=lambda c: c.total_reward / max(c.visits - c.virtual_losses, 1) if c.visits > 0 else float('-inf')
            )
        
        return current.state


if __name__ == "__main__":
    print("Optimized WU-UCT Solver")
    print("=" * 40)
    
    # Test
    try:
        nodes, budget = OrienteeringProblem.load_problem(
            "OP_Benchmark_Set/sample/sample_30.txt"
        )
        print(f"Loaded: {len(nodes)} nodes, budget: {budget}")
    except Exception as e:
        print(f"Error loading problem: {e}")
        exit(1)
    
    problem = OrienteeringProblem(nodes, budget)
    
    solver = OptimizedWUUCTSolver(
        problem=problem,
        iterations=1000,
        num_workers=4,
        exploration_constant=math.sqrt(2),
        virtual_loss=3
    )
    
    best_solution = solver.run()
    
    print(f"\nBest Solution:")
    print(f"Path: {best_solution.get_path()}")
    print(f"Reward: {best_solution.get_reward()}")
    print(f"Cost: {best_solution.get_cost()}/{budget}")
