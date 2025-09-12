"""
Synchronization utilities for WU-UCT parallel MCTS implementation.
Provides thread-safe communication and coordination between workers.
"""

import threading
import queue
import time
from typing import Any, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """Types of tasks in WU-UCT."""
    EXPANSION = "expansion"
    SIMULATION = "simulation"
    COMPLETE = "complete"
    TERMINATE = "terminate"


@dataclass
class Task:
    """Represents a task for workers."""
    task_type: TaskType
    task_id: int
    data: Any
    worker_id: Optional[int] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class TaskResult:
    """Represents the result of a completed task."""
    task_id: int
    worker_id: int
    result: Any
    success: bool = True
    error: Optional[str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class WorkerPool:
    """Thread pool for managing WU-UCT workers."""
    
    def __init__(self, num_workers: int):
        self.num_workers = num_workers
        self.workers: List[threading.Thread] = []
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.worker_status: Dict[int, str] = {}  # 'idle', 'busy', 'terminated'
        self.stop_event = threading.Event()
        self.stats_lock = threading.Lock()
        self.worker_stats: Dict[int, Dict[str, Any]] = {}
        
        # Initialize worker status
        for i in range(num_workers):
            self.worker_status[i] = 'idle'
            self.worker_stats[i] = {
                'tasks_completed': 0,
                'total_time': 0.0,
                'errors': 0
            }
    
    def start_workers(self, worker_function):
        """Start all worker threads."""
        self.workers = []
        for worker_id in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(worker_id, worker_function),
                name=f"Worker-{worker_id}"
            )
            worker.start()
            self.workers.append(worker)
    
    def _worker_loop(self, worker_id: int, worker_function):
        """Main loop for each worker thread."""
        while not self.stop_event.is_set():
            try:
                # Get task from queue (timeout to check stop event)
                task = self.task_queue.get(timeout=0.1)
                
                if task.task_type == TaskType.TERMINATE:
                    break
                
                # Update worker status
                with self.stats_lock:
                    self.worker_status[worker_id] = 'busy'
                
                # Execute task
                start_time = time.time()
                try:
                    result = worker_function(task, worker_id)
                    task_result = TaskResult(
                        task_id=task.task_id,
                        worker_id=worker_id,
                        result=result,
                        success=True
                    )
                except Exception as e:
                    task_result = TaskResult(
                        task_id=task.task_id,
                        worker_id=worker_id,
                        result=None,
                        success=False,
                        error=str(e)
                    )
                    with self.stats_lock:
                        self.worker_stats[worker_id]['errors'] += 1
                
                end_time = time.time()
                
                # Update statistics
                with self.stats_lock:
                    self.worker_status[worker_id] = 'idle'
                    self.worker_stats[worker_id]['tasks_completed'] += 1
                    self.worker_stats[worker_id]['total_time'] += (end_time - start_time)
                
                # Return result
                self.result_queue.put(task_result)
                self.task_queue.task_done()
                
            except queue.Empty:
                continue  # Check stop event and retry
            except Exception as e:
                print(f"Worker {worker_id} unexpected error: {e}")
        
        # Mark worker as terminated
        with self.stats_lock:
            self.worker_status[worker_id] = 'terminated'
    
    def submit_task(self, task: Task) -> bool:
        """Submit a task to the worker pool."""
        if self.stop_event.is_set():
            return False
        
        self.task_queue.put(task)
        return True
    
    def get_result(self, timeout: Optional[float] = None) -> Optional[TaskResult]:
        """Get a completed task result."""
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_available_workers(self) -> int:
        """Get number of idle workers."""
        with self.stats_lock:
            return sum(1 for status in self.worker_status.values() if status == 'idle')
    
    def get_busy_workers(self) -> int:
        """Get number of busy workers."""
        with self.stats_lock:
            return sum(1 for status in self.worker_status.values() if status == 'busy')
    
    def is_busy(self) -> bool:
        """Check if any workers are busy."""
        return self.get_busy_workers() > 0
    
    def wait_for_completion(self, timeout: Optional[float] = None):
        """Wait for all submitted tasks to complete."""
        self.task_queue.join()
    
    def shutdown(self, wait: bool = True):
        """Shutdown the worker pool."""
        # Signal stop to all workers
        self.stop_event.set()
        
        # Send terminate tasks
        for _ in range(self.num_workers):
            self.task_queue.put(Task(TaskType.TERMINATE, -1, None))
        
        if wait:
            # Wait for all workers to finish
            for worker in self.workers:
                worker.join()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker pool statistics."""
        with self.stats_lock:
            total_tasks = sum(stats['tasks_completed'] for stats in self.worker_stats.values())
            total_time = sum(stats['total_time'] for stats in self.worker_stats.values())
            total_errors = sum(stats['errors'] for stats in self.worker_stats.values())
            
            return {
                'total_workers': self.num_workers,
                'idle_workers': self.get_available_workers(),
                'busy_workers': self.get_busy_workers(),
                'total_tasks_completed': total_tasks,
                'total_execution_time': total_time,
                'total_errors': total_errors,
                'average_task_time': total_time / total_tasks if total_tasks > 0 else 0,
                'worker_stats': dict(self.worker_stats)
            }


class TaskCoordinator:
    """Coordinates task scheduling and result collection for WU-UCT."""
    
    def __init__(self, expansion_workers: int, simulation_workers: int):
        self.expansion_pool = WorkerPool(expansion_workers)
        self.simulation_pool = WorkerPool(simulation_workers)
        
        self.task_id_counter = 0
        self.task_id_lock = threading.Lock()
        
        # Track pending tasks
        self.pending_expansion_tasks: Dict[int, Task] = {}
        self.pending_simulation_tasks: Dict[int, Task] = {}
        self.pending_lock = threading.Lock()
    
    def generate_task_id(self) -> int:
        """Generate unique task ID."""
        with self.task_id_lock:
            self.task_id_counter += 1
            return self.task_id_counter
    
    def start(self, expansion_worker_func, simulation_worker_func):
        """Start all worker pools."""
        self.expansion_pool.start_workers(expansion_worker_func)
        self.simulation_pool.start_workers(simulation_worker_func)
    
    def submit_expansion_task(self, data: Any) -> int:
        """Submit an expansion task."""
        task_id = self.generate_task_id()
        task = Task(TaskType.EXPANSION, task_id, data)
        
        with self.pending_lock:
            self.pending_expansion_tasks[task_id] = task
        
        self.expansion_pool.submit_task(task)
        return task_id
    
    def submit_simulation_task(self, data: Any) -> int:
        """Submit a simulation task."""
        task_id = self.generate_task_id()
        task = Task(TaskType.SIMULATION, task_id, data)
        
        with self.pending_lock:
            self.pending_simulation_tasks[task_id] = task
        
        self.simulation_pool.submit_task(task)
        return task_id
    
    def get_completed_expansion_tasks(self, timeout: Optional[float] = None) -> List[TaskResult]:
        """Get all completed expansion tasks."""
        results = []
        while True:
            result = self.expansion_pool.get_result(timeout=0.001)
            if result is None:
                break
            
            # Remove from pending
            with self.pending_lock:
                self.pending_expansion_tasks.pop(result.task_id, None)
            
            results.append(result)
        
        return results
    
    def get_completed_simulation_tasks(self, timeout: Optional[float] = None) -> List[TaskResult]:
        """Get all completed simulation tasks."""
        results = []
        while True:
            result = self.simulation_pool.get_result(timeout=0.001)
            if result is None:
                break
            
            # Remove from pending
            with self.pending_lock:
                self.pending_simulation_tasks.pop(result.task_id, None)
            
            results.append(result)
        
        return results
    
    def has_available_expansion_workers(self) -> bool:
        """Check if expansion workers are available."""
        return self.expansion_pool.get_available_workers() > 0
    
    def has_available_simulation_workers(self) -> bool:
        """Check if simulation workers are available."""
        return self.simulation_pool.get_available_workers() > 0
    
    def wait_for_all_tasks(self, timeout: Optional[float] = None):
        """Wait for all submitted tasks to complete."""
        self.expansion_pool.wait_for_completion()
        self.simulation_pool.wait_for_completion()
    
    def shutdown(self, wait: bool = True):
        """Shutdown all worker pools."""
        self.expansion_pool.shutdown(wait)
        self.simulation_pool.shutdown(wait)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            'expansion_pool': self.expansion_pool.get_stats(),
            'simulation_pool': self.simulation_pool.get_stats(),
            'pending_expansion_tasks': len(self.pending_expansion_tasks),
            'pending_simulation_tasks': len(self.pending_simulation_tasks)
        }
