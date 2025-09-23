"""
WU-UCT Worker implementation for Orienteering Problem
"""
import threading
import time
import random
from typing import Optional, TYPE_CHECKING
from copy import deepcopy
import sys
import os

# Add the parent directory to path to import orienteering module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from orienteering.orienteering import OrienteeringState, OrienteeringProblem

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from wu_orienteering_tree import WUOrienteeringTree


class WUOrienteeringWorker(threading.Thread):
    """Worker thread for WU-UCT algorithm"""
    
    def __init__(self, worker_id: int, tree: 'WUOrienteeringTree', 
                 max_iterations: Optional[int] = None,
                 max_time: Optional[float] = None):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.tree = tree
        self.max_iterations = max_iterations
        self.max_time = max_time
        
        # Control flags
        self.running = False
        self.iterations_completed = 0
        self.start_time = 0
        
        # Random seed for worker
        random.seed(worker_id + int(time.time()))
        
    def run(self):
        """Main worker loop"""
        self.running = True
        self.start_time = time.time()
        
        while self.should_continue():
            try:
                # WU-UCT iteration
                self._perform_iteration()
                self.iterations_completed += 1
                
            except Exception as e:
                print(f"Worker {self.worker_id} error: {e}")
                break
        
        self.running = False
    
    def _perform_iteration(self):
        """Perform one WU-UCT iteration"""
        # Use the tree's WU-UCT iteration method
        self.tree._perform_wu_uct_iteration()
    
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
            'worker_id': self.worker_id,
            'iterations_completed': self.iterations_completed,
            'running': self.running,
            'elapsed_time': elapsed_time,
            'iterations_per_second': self.iterations_completed / max(elapsed_time, 0.001)
        }


class OrienteeringSimulationWorker:
    """Simulation worker for orienteering problem (simplified version)"""
    
    def __init__(self, worker_id: int, problem: OrienteeringProblem):
        self.worker_id = worker_id
        self.problem = problem
        
    def simulate_from_state(self, state: OrienteeringState, max_depth: int = 50) -> float:
        """
        Simulate from given state using greedy policy
        Returns the final reward
        """
        current_state = state.copy()
        steps = 0
        
        while not current_state.is_terminal() and steps < max_depth:
            actions = current_state.get_available_actions()
            if not actions:
                break
                
            # Greedy selection based on reward/distance ratio
            best_action = self._select_greedy_action(current_state, actions)
            
            if best_action is not None:
                try:
                    current_state = current_state.apply_action(best_action)
                    steps += 1
                except ValueError:
                    break
            else:
                break
                
        return current_state.get_reward()
    
    def _select_greedy_action(self, state: OrienteeringState, actions: list) -> Optional[int]:
        """Select action greedily"""
        if not actions:
            return None
            
        # Prefer END_NODE if we have some rewards
        if 1 in actions and len(state.path) > 2:  # END_NODE = 1
            return 1
        
        best_action = None
        best_ratio = -1
        current_node = state.path[-1]
        
        for action in actions:
            if action == 1:  # Skip END_NODE for now
                continue
                
            try:
                reward = state.problem.nodes[action].score
                distance = state.problem.get_distance(current_node, action)
                ratio = reward / (distance + 0.01)
                
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_action = action
            except (IndexError, ZeroDivisionError):
                continue
        
        # If no good action found, try END_NODE or random
        if best_action is None:
            if 1 in actions:
                return 1
            return random.choice(actions) if actions else None
            
        return best_action


class OrienteeringExpansionWorker:
    """Expansion worker for orienteering problem"""
    
    def __init__(self, worker_id: int, problem: OrienteeringProblem):
        self.worker_id = worker_id
        self.problem = problem
        
    def expand_node(self, state: OrienteeringState, action: int) -> tuple:
        """
        Expand a node by applying an action
        Returns: (new_state, reward, done)
        """
        try:
            new_state = state.apply_action(action)
            reward = new_state.problem.nodes[action].score
            done = new_state.is_terminal()
            
            return new_state, reward, done
            
        except ValueError as e:
            # Invalid action
            return None, 0.0, True
    
    def get_prior_probabilities(self, state: OrienteeringState) -> dict:
        """
        Calculate prior probabilities for actions based on heuristics
        """
        actions = state.get_available_actions()
        if not actions:
            return {}
            
        probs = {}
        current_node = state.path[-1]
        
        # Calculate reward/distance ratios
        for action in actions:
            if action == 1:  # END_NODE
                # Higher probability if we've collected some rewards
                probs[action] = 2.0 if len(state.path) > 2 else 0.5
            else:
                try:
                    reward = state.problem.nodes[action].score
                    distance = state.problem.get_distance(current_node, action)
                    probs[action] = reward / (distance + 0.01)
                except (IndexError, ZeroDivisionError):
                    probs[action] = 0.1
        
        # Normalize probabilities
        total = sum(probs.values())
        if total > 0:
            for action in probs:
                probs[action] /= total
        else:
            # Uniform distribution fallback
            prob = 1.0 / len(actions)
            probs = {action: prob for action in actions}
            
        return probs