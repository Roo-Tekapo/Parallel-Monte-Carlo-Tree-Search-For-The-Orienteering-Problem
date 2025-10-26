"""
Simple WU-UCT Coordinator

Simplified coordinator for the unified worker WU-UCT implementation.
This coordinator manages multiple unified workers that each handle
both expansion and simulation, eliminating the need for work queues
and complex inter-worker coordination.
"""

import time
import math
from typing import Optional, List

from Simple_WU.orienteering_adapter import OrienteeringProblem, OrienteeringState
from Simple_WU.wu_uct_node import WUUCTNode
from Simple_WU.simple_wu_worker import SimpleWUWorker


class SimpleWUUCT:
    """
    Simplified WU-UCT algorithm coordinator.
    
    This class manages multiple unified workers that each perform
    complete MCTS iterations on a shared tree. The coordination
    is much simpler since there are no work queues or separate
    worker types to manage.
    """
    
    def __init__(self, 
                 problem: OrienteeringProblem,
                 num_workers: int = 4,
                 exploration_constant: float = math.sqrt(2),
                 max_distance: Optional[float] = None):
        """
        Initialize the Simple WU-UCT coordinator.
        
        Args:
            problem: The orienteering problem to solve
            num_workers: Number of unified workers to use
            exploration_constant: UCT exploration parameter
            max_distance: Maximum distance constraint for simulations
        """
        self.problem = problem
        self.num_workers = num_workers
        self.exploration_constant = exploration_constant
        self.max_distance = max_distance
        
        # Initialize shared search tree with initial state
        initial_state = OrienteeringState(problem)
        self.root = WUUCTNode(initial_state)
        
        # Worker management
        self.workers: List[SimpleWUWorker] = []
        
    def run(self, 
            max_iterations: int, 
            max_time: Optional[float] = None, 
            verbose: bool = False) -> OrienteeringState:
        """
        Run the Simple WU-UCT algorithm.
        
        Args:
            max_iterations: Total number of iterations to perform
            max_time: Maximum time limit (overrides max_iterations if specified)  
            verbose: Whether to print progress information
            
        Returns:
            The best orienteering state found
        """
        start_time = time.time()
        
        if verbose:
            print(f"Starting Simple WU-UCT with {self.num_workers} workers")
            print(f"Target: {max_iterations} iterations" + 
                  (f" or {max_time}s" if max_time else ""))
        
        # Calculate iterations per worker
        iterations_per_worker = max_iterations // self.num_workers
        
        # Handle remainder iterations
        remainder_iterations = max_iterations % self.num_workers
        
        # Create and start workers
        for i in range(self.num_workers):
            # Some workers get an extra iteration if there's a remainder
            worker_iterations = (iterations_per_worker + 1 
                               if i < remainder_iterations 
                               else iterations_per_worker)
            
            worker = SimpleWUWorker(
                problem=self.problem,
                root=self.root,
                worker_id=i,
                iterations_per_worker=worker_iterations,
                exploration_constant=self.exploration_constant,
                max_distance=self.max_distance
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
            
        # Time limit reached - workers will naturally stop when they complete their iterations
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
        
        print(f"\nSimple WU-UCT completed in {total_time:.2f}s")
        print(f"Total iterations: {total_iterations}")
        print(f"Total simulations: {total_simulations}")
        print(f"Iterations per second: {total_iterations / total_time:.1f}")
        print(f"Tree size: {self._count_tree_nodes()} nodes")
        print(f"Root visits: {self.root.visits}")
        print(f"Average simulation time: {total_sim_time / total_simulations:.4f}s")
        
        # Per-worker statistics
        print(f"\nPer-worker statistics:")
        for worker in self.workers:
            stats = worker.get_statistics()
            print(f"  Worker {stats['worker_id']}: {stats['iterations_completed']} iterations, "
                  f"{stats['simulations_completed']} simulations")
    
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
            print(f"  (Normalization scale: 1/{1/self.problem.reward_scale:.1f})")
        else:
            print(f"  Reward: {solution.reward_so_far:.2f}")
            
        print(f"  Cost: {solution.cost_so_far:.2f} / {self.problem.budget:.2f}")
                  
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
        
        This follows the path with the highest visit counts from root to leaf,
        which represents the most promising solution found.
        
        Returns:
            The best orienteering state found
        """
        current_node = self.root
        current_state = OrienteeringState(self.problem)
        
        # Follow path with highest visit counts
        while current_node.children:
            best_child = None
            best_visits = -1
            
            for child in current_node.children:
                if child.visits > best_visits:
                    best_visits = child.visits
                    best_child = child
                    
            if best_child is None:
                break
                
            # Get the action that leads to this child
            child_action = best_child.state.path[-1]
            current_state = self._create_next_state(current_state, child_action)
            current_node = best_child
            
        return current_state
        
    def get_tree_statistics(self):
        """
        Get detailed statistics about the search tree.
        
        Returns:
            Dictionary with tree statistics
        """
        def analyze_tree(node, depth=0):
            stats = {
                'nodes': 1,
                'max_depth': depth,
                'total_visits': node.visits,
                'total_reward': node.total_reward
            }
            
            for child in node.children:
                child_stats = analyze_tree(child, depth + 1)
                stats['nodes'] += child_stats['nodes']
                stats['max_depth'] = max(stats['max_depth'], child_stats['max_depth'])
                stats['total_visits'] += child_stats['total_visits']
                stats['total_reward'] += child_stats['total_reward']
                
            return stats
        
        return analyze_tree(self.root)
        
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