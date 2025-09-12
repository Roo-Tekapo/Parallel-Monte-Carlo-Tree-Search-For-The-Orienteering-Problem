"""
WU-UCT Worker Manager implementation.
Coordinates expansion and simulation workers with the main WU-UCT algorithm.
"""

import threading
import time
from typing import Dict, List, Optional, Any
from MCTS.wu_uct import WUUCTSolver, WUUCTNode
from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from Parallel.synchronization import TaskCoordinator, Task, TaskType, TaskResult
from Parallel.wu_worker import create_expansion_worker_function, create_simulation_worker_function


class WUUCTWorkerManager:
    """
    Manager class that coordinates WU-UCT algorithm with worker pools.
    Implements the master process from the original WU-UCT paper.
    """
    
    def __init__(self, problem: OrienteeringProblem, max_steps: int = 1000,
                 expansion_workers: int = 4, simulation_workers: int = 4,
                 exploration_constant: float = 1.414, simulation_strategy: str = "random"):
        """
        Initialize WU-UCT Worker Manager.
        
        Args:
            problem: The orienteering problem to solve
            max_steps: Maximum number of MCTS iterations
            expansion_workers: Number of expansion worker threads
            simulation_workers: Number of simulation worker threads
            exploration_constant: UCT exploration parameter
            simulation_strategy: Strategy for simulation workers
        """
        self.problem = problem
        self.max_steps = max_steps
        self.exploration_constant = exploration_constant
        self.simulation_strategy = simulation_strategy
        
        # Initialize WU-UCT solver core
        self.solver = WUUCTSolver(
            problem=problem,
            iterations=max_steps,
            num_workers=expansion_workers + simulation_workers,
            exploration_constant=exploration_constant
        )
        
        # Initialize task coordinator
        self.coordinator = TaskCoordinator(expansion_workers, simulation_workers)
        
        # Task tracking
        self.pending_expansion_tasks: Dict[int, Dict] = {}
        self.pending_simulation_tasks: Dict[int, Dict] = {}
        self.completed_simulations = 0
        self.task_lock = threading.Lock()
        
        # Statistics
        self.start_time = None
        self.stats = {
            'total_expansions': 0,
            'total_simulations': 0,
            'total_time': 0.0,
            'average_simulation_time': 0.0
        }
    
    def solve(self) -> OrienteeringState:
        """
        Solve the orienteering problem using WU-UCT with worker coordination.
        
        Returns:
            Best solution found
        """
        print(f"Starting WU-UCT with {self.coordinator.expansion_pool.num_workers} expansion workers "
              f"and {self.coordinator.simulation_pool.num_workers} simulation workers")
        
        self.start_time = time.time()
        
        try:
            # Start worker pools
            expansion_worker_func = create_expansion_worker_function(self.problem)
            simulation_worker_func = create_simulation_worker_function(self.problem, self.simulation_strategy)
            
            self.coordinator.start(expansion_worker_func, simulation_worker_func)
            
            # Initialize root
            root = self.solver.initialize_root()
            
            # Main WU-UCT loop
            simulation_idx = 0
            while self.completed_simulations < self.max_steps:
                
                # Execute one WU-UCT step
                self._execute_wu_uct_step(simulation_idx)
                
                # Process completed tasks
                self._process_completed_tasks()
                
                simulation_idx += 1
                
                # Progress reporting
                if self.completed_simulations % 100 == 0:
                    self._report_progress()
            
            # Wait for remaining tasks
            self._finalize_remaining_tasks()
            
        finally:
            # Shutdown worker pools
            self.coordinator.shutdown(wait=True)
        
        # Calculate final statistics
        end_time = time.time()
        self.stats['total_time'] = end_time - self.start_time
        
        print(f"WU-UCT completed in {self.stats['total_time']:.2f} seconds")
        print(f"Total simulations: {self.completed_simulations}")
        print(f"Expansions: {self.stats['total_expansions']}")
        
        return self.solver.get_best_path()
    
    def _execute_wu_uct_step(self, sim_idx: int):
        """Execute one step of the WU-UCT algorithm."""
        root = self.solver.root
        if root is None:
            return
        
        # Selection phase - find leaf to expand
        current = root
        path = [current]
        task_id = self.solver.get_task_id()
        
        # Apply incomplete updates along selection path
        self._apply_incomplete_updates(path, task_id)
        
        # Traverse until we find an expandable node
        while not current.state.is_terminal():
            if not current.is_fully_expanded():
                # Found node to expand
                self._schedule_expansion_task(current, task_id)
                break
            elif current.children:
                # Select best child and continue
                if hasattr(current, 'select_action_wu_uct'):
                    action_idx = current.select_action_wu_uct(self.exploration_constant)
                    if action_idx is not None and action_idx < len(current.children):
                        current = current.children[action_idx]
                        path.append(current)
                        continue
                
                # Fallback: random child selection
                import random
                current = random.choice(current.children)
                path.append(current)
            else:
                break
    
    def _apply_incomplete_updates(self, path: List[WUUCTNode], task_id: int):
        """Apply incomplete updates to track unobserved samples."""
        for node in path:
            if hasattr(node, 'update_incomplete'):
                node.update_incomplete(task_id, -1)
            else:
                # Fallback for standard MCTS nodes
                node.visits += 1
    
    def _schedule_expansion_task(self, node: WUUCTNode, task_id: int):
        """Schedule an expansion task for a node."""
        if not self.coordinator.has_available_expansion_workers():
            return  # No workers available, skip for now
        
        # Prepare expansion task data
        expansion_data = {
            'state': node.state.copy(),
            'untried_actions': list(node.untried_actions) if node.untried_actions else [],
            'task_id': task_id,
            'node_id': id(node)  # For tracking
        }
        
        # Submit task
        submitted_task_id = self.coordinator.submit_expansion_task(expansion_data)
        
        # Track pending task
        with self.task_lock:
            self.pending_expansion_tasks[submitted_task_id] = {
                'node': node,
                'original_task_id': task_id,
                'timestamp': time.time()
            }
    
    def _schedule_simulation_task(self, state: OrienteeringState, task_id: int):
        """Schedule a simulation task from a given state."""
        if not self.coordinator.has_available_simulation_workers():
            return  # No workers available
        
        # Prepare simulation task data
        simulation_data = {
            'state': state.copy(),
            'task_id': task_id,
            'max_steps': 1000
        }
        
        # Submit task
        submitted_task_id = self.coordinator.submit_simulation_task(simulation_data)
        
        # Track pending task
        with self.task_lock:
            self.pending_simulation_tasks[submitted_task_id] = {
                'original_task_id': task_id,
                'timestamp': time.time()
            }
    
    def _process_completed_tasks(self):
        """Process all completed expansion and simulation tasks."""
        # Process completed expansions
        expansion_results = self.coordinator.get_completed_expansion_tasks()
        for result in expansion_results:
            self._handle_expansion_result(result)
        
        # Process completed simulations
        simulation_results = self.coordinator.get_completed_simulation_tasks()
        for result in simulation_results:
            self._handle_simulation_result(result)
    
    def _handle_expansion_result(self, result: TaskResult):
        """Handle completed expansion task."""
        if not result.success:
            print(f"Expansion task {result.task_id} failed: {result.error}")
            return
        
        with self.task_lock:
            if result.task_id not in self.pending_expansion_tasks:
                return  # Task already processed or unknown
            
            task_info = self.pending_expansion_tasks.pop(result.task_id)
            parent_node = task_info['node']
            original_task_id = task_info['original_task_id']
        
        # Extract expansion result
        expansion_result = result.result
        child_node = expansion_result['child_node']
        action = expansion_result['action']
        immediate_reward = expansion_result['immediate_reward']
        is_terminal = expansion_result['is_terminal']
        
        # Add child to parent node
        with self.solver.global_tree_lock:
            parent_node.children.append(child_node)
            child_node.parent = parent_node
            
            # Remove the action from untried actions
            if action in parent_node.untried_actions:
                parent_node.untried_actions.remove(action)
        
        # Update statistics
        self.stats['total_expansions'] += 1
        
        # If terminal, complete the update directly
        if is_terminal:
            self._complete_simulation_update(child_node, immediate_reward, original_task_id)
        else:
            # Schedule simulation from the new child
            self._schedule_simulation_task(child_node.state, original_task_id)
    
    def _handle_simulation_result(self, result: TaskResult):
        """Handle completed simulation task."""
        if not result.success:
            print(f"Simulation task {result.task_id} failed: {result.error}")
            return
        
        with self.task_lock:
            if result.task_id not in self.pending_simulation_tasks:
                return  # Task already processed or unknown
            
            task_info = self.pending_simulation_tasks.pop(result.task_id)
            original_task_id = task_info['original_task_id']
        
        # Extract simulation result
        simulation_result = result.result
        final_reward = simulation_result['final_reward']
        steps_taken = simulation_result['steps_taken']
        
        # Complete the update with simulation reward
        self._complete_simulation_update(None, final_reward, original_task_id)
        
        # Update statistics
        self.stats['total_simulations'] += 1
        self.completed_simulations += 1
    
    def _complete_simulation_update(self, node: Optional[WUUCTNode], reward: float, task_id: int):
        """Complete the WU-UCT update with simulation result."""
        # This would implement the complete update from the WU-UCT algorithm
        # For now, we'll do a simplified version
        
        # Find the path back to root for this task_id
        # In a full implementation, we'd track the exact path
        
        # Simple fallback: update root statistics
        root = self.solver.root
        if root:
            with self.solver.global_tree_lock:
                root.visits += 1
                root.total_reward += reward
                
                # If we have the specific node, update it too
                if node:
                    node.visits += 1
                    node.total_reward += reward
    
    def _finalize_remaining_tasks(self):
        """Wait for all remaining tasks to complete."""
        print("Finalizing remaining tasks...")
        
        # Wait for all tasks to complete
        self.coordinator.wait_for_all_tasks()
        
        # Process any final results
        self._process_completed_tasks()
    
    def _report_progress(self):
        """Report current progress."""
        elapsed = time.time() - self.start_time
        simulations_per_sec = self.completed_simulations / elapsed if elapsed > 0 else 0
        
        print(f"Progress: {self.completed_simulations}/{self.max_steps} simulations "
              f"({simulations_per_sec:.1f} sim/sec)")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            'wu_uct_stats': self.stats,
            'coordinator_stats': self.coordinator.get_stats(),
            'pending_tasks': {
                'expansion': len(self.pending_expansion_tasks),
                'simulation': len(self.pending_simulation_tasks)
            }
        }
