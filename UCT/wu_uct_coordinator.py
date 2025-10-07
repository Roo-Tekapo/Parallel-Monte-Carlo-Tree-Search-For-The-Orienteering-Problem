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
        """
        self.problem = problem
        self.expansion_workers_count = expansion_workers
        self.simulation_workers_count = simulation_workers
        self.exploration_constant = exploration_constant
        self.max_distance = max_distance
        
        # Create expansion workers (manage the tree)
        self.expansion_workers = []
        
        # Create the simulation worker pool
        self.simulation_worker_pool = SimulationWorkerPool(simulation_workers)
        
        # Algorithm state
        self.running = False
    
    def run(self, max_iterations: int, max_time: Optional[float] = None, verbose: bool = False) -> OrienteeringState:
        """
        Run the WU-UCT algorithm for the specified number of iterations or time limit.
        
        This is the main method that:
        1. Creates and starts multiple expansion workers in separate threads
        2. Starts all simulation workers
        3. Monitors progress while workers run independently
        4. Stops workers and returns the best solution found
        
        Args:
            max_iterations: Maximum number of iterations to run
            max_time: Maximum time in seconds (optional, overrides max_iterations if specified)
            verbose: Whether to print progress information
            
        Returns:
            The best orienteering state found
        """
        self.running = True
        start_time = time.time()
        
        # Create shared queues for all workers
        shared_work_queue = queue.Queue()
        shared_result_queue = queue.Queue()
        
        # Calculate iterations per expansion worker (only if not using time limit)
        iterations_per_worker = None if max_time else max_iterations // self.expansion_workers_count
        
        # Create and start expansion workers with shared queues
        for i in range(self.expansion_workers_count):
            worker = WUUCTExpansionWorker(
                self.problem, 
                worker_id=i,
                exploration_constant=self.exploration_constant,
                max_distance=self.max_distance,
                work_queue=shared_work_queue,
                result_queue=shared_result_queue,
                max_iterations=iterations_per_worker,
                max_time=max_time
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
                # Check for time limit
                if max_time and (time.time() - start_time) >= max_time:
                    if verbose:
                        print(f"Time limit of {max_time}s reached, stopping workers...")
                    break
                
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
        """Print progress information with per-thread statistics."""
        elapsed = time.time() - start_time
        print(f"\n=== WU-UCT Progress: Iteration {iteration}, Time: {elapsed:.1f}s ===")
        
        if self.expansion_workers:
            # Print overall tree statistics from first worker (they share the tree)
            overall_stats = self.expansion_workers[0].get_statistics()
            print(f"Tree: {overall_stats['nodes']} nodes, {overall_stats['root_visits']} root visits")
            
            # Print per-thread expansion worker statistics
            print("\nExpansion Worker Thread Results:")
            total_expanded = 0
            total_simulations = 0
            for worker in self.expansion_workers:
                thread_stats = worker.get_thread_statistics()
                total_expanded += thread_stats['nodes_expanded']
                total_simulations += thread_stats['simulations_processed']
                print(f"  Worker {thread_stats['worker_id']}: "
                      f"{thread_stats['iterations']} iter, "
                      f"{thread_stats['nodes_expanded']} expanded, "
                      f"{thread_stats['simulations_processed']}/{thread_stats['simulations_requested']} sims, "
                      f"best reward: {thread_stats['best_reward']:.1f}, "
                      f"{thread_stats['iterations_per_second']:.1f} iter/s")
            
            print(f"  Total: {total_expanded} nodes expanded, {total_simulations} simulations processed")
            
            # Print simulation worker statistics
            sim_stats = self.simulation_worker_pool.get_total_statistics()
            print(f"Simulation Workers: {sim_stats['total_simulations']} completed")
    
    def _print_final_statistics(self, iteration: int, start_time: float):
        """Print final algorithm statistics with per-thread details."""
        elapsed = time.time() - start_time
        
        print(f"\n=== WU-UCT Final Results ===")
        print(f"Completed {iteration} iterations in {elapsed:.1f}s ({iteration/elapsed:.1f} iter/s)")
        
        if self.expansion_workers:
            # Overall tree statistics
            expansion_stats = self.expansion_workers[0].get_statistics()
            print(f"\nTree: {expansion_stats['nodes']} total nodes, {expansion_stats['root_visits']} root visits")
            
            # Detailed per-thread expansion worker statistics
            print(f"\nExpansion Worker Thread Performance:")
            total_expanded = 0
            total_simulations_req = 0
            total_simulations_proc = 0
            best_overall_reward = 0
            
            for worker in self.expansion_workers:
                thread_stats = worker.get_thread_statistics()
                total_expanded += thread_stats['nodes_expanded']
                total_simulations_req += thread_stats['simulations_requested']
                total_simulations_proc += thread_stats['simulations_processed']
                best_overall_reward = max(best_overall_reward, thread_stats['best_reward'])
                
                print(f"  Worker {thread_stats['worker_id']}: "
                      f"{thread_stats['iterations']:>6} iterations, "
                      f"{thread_stats['nodes_expanded']:>6} nodes expanded, "
                      f"{thread_stats['simulations_processed']:>6}/{thread_stats['simulations_requested']:>6} simulations, "
                      f"best reward: {thread_stats['best_reward']:>6.1f}, "
                      f"{thread_stats['iterations_per_second']:>6.1f} iter/s")
            
            print(f"  Total: {total_expanded} nodes expanded, {total_simulations_proc}/{total_simulations_req} simulations")
            print(f"  Best reward found: {best_overall_reward:.1f}")
            
            # Simulation worker statistics
            worker_stats = self.simulation_worker_pool.get_total_statistics()
            print(f"\nSimulation Workers: {worker_stats['total_simulations']} total completions")
            
            # Individual simulation worker performance
            for i, worker_stat in enumerate(worker_stats['individual_worker_stats']):
                sim_count = worker_stat.get('simulations_completed', 0)
                print(f"  Sim worker {i}: {sim_count} simulations")
    
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