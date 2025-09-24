"""
True WU-UCT with Specialized Workers for Orienteering Problem
Based on the WU-UCT paper: separate expansion and simulation workers
"""
import hashlib
import threading
import time
import random
import queue
from typing import Optional, Dict, Any, Tuple, List
from copy import deepcopy
import sys
import os

# Add the parent directory to path to import orienteering module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from orienteering.orienteering import OrienteeringState, OrienteeringProblem

try:
    from .wu_orienteering_node import WUOrienteeringNode
except ImportError:
    from wu_orienteering_node import WUOrienteeringNode


class SimulationTask:
    """Task for simulation workers"""
    def __init__(self, task_id: int, node: 'WUOrienteeringNode', path: List[Tuple['WUOrienteeringNode', int]]):
        self.task_id = task_id
        self.node = node
        self.path = path
        self.created_time = time.time()


class SimulationResult:
    """Result from simulation workers"""
    def __init__(self, task_id: int, reward: float, processing_time: float):
        self.task_id = task_id
        self.reward = reward
        self.processing_time = processing_time
        self.completed_time = time.time()


class WUExpansionWorker(threading.Thread):
    """Specialized worker for selection and expansion phases"""
    
    def __init__(self, worker_id: int, tree, simulation_task_queue: queue.Queue,
                 simulation_result_queue: queue.Queue, max_iterations: Optional[int] = None,
                 max_time: Optional[float] = None):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.tree = tree
        self.simulation_task_queue = simulation_task_queue
        self.simulation_result_queue = simulation_result_queue
        self.max_iterations = max_iterations
        self.max_time = max_time
        
        # Control flags
        self.running = False
        self.iterations_completed = 0
        self.start_time = 0
        self.task_id_counter = 0
        
        # Track pending tasks for this worker
        self.pending_tasks: Dict[int, SimulationTask] = {}
        
        # Random seed for worker
        seed_string = f"expansion-{worker_id}-{time.time()}-{threading.current_thread().ident}"
        seed_hash = hashlib.md5(seed_string.encode()).hexdigest()
        worker_seed = int(seed_hash[:8], 16)
        random.seed(worker_seed)
        
    def run(self):
        """Main expansion worker loop"""
        self.running = True
        self.start_time = time.time()
        
        while self.should_continue():
            try:
                # Process any completed simulation results first
                self._process_simulation_results()
                
                # Perform expansion iteration
                self._perform_expansion_iteration()
                self.iterations_completed += 1
                
                # Small delay to prevent overwhelming the simulation queue
                time.sleep(0.001)
                
            except Exception as e:
                print(f"Expansion Worker {self.worker_id} error: {e}")
                break
        
        self.running = False
    
    def _process_simulation_results(self):
        """Process completed simulation results"""
        try:
            while True:
                try:
                    result = self.simulation_result_queue.get_nowait()
                    if result.task_id in self.pending_tasks:
                        task = self.pending_tasks.pop(result.task_id)
                        # Backpropagate the result
                        self.tree._backpropagate(task.path, result.reward)
                        self.tree.simulation_count += 1
                except queue.Empty:
                    break
        except Exception as e:
            print(f"Error processing simulation results: {e}")
    
    def _perform_expansion_iteration(self):
        """Perform selection and expansion phases"""
        with self.tree.tree_lock:
            # Selection phase
            selected_node, path = self.tree._select_node()
            
            if selected_node.is_terminal_node():
                # Terminal node - backpropagate terminal reward immediately
                reward = selected_node.state.get_reward()
                self.tree._backpropagate(path, reward)
                return
            
            # Expansion phase
            expand_action = selected_node.select_expand_action()
            if expand_action is not None:
                try:
                    child_state = selected_node.state.apply_action(expand_action)
                    child_node = selected_node.add_child(expand_action, child_state)
                    path.append((child_node, expand_action))
                    
                    # Create simulation task for simulation workers
                    task_id = self._get_next_task_id()
                    task = SimulationTask(task_id, child_node, path.copy())
                    self.pending_tasks[task_id] = task
                    
                    # Add to simulation queue (non-blocking)
                    try:
                        self.simulation_task_queue.put_nowait(task)
                    except queue.Full:
                        # If queue is full, perform simulation ourselves
                        reward = self.tree._simulate(child_node)
                        self.tree._backpropagate(path, reward)
                        self.tree.simulation_count += 1
                        del self.pending_tasks[task_id]
                    
                except ValueError:
                    # Invalid action, backpropagate current reward
                    reward = selected_node.state.get_reward()
                    self.tree._backpropagate(path, reward)
    
    def _get_next_task_id(self) -> int:
        """Get next unique task ID"""
        self.task_id_counter += 1
        return (self.worker_id << 16) | self.task_id_counter  # Worker ID in high bits
    
    def should_continue(self) -> bool:
        """Check if worker should continue running"""
        if not self.running:
            return False
            
        # Check iteration limit
        if self.max_iterations and self.iterations_completed >= self.max_iterations:
            return False
            
        # Check time limit
        if self.max_time and (time.time() - self.start_time) >= self.max_time:
            return False
            
        return True
    
    def stop(self):
        """Stop the worker"""
        self.running = False
    
    def get_statistics(self) -> dict:
        """Get worker statistics"""
        elapsed_time = time.time() - self.start_time if self.start_time > 0 else 0
        return {
            'worker_id': f"expansion-{self.worker_id}",
            'type': 'expansion',
            'iterations_completed': self.iterations_completed,
            'pending_tasks': len(self.pending_tasks),
            'running': self.running,
            'elapsed_time': elapsed_time,
            'iterations_per_second': self.iterations_completed / max(elapsed_time, 0.001)
        }


