"""
Virtual Loss Coordinator

Manages multiple VL workers performing parallel MCTS with Virtual Loss coordination.
This coordinator is simpler than WU-UCT since VL doesn't require work queues or
complex inter-worker communication.
"""

import time
import math
from typing import Optional, List

from orienteering.orienteering_traditional import OrienteeringProblem, OrienteeringState
from VL.vl_node import VLNode
from VL.vl_worker import VLWorker


class VirtualLossMCTS:
    """
    Virtual Loss parallel MCTS coordinator.
    
    This class manages multiple worker threads that use the Virtual Loss
    mechanism for coordination. Unlike WU-UCT which modifies the UCT formula,
    VL uses standard UCT but temporarily penalizes nodes being explored.
    
    Virtual Loss Advantages:
    - Simpler than WU-UCT (no formula modification)
    - Fixed penalty is intuitive to tune
    - Direct impact on node selection
    
    Virtual Loss vs WU-UCT:
    - VL: Fixed penalty value applied temporarily
    - WU-UCT: Pending simulation count affects UCT calculation
    """
    
    def __init__(self,
                 problem: OrienteeringProblem,
                 num_workers: int = 4,
                 exploration_constant: float = math.sqrt(2),
                 virtual_loss_value: float = 1.0,
                 max_distance: Optional[float] = None):
        """
        Initialize Virtual Loss MCTS coordinator.
        
        Args:
            problem: Orienteering problem to solve
            num_workers: Number of parallel worker threads
            exploration_constant: UCT exploration constant (default: √2)
            virtual_loss_value: Fixed penalty value (default: 1.0)
                - Higher values = more aggressive thread separation
                - Lower values = more exploitation of good paths
                - Typical range: 0.5 - 3.0
            max_distance: Maximum distance constraint
        """
        self.problem = problem
        self.num_workers = num_workers
        self.exploration_constant = exploration_constant
        self.virtual_loss_value = virtual_loss_value
        self.max_distance = max_distance
        
        # Initialize search tree
        initial_state = OrienteeringState(problem)
        self.root = VLNode(initial_state)
        
        # Worker management
        self.workers: List[VLWorker] = []
    
    def run(self,
            max_iterations: int,
            max_time: Optional[float] = None,
            verbose: bool = False) -> OrienteeringState:
        """
        Run Virtual Loss MCTS algorithm.
        
        Args:
            max_iterations: Total number of iterations to perform
            max_time: Maximum time limit (overrides iterations if specified)
            verbose: Print progress information
            
        Returns:
            Best solution found
        """
        start_time = time.time()
        
        if verbose:
            print(f"Starting Virtual Loss MCTS with {self.num_workers} workers")
            print(f"Virtual Loss Value: {self.virtual_loss_value}")
            print(f"Target: {max_iterations} iterations" +
                  (f" or {max_time}s" if max_time else ""))
        
        # Distribute iterations across workers
        iterations_per_worker = max_iterations // self.num_workers
        remainder_iterations = max_iterations % self.num_workers
        
        # Create and start workers
        for i in range(self.num_workers):
            worker_iterations = (iterations_per_worker + 1
                               if i < remainder_iterations
                               else iterations_per_worker)
            
            worker = VLWorker(
                problem=self.problem,
                root=self.root,
                worker_id=i,
                iterations_per_worker=worker_iterations,
                exploration_constant=self.exploration_constant,
                virtual_loss_value=self.virtual_loss_value,
                max_distance=self.max_distance
            )
            
            self.workers.append(worker)
            worker.start()
        
        # Wait for all workers to complete (with timeout if specified)
        if max_time:
            deadline = start_time + max_time
            for worker in self.workers:
                remaining_time = deadline - time.time()
                if remaining_time > 0:
                    worker.join(timeout=remaining_time)
                else:
                    break
        else:
            for worker in self.workers:
                worker.join()
        
        elapsed_time = time.time() - start_time
        
        if verbose:
            self._print_statistics(elapsed_time)
        
        # Extract best solution
        best_solution = self._get_best_solution()
        
        return best_solution
    
    def _get_best_solution(self) -> OrienteeringState:
        """
        Extract the best solution from the search tree.
        
        Follows the path with highest visit counts from root.
        
        Returns:
            Best orienteering state found
        """
        current_node = self.root
        
        while current_node.children:
            # Select child with most visits
            best_child = max(current_node.children, key=lambda c: c.visits)
            current_node = best_child
        
        return current_node.state
    
    def _print_statistics(self, elapsed_time: float):
        """
        Print algorithm statistics.
        
        Args:
            elapsed_time: Total execution time
        """
        print(f"\n{'='*60}")
        print("Virtual Loss MCTS Statistics")
        print(f"{'='*60}")
        
        # Overall statistics
        total_iterations = sum(w.iterations_completed for w in self.workers)
        total_simulations = sum(w.simulations_completed for w in self.workers)
        iterations_per_sec = total_iterations / elapsed_time if elapsed_time > 0 else 0
        
        print(f"\nOverall Performance:")
        print(f"  Total Time: {elapsed_time:.2f}s")
        print(f"  Total Iterations: {total_iterations}")
        print(f"  Total Simulations: {total_simulations}")
        print(f"  Iterations/sec: {iterations_per_sec:.2f}")
        
        # Root node statistics
        print(f"\nRoot Node:")
        print(f"  Visits: {self.root.visits}")
        print(f"  Total Reward: {self.root.total_reward:.2f}")
        print(f"  Avg Reward: {self.root.total_reward / self.root.visits if self.root.visits > 0 else 0:.4f}")
        print(f"  Children: {len(self.root.children)}")
        
        # Virtual Loss statistics
        total_collisions = sum(w.virtual_loss_collisions for w in self.workers)
        avg_collision_rate = sum(w.get_statistics()['collision_rate'] for w in self.workers) / len(self.workers)
        
        print(f"\nVirtual Loss Coordination:")
        print(f"  VL Value: {self.virtual_loss_value}")
        print(f"  Total Collisions: {total_collisions}")
        print(f"  Avg Collision Rate: {avg_collision_rate:.2%}")
        print(f"    (Lower is better - indicates good thread separation)")
        
        # Per-worker statistics
        print(f"\nPer-Worker Performance:")
        print(f"  {'Worker':<8} {'Iters':<8} {'Sims':<8} {'Avg Sim(ms)':<12} {'Collisions':<12} {'Coll Rate':<10}")
        print(f"  {'-'*70}")
        
        for worker in self.workers:
            stats = worker.get_statistics()
            print(f"  {stats['worker_id']:<8} "
                  f"{stats['iterations_completed']:<8} "
                  f"{stats['simulations_completed']:<8} "
                  f"{stats['avg_simulation_time']*1000:<12.3f} "
                  f"{stats['virtual_loss_collisions']:<12} "
                  f"{stats['collision_rate']:<10.2%}")
        
        # Best solution path
        best_solution = self._get_best_solution()
        
        # Calculate actual reward from raw node scores
        actual_reward = sum(self.problem.nodes[node_id].score for node_id in best_solution.path)
        
        print(f"\nBest Solution Found:")
        print(f"  Path length: {len(best_solution.path)} nodes")
        print(f"  Path: {best_solution.path}")
        
        if self.problem.normalize_rewards:
            print(f"  Normalized reward: {best_solution.reward_so_far:.6f}")
            print(f"  Actual reward: {actual_reward}")
            print(f"  (Normalization scale: 1/{1/self.problem.reward_scale:.1f})")
        else:
            print(f"  Reward: {best_solution.reward_so_far:.2f}")
            
        print(f"  Cost: {best_solution.cost_so_far:.2f} / {self.problem.budget:.2f}")
        
        print(f"{'='*60}\n")
    
    def get_tree_statistics(self):
        """
        Get detailed tree statistics for analysis.
        
        Returns:
            Dictionary with tree statistics
        """
        def count_nodes(node):
            """Recursively count nodes in tree."""
            count = 1
            for child in node.children:
                count += count_nodes(child)
            return count
        
        def get_max_depth(node, depth=0):
            """Get maximum depth of tree."""
            if not node.children:
                return depth
            return max(get_max_depth(child, depth + 1) for child in node.children)
        
        total_nodes = count_nodes(self.root)
        max_depth = get_max_depth(self.root)
        
        return {
            'total_nodes': total_nodes,
            'max_depth': max_depth,
            'root_visits': self.root.visits,
            'root_children': len(self.root.children),
            'root_avg_reward': self.root.total_reward / self.root.visits if self.root.visits > 0 else 0
        }
