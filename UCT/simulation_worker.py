"""
Simulation worker for WU-UCT algorithm.

Simulation workers are responsible for:
1. Receiving work units from the expansion worker
2. Performing random rollout simulations
3. Returning simulation results
4. Running independently in their own threads

These workers handle the computationally intensive simulation phase
while the expansion worker manages the tree structure.
"""

import threading
import queue
import random
from typing import TYPE_CHECKING

from orienteering.orienteering_traditional import OrienteeringState, END_NODE
from .work_units import WorkUnit, SimulationResult

if TYPE_CHECKING:
    pass


class WUUCTSimulationWorker:
    """
    Simulation worker that performs random rollouts from given states.
    
    Each simulation worker runs in its own thread and:
    - Continuously processes work units from a shared queue
    - Performs random simulations to terminal states
    - Returns results via a shared result queue
    - Tracks its own performance statistics
    """
    
    def __init__(self, worker_id: int):
        """
        Initialize a simulation worker.
        
        Args:
            worker_id: Unique identifier for this worker (for debugging/stats)
        """
        self.worker_id = worker_id
        self.simulations_completed = 0
        self.total_simulation_time = 0.0
    
    def simulate(self, state: OrienteeringState) -> float:
        """
        Perform a random simulation from the given state to a terminal state.
        
        This uses a simple random policy:
        1. While not terminal, select a random available action
        2. Apply the action to get a new state
        3. Repeat until terminal state is reached
        4. Return the final reward with completion bonus/penalty
        
        Args:
            state: The state to simulate from
            
        Returns:
            The reward obtained from the simulation
        """
        # Work with a copy to avoid modifying the original state
        current = state.copy()
        
        # Simulate until we reach a terminal state
        while not current.is_terminal():
            actions = current.get_available_actions()
            
            if not actions:
                # Dead-end: no more actions available
                break
            
            # Random action selection (pure Monte Carlo simulation)
            action = random.choice(actions)
            
            try:
                current = current.apply_action(action)
            except ValueError:
                # Invalid action (shouldn't happen but be safe)
                break
        
        # Calculate final reward with completion bonus/penalty
        self.simulations_completed += 1
        reward = current.get_reward()
        
        if current.is_terminal():
            # Completion bonus for finishing the path
            if hasattr(current.problem, 'normalize_rewards') and current.problem.normalize_rewards:
                # Meaningful bonus - 15% of typical collected reward
                # With avg node ~0.5, this is ~30% of a typical node value
                reward += 0.15
            else:
                reward += 100  # Larger bonus for unnormalized rewards
        else:
            # Penalty for incomplete paths (only if path is non-trivial)
            if len(current.path) > 2:
                if hasattr(current.problem, 'normalize_rewards') and current.problem.normalize_rewards:
                    # Moderate penalty - allows good incomplete exploration
                    reward *= 0.7  # 30% penalty
                else:
                    reward *= 0.1  # 90% penalty
        
        return reward
    
    def run(self, work_queue: queue.Queue[WorkUnit], 
            result_queue: queue.Queue[SimulationResult], 
            stop_event: threading.Event):
        """
        Main worker loop - processes work units until stopped.
        
        This method runs in its own thread and:
        1. Continuously checks for new work units
        2. Performs simulations when work is available
        3. Sends results back to the expansion worker
        4. Stops gracefully when signaled
        
        Args:
            work_queue: Queue to receive work units from
            result_queue: Queue to send results to
            stop_event: Event to signal when to stop working
        """
        while not stop_event.is_set():
            try:
                # Try to get a work unit with a short timeout
                # This allows the worker to check the stop event regularly
                work_unit = work_queue.get(timeout=0.1)
                
                # Perform the simulation
                reward = self.simulate(work_unit.state)
                
                # Create and send the result
                result = SimulationResult(work_unit.work_id, reward)
                result_queue.put(result)
                
                # Mark the work unit as done
                work_queue.task_done()
                
            except queue.Empty:
                # No work available right now, continue checking
                continue
            except Exception as e:
                # Log errors but don't crash the worker
                print(f"Simulation worker {self.worker_id} error: {e}")
                continue
    
    def get_statistics(self) -> dict:
        """
        Get statistics about this worker's performance.
        
        Returns:
            Dictionary with worker performance metrics
        """
        return {
            'worker_id': self.worker_id,
            'simulations_completed': self.simulations_completed,
            'average_simulations_per_second': self.simulations_completed / max(self.total_simulation_time, 0.001)
        }
    
    def reset_statistics(self):
        """Reset the worker's performance statistics."""
        self.simulations_completed = 0
        self.total_simulation_time = 0.0


class SimulationWorkerPool:
    """
    Helper class to manage multiple simulation workers.
    
    This makes it easier to create, start, and stop multiple workers
    as a coordinated group.
    """
    
    def __init__(self, num_workers: int):
        """
        Create a pool of simulation workers.
        
        Args:
            num_workers: Number of simulation workers to create
        """
        self.num_workers = num_workers
        self.workers = [WUUCTSimulationWorker(i) for i in range(num_workers)]
        self.worker_threads = []
        self.stop_event = threading.Event()
    
    def start_workers(self, work_queue: queue.Queue[WorkUnit], 
                     result_queue: queue.Queue[SimulationResult]):
        """
        Start all workers in their own threads.
        
        Args:
            work_queue: Queue for workers to receive work units from
            result_queue: Queue for workers to send results to
        """
        self.stop_event.clear()
        self.worker_threads = []
        
        for worker in self.workers:
            thread = threading.Thread(
                target=worker.run,
                args=(work_queue, result_queue, self.stop_event),
                name=f"SimulationWorker-{worker.worker_id}"
            )
            thread.start()
            self.worker_threads.append(thread)
    
    def stop_workers(self, timeout: float = 1.0):
        """
        Stop all workers gracefully.
        
        Args:
            timeout: Maximum time to wait for workers to stop
        """
        # Signal all workers to stop
        self.stop_event.set()
        
        # Wait for all workers to finish
        for thread in self.worker_threads:
            thread.join(timeout=timeout)
    
    def get_total_statistics(self) -> dict:
        """
        Get combined statistics from all workers.
        
        Returns:
            Dictionary with aggregated worker statistics
        """
        total_simulations = sum(worker.simulations_completed for worker in self.workers)
        
        return {
            'num_workers': self.num_workers,
            'total_simulations': total_simulations,
            'individual_worker_stats': [worker.get_statistics() for worker in self.workers]
        }
    
    def reset_all_statistics(self):
        """Reset statistics for all workers."""
        for worker in self.workers:
            worker.reset_statistics()