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
                 exploration_constant: float = math.sqrt(2)):
        """
        Initialize the WU-UCT coordinator.
        
        Args:
            problem: The orienteering problem to solve
            expansion_workers: Number of expansion workers (must be 1 for WU-UCT)
            simulation_workers: Number of simulation workers
            exploration_constant: UCT exploration parameter
            
        Raises:
            ValueError: If expansion_workers != 1 (WU-UCT requires exactly 1)
        """
        if expansion_workers != 1:
            raise ValueError("WU-UCT requires exactly 1 expansion worker")
        
        self.problem = problem
        self.simulation_workers_count = simulation_workers
        self.exploration_constant = exploration_constant
        
        # Create the expansion worker (manages the tree)
        self.expansion_worker = WUUCTExpansionWorker(problem, exploration_constant)
        
        # Create the simulation worker pool
        self.simulation_worker_pool = SimulationWorkerPool(simulation_workers)
        
        # Algorithm state
        self.running = False
    
    def run(self, max_iterations: int, verbose: bool = False) -> OrienteeringState:
        """
        Run the WU-UCT algorithm for the specified number of iterations.
        
        This is the main method that:
        1. Starts all simulation workers
        2. Main loop: expansion worker creates work, simulation workers process it
        3. Processes results and tracks progress
        4. Stops workers and returns the best solution found
        
        Args:
            max_iterations: Maximum number of iterations to run
            verbose: Whether to print progress information
            
        Returns:
            The best orienteering state found
        """
        self.running = True
        start_time = time.time()
        
        # Start simulation workers
        self.simulation_worker_pool.start_workers(
            self.expansion_worker.work_queue,
            self.expansion_worker.result_queue
        )
        
        try:
            iteration = 0
            
            if verbose:
                print(f"Starting WU-UCT with {self.simulation_workers_count} simulation workers")
            
            # Main algorithm loop
            while iteration < max_iterations and self.running:
                # Expansion worker creates work units
                work_unit = self.expansion_worker.selection_and_expansion()
                
                if work_unit is None:
                    # No more work available (shouldn't happen in practice)
                    if verbose:
                        print(f"No more work available at iteration {iteration}")
                    break
                
                # Send work unit to simulation workers
                self.expansion_worker.work_queue.put(work_unit)
                
                # Process any completed simulation results
                self._process_available_results()
                
                # Update iteration count based on completed simulations
                iteration = self._count_completed_iterations()
                
                # Print progress if requested
                if verbose and iteration > 0 and iteration % 10000 == 0:
                    self._print_progress(iteration, start_time)
                
                # Small delay to prevent overwhelming the system
                if self.expansion_worker.work_queue.qsize() > 1000:
                    time.sleep(0.001)
            
            # Process any remaining results
            self._process_remaining_results()
            
            if verbose:
                self._print_final_statistics(iteration, start_time)
        
        finally:
            # Always clean up workers
            self._cleanup_workers()
        
        # Get the best solution found
        best_state = self.expansion_worker.get_best_path()
        if best_state is None:
            # Fallback to initial state if no solution found
            return OrienteeringState(self.problem)
        
        return best_state
    
    def _process_available_results(self):
        """Process all currently available simulation results."""
        while True:
            try:
                result = self.expansion_worker.result_queue.get_nowait()
                self.expansion_worker.process_simulation_result(result)
            except queue.Empty:
                break
    
    def _process_remaining_results(self):
        """Process any remaining results in the queue."""
        # Wait a bit for any in-flight simulations to complete
        time.sleep(0.1)
        self._process_available_results()
    
    def _count_completed_iterations(self) -> int:
        """Count total completed iterations from all workers."""
        stats = self.expansion_worker.get_statistics()
        return stats.get('root_visits', 0)
    
    def _print_progress(self, iteration: int, start_time: float):
        """Print progress information."""
        elapsed = time.time() - start_time
        stats = self.expansion_worker.get_statistics()
        print(f"Iteration {iteration}, "
              f"Time: {elapsed:.1f}s, "
              f"Nodes: {stats['nodes']}, "
              f"Root visits: {stats['root_visits']}")
    
    def _print_final_statistics(self, iteration: int, start_time: float):
        """Print final algorithm statistics."""
        elapsed = time.time() - start_time
        expansion_stats = self.expansion_worker.get_statistics()
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
        self.simulation_worker_pool.stop_workers(timeout=2.0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the current search.
        
        Returns:
            Dictionary with detailed statistics from all components
        """
        expansion_stats = self.expansion_worker.get_statistics()
        worker_stats = self.simulation_worker_pool.get_total_statistics()
        
        # Combine statistics
        combined_stats = {
            'expansion_worker': expansion_stats,
            'simulation_workers': worker_stats,
            'algorithm': {
                'running': self.running,
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
        
        self.expansion_worker.reset()
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