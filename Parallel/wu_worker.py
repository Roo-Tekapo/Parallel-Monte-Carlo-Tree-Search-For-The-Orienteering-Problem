"""
WU-UCT Worker implementation for parallel MCTS.
Handles expansion and simulation tasks in the WU-UCT algorithm.
"""

import threading
import copy
from typing import Any, Optional, Tuple
from MCTS.wu_uct import WUUCTNode, WUUCTSolver
from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from Parallel.synchronization import Task, TaskType, TaskResult


class WUWorker:
    """Worker class for WU-UCT expansion and simulation tasks."""
    
    def __init__(self, problem: OrienteeringProblem, worker_type: str = "both"):
        """
        Initialize WU worker.
        
        Args:
            problem: The orienteering problem instance
            worker_type: "expansion", "simulation", or "both"
        """
        self.problem = problem
        self.worker_type = worker_type
        self.local_solver = None  # Will be set if needed for simulation
        
        # Statistics
        self.expansion_count = 0
        self.simulation_count = 0
        self.total_reward = 0.0
        self.stats_lock = threading.Lock()
    
    def handle_task(self, task: Task, worker_id: int) -> Any:
        """
        Handle a task based on its type.
        
        Args:
            task: The task to handle
            worker_id: ID of the worker handling this task
            
        Returns:
            Task result data
        """
        if task.task_type == TaskType.EXPANSION:
            return self._handle_expansion_task(task, worker_id)
        elif task.task_type == TaskType.SIMULATION:
            return self._handle_simulation_task(task, worker_id)
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")
    
    def _handle_expansion_task(self, task: Task, worker_id: int) -> Tuple[WUUCTNode, int, float, bool]:
        """
        Handle expansion task: expand a node and return the result.
        
        Args:
            task: Expansion task containing (node_state, untried_actions)
            worker_id: ID of the worker
            
        Returns:
            Tuple of (new_child_node, action_taken, immediate_reward, is_terminal)
        """
        try:
            node_data = task.data
            node_state = node_data['state']
            untried_actions = node_data['untried_actions']
            task_id = node_data['task_id']
            
            if not untried_actions:
                # No actions to expand
                return None, -1, 0.0, True
            
            # Select an action to expand (random selection for now)
            import random
            action = random.choice(untried_actions)
            
            # Apply the action to get the new state
            new_state = node_state.apply_action(action)
            
            # Create new child node
            child_node = WUUCTNode(new_state)
            
            # Calculate immediate reward (difference in total reward)
            immediate_reward = new_state.get_reward() - node_state.get_reward()
            
            # Check if terminal
            is_terminal = new_state.is_terminal()
            
            # Update statistics
            with self.stats_lock:
                self.expansion_count += 1
            
            return {
                'child_node': child_node,
                'action': action,
                'immediate_reward': immediate_reward,
                'is_terminal': is_terminal,
                'task_id': task_id
            }
            
        except Exception as e:
            print(f"Expansion worker {worker_id} error: {e}")
            raise
    
    def _handle_simulation_task(self, task: Task, worker_id: int) -> float:
        """
        Handle simulation task: perform random rollout from given state.
        
        Args:
            task: Simulation task containing state to simulate from
            worker_id: ID of the worker
            
        Returns:
            Total accumulated reward from simulation
        """
        try:
            simulation_data = task.data
            initial_state = simulation_data['state']
            max_steps = simulation_data.get('max_steps', 1000)
            task_id = simulation_data['task_id']
            
            # Perform random simulation
            current_state = initial_state.copy()
            accumulated_reward = 0.0
            steps = 0
            
            while not current_state.is_terminal() and steps < max_steps:
                available_actions = current_state.get_available_actions()
                if not available_actions:
                    break
                
                # Random action selection
                import random
                action = random.choice(available_actions)
                
                # Apply action
                prev_reward = current_state.get_reward()
                current_state = current_state.apply_action(action.path[-1])
                
                # Calculate step reward
                step_reward = current_state.get_reward() - prev_reward
                accumulated_reward += step_reward
                
                steps += 1
            
            # Final reward includes the terminal state reward
            final_reward = current_state.get_reward()
            
            # Update statistics
            with self.stats_lock:
                self.simulation_count += 1
                self.total_reward += final_reward
            
            return {
                'accumulated_reward': accumulated_reward,
                'final_reward': final_reward,
                'steps_taken': steps,
                'task_id': task_id
            }
            
        except Exception as e:
            print(f"Simulation worker {worker_id} error: {e}")
            raise
    
    def get_stats(self) -> dict:
        """Get worker statistics."""
        with self.stats_lock:
            avg_reward = self.total_reward / self.simulation_count if self.simulation_count > 0 else 0.0
            return {
                'expansions': self.expansion_count,
                'simulations': self.simulation_count,
                'total_reward': self.total_reward,
                'average_reward': avg_reward
            }