class WUSimulationWorker(threading.Thread):
    """Specialized worker for simulation/rollout phases"""
    
    def __init__(self, worker_id: int, tree, simulation_task_queue: queue.Queue,
                 simulation_result_queue: queue.Queue, max_time: Optional[float] = None):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.tree = tree
        self.simulation_task_queue = simulation_task_queue
        self.simulation_result_queue = simulation_result_queue
        self.max_time = max_time
        
        # Control flags
        self.running = False
        self.simulations_completed = 0
        self.start_time = 0
        
        # Random seed for worker
        seed_string = f"simulation-{worker_id}-{time.time()}-{threading.current_thread().ident}"
        seed_hash = hashlib.md5(seed_string.encode()).hexdigest()
        worker_seed = int(seed_hash[:8], 16)
        random.seed(worker_seed)
    
    def run(self):
        """Main simulation worker loop"""
        self.running = True
        self.start_time = time.time()
        
        while self.should_continue():
            try:
                # Get simulation task (blocking with timeout)
                try:
                    task = self.simulation_task_queue.get(timeout=1.0)
                    
                    # Perform simulation
                    start_sim_time = time.time()
                    reward = self.tree._simulate(task.node)
                    processing_time = time.time() - start_sim_time
                    
                    # Create result
                    result = SimulationResult(task.task_id, reward, processing_time)
                    
                    # Return result (non-blocking)
                    try:
                        self.simulation_result_queue.put_nowait(result)
                        self.simulations_completed += 1
                    except queue.Full:
                        # If result queue is full, something is wrong - skip this result
                        print(f"Simulation worker {self.worker_id}: result queue full")
                    
                    # Mark task as done
                    self.simulation_task_queue.task_done()
                    
                except queue.Empty:
                    # No tasks available, continue
                    continue
                    
            except Exception as e:
                print(f"Simulation Worker {self.worker_id} error: {e}")
                break
        
        self.running = False
    
    def should_continue(self) -> bool:
        """Check if worker should continue running"""
        if not self.running:
            return False
            
        # Check time limit
        if self.max_time and (time.time() - self.start_time) >= self.max_time:
            return False
            
        return True
    
    def stop(self):
        """Stop the worker"""
        self.running = False
    
    def get_statistics(self) -> dict:
        """Get worker statistics"""
        elapsed_time = time.time() - self.start_time if self.start_time > 0 else 0
        return {
            'worker_id': f"simulation-{self.worker_id}",
            'type': 'simulation',
            'simulations_completed': self.simulations_completed,
            'running': self.running,
            'elapsed_time': elapsed_time,
            'simulations_per_second': self.simulations_completed / max(elapsed_time, 0.001)
        }


