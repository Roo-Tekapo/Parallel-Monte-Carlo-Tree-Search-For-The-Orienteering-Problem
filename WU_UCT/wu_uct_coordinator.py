"""
WU-UCT Coordinator

Manages expansion and simulation workers, coordinates the overall WU-UCT algorithm.
"""

import time
import threading
from typing import Optional, List
from queue import Queue
import math

from WU_UCT.wu_uct_node import WUUCTNode
from WU_UCT.expansion_worker import ExpansionWorker
from WU_UCT.simulation_worker import SimulationWorker


class WUUCTCoordinator:
    """
    Coordinator for true WU-UCT algorithm.
    
    Manages:
    - Expansion workers (tree traversal and node expansion)
    - Simulation workers (performing rollouts)
    - Work queue connecting expansion to simulation
    - Overall algorithm execution
    
    Following the design from Chen et al. (2018).
    """
    
    def __init__(self, 
                 problem,
                 num_expansion_workers: int = 4,
                 num_simulation_workers: int = 8,
                 exploration_constant: float = math.sqrt(2),
                 work_queue_size: int = 1000,
                 max_distance: float = 1.42):
        """
        Initialize WU-UCT coordinator.
        
        Args:
            problem: Problem instance (e.g., OrienteeringProblem)
            num_expansion_workers: Number of expansion workers
            num_simulation_workers: Number of simulation workers
            exploration_constant: UCT exploration parameter
            work_queue_size: Maximum size of work queue
            max_distance: Maximum travel distance constraint (default: 1.42)
        """
        self.problem = problem
        self.num_expansion_workers = num_expansion_workers
        self.num_simulation_workers = num_simulation_workers
        self.exploration_constant = exploration_constant
        self.max_distance = max_distance
        
        # Create shared work queue
        self.work_queue = Queue(maxsize=work_queue_size)
        
        # Create root node
        initial_state = self._create_initial_state()
        self.root = WUUCTNode(initial_state)
        
        # Worker management
        self.expansion_workers: List[ExpansionWorker] = []
        self.simulation_workers: List[SimulationWorker] = []
        self.stop_event = threading.Event()
        
    def run(self, 
            max_iterations: int,
            max_time: Optional[float] = None,
            verbose: bool = True):
        """
        Run the WU-UCT algorithm.
        
        Args:
            max_iterations: Total number of iterations (divided among expansion workers)
            max_time: Optional time limit in seconds
            verbose: Whether to print progress information
            
        Returns:
            Best solution found
        """
        start_time = time.time()
        
        if verbose:
            print(f"Starting True WU-UCT")
            print(f"Expansion workers: {self.num_expansion_workers}")
            print(f"Simulation workers: {self.num_simulation_workers}")
            print(f"Target iterations: {max_iterations}")
            if max_time:
                print(f"Time limit: {max_time}s")
        
        # Calculate iterations per expansion worker
        iterations_per_worker = max_iterations // self.num_expansion_workers
        remainder = max_iterations % self.num_expansion_workers
        
        # Create and start simulation workers
        for i in range(self.num_simulation_workers):
            worker = SimulationWorker(
                worker_id=i,
                work_queue=self.work_queue,
                stop_event=self.stop_event,
                problem=self.problem,
                max_distance=self.max_distance
            )
            self.simulation_workers.append(worker)
            worker.start()
        
        if verbose:
            print(f"Started {self.num_simulation_workers} simulation workers")
        
        # Create and start expansion workers
        for i in range(self.num_expansion_workers):
            # Distribute remainder iterations
            worker_iterations = iterations_per_worker + (1 if i < remainder else 0)
            
            worker = ExpansionWorker(
                worker_id=i,
                root=self.root,
                work_queue=self.work_queue,
                num_iterations=worker_iterations,
                exploration_constant=self.exploration_constant,
                problem=self.problem,
                max_distance=self.max_distance
            )
            self.expansion_workers.append(worker)
            worker.start()
        
        if verbose:
            print(f"Started {self.num_expansion_workers} expansion workers")
        
        # Monitor progress
        if max_time:
            self._monitor_with_time_limit(max_time, verbose)
        else:
            # Wait for all expansion workers to complete
            for worker in self.expansion_workers:
                worker.join()
            
            if verbose:
                print("All expansion workers completed")
        
        # Wait for work queue to empty
        if verbose:
            print("Waiting for simulation queue to empty...")
        
        self.work_queue.join()
        
        # Stop simulation workers
        self.stop_event.set()
        
        for worker in self.simulation_workers:
            worker.join(timeout=1.0)
        
        end_time = time.time()
        
        # Print statistics
        if verbose:
            self._print_statistics(end_time - start_time)
        
        # Extract best solution
        best_solution = self._extract_best_solution()
        
        return best_solution
    
    def _monitor_with_time_limit(self, max_time: float, verbose: bool):
        """
        Monitor worker progress with time limit.
        
        Args:
            max_time: Maximum time to run
            verbose: Whether to print progress updates
        """
        start_time = time.time()
        
        while time.time() - start_time < max_time:
            # Check if expansion workers are done
            if not any(w.is_alive() for w in self.expansion_workers):
                break
            
            if verbose:
                elapsed = time.time() - start_time
                completed = sum(w.iterations_completed for w in self.expansion_workers)
                queue_size = self.work_queue.qsize()
                print(f"Progress: {completed} iterations, queue: {queue_size}, time: {elapsed:.1f}s")
            
            time.sleep(1.0)
        
        if verbose:
            print(f"Time limit reached or workers completed")
    
    def _print_statistics(self, total_time: float):
        """
        Print comprehensive statistics.
        
        Args:
            total_time: Total execution time
        """
        print(f"\n{'='*70}")
        print(f"WU-UCT Algorithm Completed in {total_time:.2f}s")
        print(f"{'='*70}")
        
        # Expansion worker stats
        total_iterations = sum(w.iterations_completed for w in self.expansion_workers)
        total_expansions = sum(w.expansions_performed for w in self.expansion_workers)
        
        print(f"\nExpansion Phase:")
        print(f"  Total iterations: {total_iterations}")
        print(f"  Total expansions: {total_expansions}")
        print(f"  Iterations/sec: {total_iterations / total_time:.1f}")
        
        print(f"\n  Per-Worker Breakdown:")
        print(f"  {'Worker':<8} {'Iterations':<12} {'Expansions':<12} {'Avg Select(ms)':<15}")
        print(f"  {'-'*60}")
        for worker in self.expansion_workers:
            stats = worker.get_statistics()
            print(f"  Exp-{stats['worker_id']:<4} "
                  f"{stats['iterations_completed']:<12} "
                  f"{stats['expansions_performed']:<12} "
                  f"{stats['avg_selection_time']*1000:<15.3f}")
        
        # Simulation worker stats
        total_simulations = sum(w.simulations_completed for w in self.simulation_workers)
        
        print(f"\nSimulation Phase:")
        print(f"  Total simulations: {total_simulations}")
        print(f"  Simulations/sec: {total_simulations / total_time:.1f}")
        
        print(f"\n  Per-Worker Breakdown:")
        print(f"  {'Worker':<8} {'Simulations':<12} {'Avg Sim(ms)':<12} {'Avg BP(ms)':<12} {'Queue Wait(ms)':<15}")
        print(f"  {'-'*75}")
        for worker in self.simulation_workers:
            stats = worker.get_statistics()
            print(f"  Sim-{stats['worker_id']:<4} "
                  f"{stats['simulations_completed']:<12} "
                  f"{stats['avg_simulation_time']*1000:<12.3f} "
                  f"{stats['avg_backprop_time']*1000:<12.3f} "
                  f"{stats['avg_queue_wait_time']*1000:<15.3f}")
        
        # Tree statistics
        tree_stats = self._get_tree_statistics()
        print(f"\nTree Statistics:")
        print(f"  Total nodes: {tree_stats['total_nodes']}")
        print(f"  Max depth: {tree_stats['max_depth']}")
        print(f"  Root visits: {self.root.visits}")
        root_stats = self.root.get_local_statistics()
        print(f"  Root avg reward: {root_stats.average_reward:.4f}")
        
        # Efficiency metrics
        print(f"\nEfficiency Metrics:")
        print(f"  Worker utilization: {(total_simulations / total_iterations * 100):.1f}%")
        print(f"  Expansion/Simulation ratio: 1:{total_simulations/total_iterations:.2f}")
        
    def _get_tree_statistics(self) -> dict:
        """
        Gather statistics about the search tree.
        
        Returns:
            Dictionary with tree statistics
        """
        def count_recursive(node, depth=0):
            stats = {
                'total_nodes': 1,
                'max_depth': depth,
                'total_visits': node.visits
            }
            
            for child in node.children:
                child_stats = count_recursive(child, depth + 1)
                stats['total_nodes'] += child_stats['total_nodes']
                stats['max_depth'] = max(stats['max_depth'], child_stats['max_depth'])
                stats['total_visits'] += child_stats['total_visits']
            
            return stats
        
        return count_recursive(self.root)
    
    def get_statistics(self) -> dict:
        """
        Get comprehensive statistics about the run.
        
        Returns:
            Dictionary with algorithm statistics
        """
        total_iterations = sum(w.iterations_completed for w in self.expansion_workers)
        total_expansions = sum(w.expansions_performed for w in self.expansion_workers)
        total_simulations = sum(w.simulations_completed for w in self.simulation_workers)
        
        tree_stats = self._get_tree_statistics()
        
        return {
            'total_iterations': total_iterations,
            'total_expansions': total_expansions,
            'total_simulations': total_simulations,
            'iterations_per_second': 0,  # Will be computed by caller if needed
            'tree_nodes': tree_stats['total_nodes'],
            'tree_depth': tree_stats['max_depth'],
            'root_visits': self.root.visits,
        }
    
    def _extract_best_solution(self):
        """
        Extract the best solution by following most-visited path.
        
        Returns:
            Best state found
        """
        current_node = self.root
        
        while current_node.children:
            # Select child with most visits
            best_child = max(current_node.children, key=lambda c: c.visits)
            
            if best_child.visits == 0:
                break
            
            current_node = best_child
        
        return current_node.state
    
    def _create_initial_state(self):
        """
        Create initial state for the problem.
        
        Returns:
            Initial state
        """
        if hasattr(self.problem, 'create_initial_state'):
            return self.problem.create_initial_state()
        else:
            # For orienteering problems
            from orienteering.orienteering_optimized import OrienteeringState
            return OrienteeringState(self.problem)