# TODO: class has bug in returning path
# class AdvancedWUWorker(WUWorker):
#     """Advanced WU worker with more sophisticated simulation strategies."""
    
#     def __init__(self, problem: OrienteeringProblem, worker_type: str = "both", 
#                  simulation_strategy: str = "random"):
#         """
#         Initialize advanced WU worker.
        
#         Args:
#             problem: The orienteering problem instance
#             worker_type: "expansion", "simulation", or "both"
#             simulation_strategy: "random", "greedy", "epsilon_greedy"
#         """
#         super().__init__(problem, worker_type)
#         self.simulation_strategy = simulation_strategy
#         self.epsilon = 0.1  # For epsilon-greedy strategy
    
#     def _handle_simulation_task(self, task: Task, worker_id: int) -> float:
#         """Enhanced simulation with different strategies."""
#         try:
#             simulation_data = task.data
#             initial_state = simulation_data['state']
#             max_steps = simulation_data.get('max_steps', 1000)
#             task_id = simulation_data['task_id']
            
#             current_state = initial_state.copy()
#             accumulated_reward = 0.0
#             steps = 0
            
#             while not current_state.is_terminal() and steps < max_steps:
#                 available_actions = current_state.get_available_actions()
#                 if not available_actions:
#                     break
                
#                 # Select action based on strategy
#                 action = self._select_action(current_state, available_actions)
                
#                 # Apply action
#                 prev_reward = current_state.get_reward()
#                 current_state = current_state.apply_action(action.path[-1])
                
#                 # Calculate step reward
#                 step_reward = current_state.get_reward() - prev_reward
#                 accumulated_reward += step_reward
                
#                 steps += 1
            
#             final_reward = current_state.get_reward()
            
#             # Update statistics
#             with self.stats_lock:
#                 self.simulation_count += 1
#                 self.total_reward += final_reward
            
#             return {
#                 'accumulated_reward': accumulated_reward,
#                 'final_reward': final_reward,
#                 'steps_taken': steps,
#                 'task_id': task_id
#             }
            
#         except Exception as e:
#             print(f"Advanced simulation worker {worker_id} error: {e}")
#             raise
    
#     def _select_action(self, state: OrienteeringState, available_actions: list):
#         """Select action based on simulation strategy."""
#         import random
        
#         if self.simulation_strategy == "random":
#             return random.choice(available_actions)
        
#         elif self.simulation_strategy == "greedy":
#             # Select action that maximizes immediate reward
#             best_action = None
#             best_reward = float('-inf')
            
#             for action in available_actions:
#                 # Look ahead one step
#                 next_state = state.apply_action(action.path[-1])
#                 reward_gain = next_state.get_reward() - state.get_reward()
                
#                 if reward_gain > best_reward:
#                     best_reward = reward_gain
#                     best_action = action
            
#             return best_action if best_action else random.choice(available_actions)
        
#         elif self.simulation_strategy == "epsilon_greedy":
#             # Epsilon-greedy: random with probability epsilon, greedy otherwise
#             if random.random() < self.epsilon:
#                 return random.choice(available_actions)
#             else:
#                 return self._select_action(state, available_actions)  # Use greedy
        
#         else:
#             # Default to random
#             return random.choice(available_actions)


def create_expansion_worker_function(problem: OrienteeringProblem):
    """Create a worker function for expansion tasks."""
    worker = WUWorker(problem, "expansion")
    return worker.handle_task


def create_simulation_worker_function(problem: OrienteeringProblem, strategy: str = "random"):
    """Create a worker function for simulation tasks."""
    worker = WUWorker(problem, "simulation")
    return worker.handle_task

def create_combined_worker_function(problem: OrienteeringProblem):
    """Create a worker function that can handle both expansion and simulation."""
    worker = WUWorker(problem, "both")
    return worker.handle_task

# Uses the advanced worker with different strategies - currently has a bug with path
# def create_simulation_worker_function(problem: OrienteeringProblem, strategy: str = "random"):
#     """Create a worker function for simulation tasks."""
#     worker = AdvancedWUWorker(problem, "simulation", strategy)
#     return worker.handle_task


# def create_combined_worker_function(problem: OrienteeringProblem, strategy: str = "random"):
#     """Create a worker function that can handle both expansion and simulation."""
#     worker = AdvancedWUWorker(problem, "both", strategy)
#     return worker.handle_task