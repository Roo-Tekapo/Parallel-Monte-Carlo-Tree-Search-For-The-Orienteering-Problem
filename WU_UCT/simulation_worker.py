"""
Simulation Worker for WU-UCT

Receives work units from expansion workers, performs simulations,
and asynchronously commits results back to the tree.
"""

import threading
import time
import random
from typing import Optional
from queue import Queue, Empty

from WU_UCT.wu_uct_node import WUUCTNode
from WU_UCT.expansion_worker import WorkUnit


class SimulationWorker(threading.Thread):
    """
    Simulation worker for WU-UCT algorithm.
    
    Responsibilities:
    1. Receive work units from queue
    2. Perform random simulation (no tree access needed)
    3. Asynchronously commit results via update-complete
    4. Update all nodes in path
    
    Key feature: Simulations are completely independent, no locking needed!
    Only brief atomic writes when committing results.
    """
    
    def __init__(self, worker_id: int, work_queue: Queue, 
                 stop_event: threading.Event, problem=None,
                 timeout: float = 0.1, max_distance: float = 1.42):
        """
        Initialize simulation worker.
        
        Args:
            worker_id: Unique identifier for this worker
            work_queue: Queue to receive work units from expansion workers
            stop_event: Event to signal worker to stop
            problem: Orienteering problem instance
            timeout: Queue timeout for checking stop event
            max_distance: Maximum travel distance constraint (default: 1.42)
        """
        super().__init__()
        self.worker_id = worker_id
        self.work_queue = work_queue
        self.stop_event = stop_event
        self.problem = problem
        self.timeout = timeout
        self.max_distance = max_distance
        
        self.daemon = True
        
        # Statistics
        self.simulations_completed = 0
        self.total_simulation_time = 0.0
        self.total_backprop_time = 0.0
        self.total_queue_wait_time = 0.0
        
    def run(self):
        """Main worker loop."""
        while not self.stop_event.is_set():
            try:
                # Get work unit from queue
                wait_start = time.time()
                work_unit = self.work_queue.get(timeout=self.timeout)
                self.total_queue_wait_time += time.time() - wait_start
                
                # Process the work unit
                self._process_work_unit(work_unit)
                
                self.work_queue.task_done()
                
            except Empty:
                # No work available, check if we should stop
                continue
            except Exception as e:
                print(f"Simulation worker {self.worker_id} error: {e}")
                continue
    
    def _process_work_unit(self, work_unit: WorkUnit):
        """
        Process a work unit: simulate and backpropagate.
        
        Args:
            work_unit: Work unit containing simulation task
        """
        # Phase 1: Perform simulation (completely independent, no locks!)
        sim_start = time.time()
        reward = self._simulate(work_unit.state_to_simulate)
        self.total_simulation_time += time.time() - sim_start
        
        # Phase 2: Asynchronous backpropagation (Algorithm 3: Update-Complete)
        backprop_start = time.time()
        self._backpropagate(work_unit.path, reward, work_unit.simulation_id)
        self.total_backprop_time += time.time() - backprop_start
        
        self.simulations_completed += 1
    
    def _simulate(self, state) -> float:
        """
        Perform random simulation from given state.
        
        This is completely independent - no tree access needed!
        
        Args:
            state: State to simulate from
            
        Returns:
            Reward obtained from simulation
        """
        simulation_state = self._copy_state(state)
        
        # Random rollout - continue until truly terminal
        # For no-end mode: terminal = no available actions (budget exhausted or dead-end)
        # For traditional mode: terminal = reached END node or no available actions
        max_steps = 1000  # Safety limit to prevent infinite loops
        steps = 0
        
        while not simulation_state.is_terminal() and steps < max_steps:
            available_actions = simulation_state.get_available_actions()
            
            if not available_actions:
                # No actions means terminal - let loop condition handle it
                break
            
            # Random action selection
            action = random.choice(available_actions)
            simulation_state = self._apply_action(simulation_state, action)
            
            if simulation_state is None:  # Safety check
                break
            
            steps += 1
        
        # Calculate final reward
        reward = simulation_state.reward_so_far if hasattr(simulation_state, 'reward_so_far') else 0.0
        
        # Add completion bonus/penalty - behavior depends on variant
        # Check if this is no-end variant (no required END node)
        is_no_end = hasattr(simulation_state.problem, 'is_no_end_variant') and simulation_state.problem.is_no_end_variant
        
        if is_no_end:
            # No-end mode: Only reward terminal states (budget exhausted or dead-end)
            # No penalty for non-terminal since there's no required destination
            if simulation_state.is_terminal():
                reward += 0.1  # Stronger bonus for exhausting budget
        else:
            # Traditional mode: Reward reaching END node, penalize incomplete paths
            if simulation_state.is_terminal():
                reward += 0.05  # Completion bonus (standardized)
            elif hasattr(simulation_state, 'path') and len(simulation_state.path) > 2:
                reward *= 0.8  # 20% penalty (standardized)
        
        return reward
    
    def _backpropagate(self, path: list, reward: float, simulation_id: str):
        """
        Backpropagate simulation result through the tree.
        
        This is Algorithm 3 (Update-Complete) from the paper.
        Uses brief atomic writes at each node - no long locks!
        
        Args:
            path: List of nodes from root to leaf
            reward: Simulation reward to propagate
            simulation_id: Unique identifier for this simulation
        """
        accumulated_reward = reward
        
        # Traverse path backwards (leaf to root)
        for node in reversed(path):
            # Asynchronous commit - brief atomic write only!
            accumulated_reward = node.commit_simulation_result(
                simulation_id, 
                accumulated_reward
            )
    
    def _copy_state(self, state):
        """
        Create a copy of state for simulation.
        
        Args:
            state: State to copy
            
        Returns:
            Copy of state
        """
        if hasattr(state, 'copy'):
            return state.copy()
        else:
            # For orienteering states
            if hasattr(state, 'path'):
                from WU_UCT.orienteering_adapter import OrienteeringState
                return OrienteeringState(
                    self.problem,
                    path=state.path[:],
                    cost_so_far=state.cost_so_far,
                    reward_so_far=state.reward_so_far
                )
            else:
                raise NotImplementedError("State must have copy() method or path attribute")
    
    def _apply_action(self, state, action):
        """
        Apply action to state.
        
        Args:
            state: Current state
            action: Action to apply
            
        Returns:
            New state after applying action
        """
        # Simply use the state's built-in apply_action which already handles
        # all constraints (budget, reachability to END, etc.)
        if hasattr(state, 'apply_action'):
            return state.apply_action(action)
        else:
            raise NotImplementedError("State must have apply_action method")
    
    def get_statistics(self) -> dict:
        """
        Get worker statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        avg_sim_time = (self.total_simulation_time / self.simulations_completed 
                       if self.simulations_completed > 0 else 0)
        avg_backprop_time = (self.total_backprop_time / self.simulations_completed
                            if self.simulations_completed > 0 else 0)
        avg_queue_wait = (self.total_queue_wait_time / self.simulations_completed
                         if self.simulations_completed > 0 else 0)
        
        return {
            'worker_id': self.worker_id,
            'worker_type': 'simulation',
            'simulations_completed': self.simulations_completed,
            'avg_simulation_time': avg_sim_time,
            'avg_backprop_time': avg_backprop_time,
            'avg_queue_wait_time': avg_queue_wait,
            'total_time': self.total_simulation_time + self.total_backprop_time,
        }
