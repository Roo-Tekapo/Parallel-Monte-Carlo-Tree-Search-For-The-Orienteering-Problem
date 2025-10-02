"""
Main WU-UCT coordinator.

This is the main entry point for the WU-UCT algorithm that:
1. Coordinates between expansion and simulation workers
2. Manages the overall algorithm execution
3. Provides a clean interface for running WU-UCT
4. Handles worker lifecycle and statistics

The coordinator orchestrates the parallel execution while keeping
the interface simple for users.
"""

import time
import queue
from typing import Optional
import math
from typing import Dict, Any

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from .expansion_worker import WUUCTExpansionWorker
from .simulation_worker import SimulationWorkerPool
from .work_units import WorkUnit, SimulationResult


class WUUCT:
    """
    Main WU-UCT algorithm coordinator.
    
    This class orchestrates the parallel WU-UCT algorithm by:
    - Managing one expansion worker (tree management)
    - Managing multiple simulation workers (rollouts)
    - Coordinating communication between workers
    - Providing a simple interface for running the algorithm
    """
    
    def __init__(self, problem: OrienteeringProblem, 
                 expansion_workers: int = 1,
                 simulation_workers: int = 4,
                 exploration_constant: float = math.sqrt(2),
                 max_distance: Optional[float] = None):
        """
        Initialize the WU-UCT coordinator.
        
        Args:
            problem: The orienteering problem to solve
            expansion_workers: Number of expansion workers (must be 1 for WU-UCT)
            simulation_workers: Number of simulation workers
            exploration_constant: UCT exploration parameter
            max_distance: Maximum distance limit for simulations (optional)
            
            max_distance: Maximum distance limit for simulations (optional)
        """
        self.problem = problem
        self.expansion_workers_count = expansion_workers
        self.simulation_workers_count = simulation_workers
        self.exploration_constant = exploration_constant
        self.max_distance = max_distance        # Create expansion workers (manage the tree)
        self.expansion_workers = []
        
        # Create the simulation worker pool
        self.simulation_worker_pool = SimulationWorkerPool(simulation_workers)
        
        # Algorithm state
        self.running = False
    
    def run(self, max_iterations: int, verbose: bool = False) -> OrienteeringState:
        """
        Run the WU-UCT algorithm for the specified number of iterations.
        
        This is the main method that:
        1. Creates and starts multiple expansion workers in separate threads
        2. Starts all simulation workers
        3. Monitors progress while workers run independently
        4. Stops workers and returns the best solution found
        
        Args:
            max_iterations: Maximum number of iterations to run
            verbose: Whether to print progress information
            
        Returns:
            The best orienteering state found
        """
        self.running = True
        start_time = time.time()
        
        # Create shared queues for all workers
        shared_work_queue = queue.Queue()
        shared_result_queue = queue.Queue()
        
        # Calculate iterations per expansion worker
        iterations_per_worker = max_iterations // self.expansion_workers_count
        
        # Create and start expansion workers with shared queues
        for i in range(self.expansion_workers_count):
            worker = WUUCTExpansionWorker(
                self.problem, 
                worker_id=i,
                exploration_constant=self.exploration_constant,
                max_distance=self.max_distance,
                work_queue=shared_work_queue,
                result_queue=shared_result_queue,
                max_iterations=iterations_per_worker
            )
            self.expansion_workers.append(worker)
            worker.start()  # Start the thread
        
        # Start simulation workers with shared queues
        self.simulation_worker_pool.start_workers(shared_work_queue, shared_result_queue)
        
        try:
            if verbose:
                print(f"Starting WU-UCT with {self.expansion_workers_count} expansion workers "
                      f"and {self.simulation_workers_count} simulation workers")
            
            # Monitor progress while workers run independently
            last_iteration = 0
            while self.running and any(worker.is_alive() for worker in self.expansion_workers):
                time.sleep(1)  # Check every second
                
                # Update iteration count based on completed simulations
                current_iteration = self._count_completed_iterations()
                
                # Print progress if requested
                if verbose and current_iteration > last_iteration and current_iteration % 10000 == 0:
                    self._print_progress(current_iteration, start_time)
                    last_iteration = current_iteration
            
            # Wait for all expansion workers to complete
            for worker in self.expansion_workers:
                worker.join(timeout=1.0)
            
            # Get final iteration count
            final_iteration = self._count_completed_iterations()
            
            if verbose:
                self._print_final_statistics(final_iteration, start_time)
        
        finally:
            # Always clean up workers
            self._cleanup_workers()
        
        # Get the best solution found (use first expansion worker since they share the tree)
        best_state = None
        if self.expansion_workers:
            best_state = self.expansion_workers[0].get_best_path()
        
        if best_state is None:
            # Fallback to initial state if no solution found
            return OrienteeringState(self.problem)
        
        return best_state
    
    def _process_available_results(self):
        """Process all currently available simulation results."""
        if not self.expansion_workers:
            return
            
        # Use first expansion worker's result queue (shared by all)
        result_queue = self.expansion_workers[0].result_queue
        
        while True:
            try:
                result = result_queue.get_nowait()
                # Find which expansion worker should process this result
                # by checking the worker_id encoded in the work_id
                worker_id = result.work_id >> 16
                if worker_id < len(self.expansion_workers):
                    self.expansion_workers[worker_id].process_simulation_result(result)
            except queue.Empty:
                break
    
    def _process_remaining_results(self):
        """Process any remaining results in the queue."""
        # Wait a bit for any in-flight simulations to complete
        time.sleep(0.1)
        self._process_available_results()
    
    def _count_completed_iterations(self) -> int:
        """Count total completed iterations from all workers."""
        if not self.expansion_workers:
            return 0
        # Use first expansion worker since they all share the same tree
        stats = self.expansion_workers[0].get_statistics()
        return stats.get('root_visits', 0)
    
    def _print_progress(self, iteration: int, start_time: float):
        """Print progress information."""
        elapsed = time.time() - start_time
        if self.expansion_workers:
            stats = self.expansion_workers[0].get_statistics()
            print(f"Iteration {iteration}, "
                  f"Time: {elapsed:.1f}s, "
                  f"Nodes: {stats['nodes']}, "
                  f"Root visits: {stats['root_visits']}")
    
    def _print_final_statistics(self, iteration: int, start_time: float):
        """Print final algorithm statistics."""
        elapsed = time.time() - start_time
        
        if self.expansion_workers:
            expansion_stats = self.expansion_workers[0].get_statistics()
            worker_stats = self.simulation_worker_pool.get_total_statistics()
            
            print(f"Completed {iteration} iterations in {elapsed:.1f}s")
            print(f"Tree statistics: {expansion_stats}")
            print(f"Worker statistics: {worker_stats}")
            
            # Print individual worker performance
            for i, worker_stat in enumerate(worker_stats['individual_worker_stats']):
                print(f"Simulation worker {i}: {worker_stat['simulations_completed']} simulations")
    
    def _cleanup_workers(self):
        """Clean up all workers."""
        self.running = False
        
        # Stop expansion workers
        for worker in self.expansion_workers:
            worker.stop()
        
        # Wait for expansion workers to finish
        for worker in self.expansion_workers:
            if worker.is_alive():
                worker.join(timeout=2.0)
        
        # Stop simulation workers
        self.simulation_worker_pool.stop_workers(timeout=2.0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the current search.
        
        Returns:
            Dictionary with detailed statistics from all components
        """
        if not self.expansion_workers:
            expansion_stats = {}
        else:
            expansion_stats = self.expansion_workers[0].get_statistics()
            
        worker_stats = self.simulation_worker_pool.get_total_statistics()
        
        # Combine statistics
        combined_stats = {
            'expansion_worker': expansion_stats,
            'simulation_workers': worker_stats,
            'algorithm': {
                'running': self.running,
                'expansion_workers_count': self.expansion_workers_count,
                'simulation_workers_count': self.simulation_workers_count,
                'exploration_constant': self.exploration_constant
            }
        }
        
        # Add some convenient top-level stats
        combined_stats.update({
            'nodes': expansion_stats.get('nodes', 0),
            'root_visits': expansion_stats.get('root_visits', 0),
            'total_simulations': worker_stats.get('total_simulations', 0),
            'pending_work': expansion_stats.get('pending_work', 0)
        })
        
        return combined_stats
    
    def reset(self):
        """
        Reset the algorithm state for a new run.
        
        This clears all search progress and prepares for a fresh start.
        """
        if self.running:
            self._cleanup_workers()
        
        # Reset all expansion workers
        for expansion_worker in self.expansion_workers:
            expansion_worker.reset()
        
        # Clear the expansion workers list
        self.expansion_workers.clear()
        
        self.simulation_worker_pool.reset_all_statistics()
        self.running = False


# Convenience function for easy usage
def run_wu_uct(problem: OrienteeringProblem, 
               max_iterations: int = 100000,
               simulation_workers: int = 4,
               exploration_constant: float = math.sqrt(2),
               verbose: bool = False) -> OrienteeringState:
    """
    Convenience function to run WU-UCT with default settings.
    
    Args:
        problem: The orienteering problem to solve
        max_iterations: Maximum number of iterations
        simulation_workers: Number of simulation workers
        exploration_constant: UCT exploration parameter
        verbose: Whether to print progress
        
    Returns:
        The best solution found
    """
    wu_uct = WUUCT(problem, 
                   simulation_workers=simulation_workers,
                   exploration_constant=exploration_constant)
    
    return wu_uct.run(max_iterations=max_iterations, verbose=verbose)