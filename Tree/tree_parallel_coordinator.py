"""
Tree Parallel MCTS Coordinator

Coordinator for tree-parallel MCTS with standard UCT.
Manages multiple workers that share a single tree structure.
"""

import time
import math
import threading
from typing import Optional, List

from Tree.orienteering_adapter import OrienteeringProblem, OrienteeringState
from Tree.tree_parallel_node import TreeParallelNode
from Tree.tree_parallel_worker import TreeParallelWorker


class TreeParallelMCTS:
    """
    Tree-parallel MCTS coordinator.
    
    Manages multiple workers that perform MCTS iterations on a shared tree.
    Uses standard UCT formula without WU-UCT modifications.
    """
    
    def __init__(self,
                 problem: OrienteeringProblem,
                 num_workers: int = 4,
                 exploration_constant: float = math.sqrt(2)):
        """
        Initialize the tree-parallel MCTS coordinator.
        
        Args:
            problem: The orienteering problem to solve
            num_workers: Number of worker threads to use
            exploration_constant: UCT exploration parameter (default: √2)
        """
        self.problem = problem
        self.num_workers = num_workers
        self.exploration_constant = exploration_constant
        
        # Initialize shared search tree with initial state
        initial_state = OrienteeringState(problem)
        self.root = TreeParallelNode(initial_state)
        
        # Global tree lock for expansion (optional, can use finer-grained locking)
        self.tree_lock = threading.Lock()
        
        # Worker management
        self.workers: List[TreeParallelWorker] = []
    
    def run(self,
            max_iterations: int,
            max_time: Optional[float] = None,
            verbose: bool = False) -> OrienteeringState:
        """
        Run the tree-parallel MCTS algorithm.
        
        Args:
            max_iterations: Total number of iterations to perform
            max_time: Maximum time limit (overrides max_iterations if specified)
            verbose: Whether to print progress information
            
        Returns:
            The best orienteering state found
        """
        start_time = time.time()
        
        if verbose:
            print(f"Starting Tree-Parallel MCTS with {self.num_workers} workers")
            print(f"Target: {max_iterations} iterations" +
                  (f" or {max_time}s" if max_time else ""))
            print(f"Exploration constant: {self.exploration_constant}")
        
        # Calculate iterations per worker
        iterations_per_worker = max_iterations // self.num_workers
        remainder_iterations = max_iterations % self.num_workers
        
        # Create and start workers
        for i in range(self.num_workers):
            # Some workers get an extra iteration if there's a remainder
            worker_iterations = (iterations_per_worker + 1
                               if i < remainder_iterations
                               else iterations_per_worker)
            
            worker = TreeParallelWorker(
                problem=self.problem,
                root=self.root,
                worker_id=i,
                iterations_per_worker=worker_iterations,
                exploration_constant=self.exploration_constant,
                tree_lock=self.tree_lock
            )
            
            self.workers.append(worker)
            worker.start()
        
        # Monitor progress if time limit is specified
        if max_time:
            self._monitor_with_time_limit(max_time, verbose)
        else:
            # Wait for all workers to complete
            for worker in self.workers:
                worker.join()
        
        end_time = time.time()
        
        # Print final statistics
        if verbose:
            self._print_final_statistics(end_time - start_time)
        
        # Extract best solution from the tree
        best_solution = self._extract_best_solution()
        
        if verbose:
            self._print_solution_details(best_solution)
        
        return best_solution
    
    def _monitor_with_time_limit(self, max_time: float, verbose: bool):
        """
        Monitor worker progress with a time limit.
        
        Args:
            max_time: Maximum time to run
            verbose: Whether to print progress updates
        """
        start_time = time.time()
        
        while time.time() - start_time < max_time:
            # Check if all workers are done
            if not any(worker.is_alive() for worker in self.workers):
                break
            
            if verbose:
                # Print periodic progress updates
                elapsed = time.time() - start_time
                completed_iterations = sum(worker.iterations_completed for worker in self.workers)
                print(f"Progress: {completed_iterations} iterations in {elapsed:.1f}s")
            
            time.sleep(1.0)  # Check every second
        
        if verbose:
            print(f"Time limit of {max_time}s reached")
    
    def _print_final_statistics(self, total_time: float):
        """
        Print comprehensive algorithm statistics.
        
        Args:
            total_time: Total execution time in seconds
        """
        total_iterations = sum(worker.iterations_completed for worker in self.workers)
        total_simulations = sum(worker.simulations_completed for worker in self.workers)
        total_sim_time = sum(worker.total_simulation_time for worker in self.workers)
        
        print(f"\nTree-Parallel MCTS completed in {total_time:.2f}s")
        print(f"Total iterations: {total_iterations}")
        print(f"Total simulations: {total_simulations}")
        print(f"Iterations per second: {total_iterations / total_time:.1f}")
        print(f"Tree size: {self._count_tree_nodes()} nodes")
        print(f"Root visits: {self.root.visits}")
        if total_simulations > 0:
            print(f"Average simulation time: {total_sim_time / total_simulations:.4f}s")
        
        # Lock contention / collision statistics
        total_collisions = sum(worker.lock_contentions for worker in self.workers)
        avg_collision_rate = sum(worker.get_statistics()['collision_rate'] for worker in self.workers) / len(self.workers)
        
        print(f"\nParallel Coordination (Lock Contention):")
        print(f"  Total Lock Contentions: {total_collisions}")
        print(f"  Avg Contention Rate: {avg_collision_rate:.2%}")
        print(f"    (Workers competing for tree expansion rights)")
        
        # Per-worker statistics
        print(f"\nPer-Worker Performance:")
        print(f"  {'Worker':<8} {'Iters':<8} {'Sims':<8} {'Avg Sim(ms)':<12} {'Contentions':<12} {'Rate':<10}")
        print(f"  {'-'*70}")
        for worker in self.workers:
            stats = worker.get_statistics()
            print(f"  {stats['worker_id']:<8} "
                  f"{stats['iterations_completed']:<8} "
                  f"{stats['simulations_completed']:<8} "
                  f"{stats['avg_simulation_time']*1000:<12.3f} "
                  f"{stats['lock_contentions']:<12} "
                  f"{stats['collision_rate']:<10.2%}")
    
    def _print_solution_details(self, solution: OrienteeringState):
        """
        Print solution details with both normalized and actual rewards.
        
        Args:
            solution: The best solution found
        """
        # Calculate actual reward from raw node scores
        actual_reward = sum(self.problem.nodes[node_id].score for node_id in solution.path)
        
        print(f"\nBest solution found:")
        print(f"  Path length: {len(solution.path)} nodes")
        print(f"  Path: {solution.path}")
        
        if self.problem.normalize_rewards:
            print(f"  Normalized reward: {solution.reward_so_far:.6f}")
            print(f"  Actual reward: {actual_reward}")
        else:
            print(f"  Reward: {solution.reward_so_far:.2f}")
        
        print(f"  Cost: {solution.cost_so_far:.2f} / {self.problem.budget:.2f}")
        print(f"  Valid solution: {solution.is_terminal()}")
    
    def _count_tree_nodes(self) -> int:
        """
        Count the total number of nodes in the search tree.
        
        Returns:
            Total number of nodes in the tree
        """
        def count_recursive(node):
            count = 1  # Count current node
            for child in node.children:
                count += count_recursive(child)
            return count
        
        return count_recursive(self.root)
    
    def _extract_best_solution(self) -> OrienteeringState:
        """
        Extract the best solution from the search tree.
        
        Follows the path with the highest visit counts from root to leaf.
        
        Returns:
            The best orienteering state found
        """
        current_node = self.root
        current_state = OrienteeringState(self.problem)
        
        # Follow path with highest visit counts
        while current_node.children:
            best_child = current_node.get_best_child_by_visits()
            
            if best_child is None:
                break
            
            # Get the action that leads to this child
            child_action = best_child.state.path[-1]
            current_state = current_state.apply_action(child_action)
            current_node = best_child
        
        return current_state
    
    def get_tree_statistics(self):
        """
        Get detailed statistics about the search tree.
        
        Returns:
            Dictionary with tree statistics
        """
        def analyze_tree(node, depth=0):
            stats = node.get_statistics()
            stats['depth'] = depth
            stats['max_depth'] = depth
            stats['total_nodes'] = 1
            
            for child in node.children:
                child_stats = analyze_tree(child, depth + 1)
                stats['total_nodes'] += child_stats['total_nodes']
                stats['max_depth'] = max(stats['max_depth'], child_stats['max_depth'])
            
            return stats
        
        return analyze_tree(self.root)