class WUCoordinatedSolver:
    """Coordinated solver that manages both expansion and simulation workers"""
    
    def __init__(self, tree, num_expansion_workers: int = 1, num_simulation_workers: int = 4,
                 max_queue_size: int = 1000):
        self.tree = tree
        self.num_expansion_workers = num_expansion_workers
        self.num_simulation_workers = num_simulation_workers
        
        # Create task queues
        self.simulation_task_queue = queue.Queue(maxsize=max_queue_size)
        self.simulation_result_queue = queue.Queue(maxsize=max_queue_size * 2)
        
        # Workers
        self.expansion_workers: List[WUExpansionWorker] = []
        self.simulation_workers: List[WUSimulationWorker] = []
        self.workers_running = False
    
    def solve(self, max_iterations: Optional[int] = None, max_time: Optional[float] = None,
              verbose: bool = False) -> Tuple[List[int], float, dict]:
        """Solve using coordinated WU-UCT workers"""
        if verbose:
            print(f"Starting True WU-UCT with {self.num_expansion_workers} expansion workers "
                  f"and {self.num_simulation_workers} simulation workers")
        
        start_time = time.time()
        
        # Calculate iterations per expansion worker
        iterations_per_expansion_worker = None
        if max_iterations:
            iterations_per_expansion_worker = max_iterations // self.num_expansion_workers
        
        # Start workers
        self._start_workers(iterations_per_expansion_worker, max_time)
        
        if verbose and max_time:
            self._monitor_progress(max_time, start_time)
        
        # Wait for completion
        self._wait_for_completion()
        
        # Get results
        best_path, best_reward = self.tree._extract_best_complete_path()
        
        # Collect statistics
        elapsed_time = time.time() - start_time
        stats = self._collect_statistics(elapsed_time)
        
        if verbose:
            print(f"\nTrue WU-UCT solution found:")
            print(f"Best path: {best_path}")
            print(f"Best reward: {best_reward}")
            print(f"Total time: {elapsed_time:.2f}s")
            print(f"Total simulations: {stats['total_simulations']}")
            self._print_detailed_stats(stats)
        
        return best_path, best_reward, stats
    
    def _start_workers(self, iterations_per_expansion_worker: Optional[int], max_time: Optional[float]):
        """Start all workers"""
        # Start expansion workers
        for i in range(self.num_expansion_workers):
            worker = WUExpansionWorker(
                worker_id=i,
                tree=self.tree,
                simulation_task_queue=self.simulation_task_queue,
                simulation_result_queue=self.simulation_result_queue,
                max_iterations=iterations_per_expansion_worker,
                max_time=max_time
            )
            self.expansion_workers.append(worker)
            worker.start()
        
        # Start simulation workers
        for i in range(self.num_simulation_workers):
            worker = WUSimulationWorker(
                worker_id=i,
                tree=self.tree,
                simulation_task_queue=self.simulation_task_queue,
                simulation_result_queue=self.simulation_result_queue,
                max_time=max_time
            )
            self.simulation_workers.append(worker)
            worker.start()
        
        self.workers_running = True
    
    def _wait_for_completion(self):
        """Wait for all workers to complete"""
        # Wait for expansion workers to finish
        for worker in self.expansion_workers:
            worker.join()
        
        # Stop simulation workers
        for worker in self.simulation_workers:
            worker.stop()
        
        # Wait for simulation workers to finish
        for worker in self.simulation_workers:
            worker.join()
        
        self.workers_running = False
    
    def _monitor_progress(self, max_time: float, start_time: float):
        """Monitor and print progress"""
        def monitor():
            progress_count = 0
            while self.workers_running and (time.time() - start_time) < max_time:
                time.sleep(5)  # Update every 5 seconds
                if self.workers_running:
                    stats = self.tree.get_statistics()
                    elapsed = time.time() - start_time
                    queue_size = self.simulation_task_queue.qsize()
                    result_queue_size = self.simulation_result_queue.qsize()
                    
                    print(f"Progress: {elapsed:.1f}s, Simulations: {stats['simulation_count']}, "
                          f"Best reward: {stats['best_reward']:.2f}, "
                          f"Task queue: {queue_size}, Result queue: {result_queue_size}")
                    
                    # Show detailed worker stats every 15 seconds
                    progress_count += 1
                    if progress_count % 3 == 0:
                        active_expansion = sum(1 for w in self.expansion_workers if w.is_alive())
                        active_simulation = sum(1 for w in self.simulation_workers if w.is_alive())
                        total_expansions = sum(w.iterations_completed for w in self.expansion_workers)
                        total_simulations = sum(w.simulations_completed for w in self.simulation_workers)
                        
                        print(f"  Active: {active_expansion}/{self.num_expansion_workers} expansion, "
                              f"{active_simulation}/{self.num_simulation_workers} simulation")
                        print(f"  Completed: {total_expansions} expansions, {total_simulations} simulations")
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def _collect_statistics(self, elapsed_time: float) -> dict:
        """Collect comprehensive statistics"""
        expansion_stats = [w.get_statistics() for w in self.expansion_workers]
        simulation_stats = [w.get_statistics() for w in self.simulation_workers]
        
        tree_stats = self.tree.get_statistics()
        
        total_expansions = sum(w.iterations_completed for w in self.expansion_workers)
        total_simulations = sum(w.simulations_completed for w in self.simulation_workers)
        
        return {
            'elapsed_time': elapsed_time,
            'total_simulations': tree_stats.get('simulation_count', 0),
            'total_expansions': total_expansions,
            'total_worker_simulations': total_simulations,
            'expansion_workers': len(self.expansion_workers),
            'simulation_workers': len(self.simulation_workers),
            'expansion_stats': expansion_stats,
            'simulation_stats': simulation_stats,
            'queue_final_size': self.simulation_task_queue.qsize(),
            'result_queue_final_size': self.simulation_result_queue.qsize(),
            **tree_stats
        }
    
    def _print_detailed_stats(self, stats: dict):
        """Print detailed worker statistics"""
        print(f"\nExpansion Worker Performance:")
        print(f"{'Worker':<12} {'Iterations':<12} {'Rate (it/s)':<12} {'Pending':<10} {'Time (s)':<10}")
        print("-" * 70)
        for worker_stat in stats['expansion_stats']:
            print(f"{worker_stat['worker_id']:<12} "
                  f"{worker_stat['iterations_completed']:<12} "
                  f"{worker_stat['iterations_per_second']:<12.1f} "
                  f"{worker_stat['pending_tasks']:<10} "
                  f"{worker_stat['elapsed_time']:<10.2f}")
        
        print(f"\nSimulation Worker Performance:")
        print(f"{'Worker':<15} {'Simulations':<12} {'Rate (sim/s)':<12} {'Time (s)':<10}")
        print("-" * 60)
        for worker_stat in stats['simulation_stats']:
            print(f"{worker_stat['worker_id']:<15} "
                  f"{worker_stat['simulations_completed']:<12} "
                  f"{worker_stat['simulations_per_second']:<12.1f} "
                  f"{worker_stat['elapsed_time']:<10.2f}")
        
        print(f"\nQueue Status:")
        print(f"- Final task queue size: {stats['queue_final_size']}")
        print(f"- Final result queue size: {stats['result_queue_final_size']}")
    
    def stop(self):
        """Stop all workers"""
        for worker in self.expansion_workers:
            worker.stop()
        for worker in self.simulation_workers:
            worker.stop()
        self.workers_running = False