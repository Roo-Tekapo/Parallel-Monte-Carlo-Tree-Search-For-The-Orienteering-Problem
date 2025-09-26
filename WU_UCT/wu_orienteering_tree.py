"""
WU-UCT Tree implementation for Orienteering Problem
"""
import hashlib
import math
import random
import threading
import time
import logging
import gc
from typing import List, Optional, Tuple
from copy import deepcopy
import sys
import os

# Add the parent directory to path to import orienteering module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from orienteering.orienteering import OrienteeringProblem, OrienteeringState

# Handle both relative and absolute imports
try:
    from .wu_orienteering_node import WUOrienteeringNode
except ImportError:
    from wu_orienteering_node import WUOrienteeringNode


class WUOrienteeringTree:
    """WU-UCT Tree for Orienteering Problem"""
    
    def __init__(self, problem: OrienteeringProblem, max_steps: int = 1000, 
                 max_depth: int = 20, max_width: int = 10, gamma: float = 1.0,
                 expansion_worker_num: int = 4, simulation_worker_num: int = 8):
        self.problem = problem
        self.max_steps = max_steps
        self.max_depth = max_depth
        self.max_width = max_width
        self.gamma = gamma
        self.expansion_worker_num = expansion_worker_num
        self.simulation_worker_num = simulation_worker_num
        
        # Initialize root
        root_state = OrienteeringState(problem)
        self.root_node = WUOrienteeringNode(root_state, tree=self)
        
        # Global lock for tree modifications
        self.tree_lock = threading.RLock()
        
        # Initialize random seed for better exploration diversity
        # Use a combination of time and problem characteristics for unique seeding
        seed_string = f"{time.time()}-{len(problem.nodes)}-{problem.budget}-{threading.current_thread().ident}"
        seed_hash = hashlib.md5(seed_string.encode()).hexdigest()
        tree_seed = int(seed_hash[:8], 16)  # Use first 8 hex chars as seed
        random.seed(tree_seed)
        
        # Statistics
        self.simulation_count = 0
        self.global_saving_idx = 0
        
        # Task tracking for parallel execution
        self.expansion_task_recorder = dict()
        self.unscheduled_expansion_tasks = list()
        self.simulation_task_recorder = dict()
        self.unscheduled_simulation_tasks = list()
        
        # Logging setup
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"WU_UCT_Orienteering_{simulation_worker_num}.log")
        
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def simulate_single_move(self, state: OrienteeringState) -> int:
        """
        Plan a single move using WU-UCT algorithm
        Returns the best action to take
        """
        # Clear previous state
        self._reset_for_new_move(state)
        
        # Perform WU-UCT simulations
        for step in range(self.max_steps):
            self._perform_wu_uct_iteration()
            
            if step % 100 == 0:
                logging.info(f"WU-UCT step {step}, simulations: {self.simulation_count}")
        
        # Return best action
        best_action = self.root_node.max_utility_action()
        if best_action is None:
            # Fallback to available actions if no utility computed
            available = self.root_node.state.get_available_actions()
            best_action = available[0] if available else 1  # Default to END_NODE
        
        logging.info(f"Selected action: {best_action}")
        return best_action
    
    def _reset_for_new_move(self, state: OrienteeringState):
        """Reset tree state for a new move"""
        # Create new root
        self.root_node = WUOrienteeringNode(state, tree=self)
        self.simulation_count = 0
        self.global_saving_idx = 0
        
        # Clear task trackers
        self.expansion_task_recorder.clear()
        self.unscheduled_expansion_tasks.clear()
        self.simulation_task_recorder.clear()
        self.unscheduled_simulation_tasks.clear()
        
        gc.collect()
    
    def _perform_wu_uct_iteration(self):
        """Perform one iteration of WU-UCT algorithm"""
        # Selection phase
        selected_node, path = self._select_node()
        
        if selected_node.is_terminal_node():
            # Terminal node - backpropagate terminal reward
            reward = selected_node.state.get_reward()
            self._backpropagate(path, reward)
            return
        
        # Expansion phase
        expand_action = selected_node.select_expand_action()
        if expand_action is not None:
            try:
                child_state = selected_node.state.apply_action(expand_action)
                child_node = selected_node.add_child(expand_action, child_state)
                path.append((child_node, expand_action))
                
                # Simulation phase
                simulation_reward = self._simulate(child_node)
                
                # Backpropagation phase
                self._backpropagate(path, simulation_reward)
                
            except ValueError:
                # Invalid action, backpropagate current reward
                reward = selected_node.state.get_reward()
                self._backpropagate(path, reward)
        else:
            # No more actions to expand, but still simulate from current node
            # This ensures continuous exploration even when tree is "full"
            simulation_reward = self._simulate(selected_node)
            self._backpropagate(path, simulation_reward)
    
    def _select_node(self) -> Tuple[WUOrienteeringNode, List[Tuple[WUOrienteeringNode, int]]]:
        """
        Select a node for expansion using UCT policy
        Returns: (selected_node, path_with_actions)
        """
        current = self.root_node
        path = [(current, None)]  # (node, action_to_reach_node)
        depth = 0
        
        while not current.is_terminal_node() and depth < self.max_depth:
            if not current.is_fully_expanded():
                # Node can be expanded
                return current, path
            
            # Select best child using UCT
            action = current.select_action()
            if action is None or action not in current.children:
                break
                
            current = current.children[action]
            path.append((current, action))
            depth += 1
        
        return current, path
    
    def _simulate(self, node: WUOrienteeringNode) -> float:
        """
        Simulate from the given node to a terminal state
        Using random simulation like MCTS base for better exploration
        """
        current_state = node.state.copy()
        
        while not current_state.is_terminal():
            actions = current_state.get_available_actions()
            if not actions:
                # Dead-end: return current reward with small penalty
                self.simulation_count += 1
                return current_state.get_reward() * 0.8  # 20% penalty for not reaching end
            
            # Pure random action selection (like MCTS base)
            action = random.choice(actions)
            try:
                current_state = current_state.apply_action(action)
            except ValueError:
                # Invalid action, break out
                break
        
        self.simulation_count += 1
        return current_state.get_reward()
    
    def _select_greedy_action(self, state: OrienteeringState, actions: List[int]) -> Optional[int]:
        """Select action greedily based on reward/distance ratio with minimal random tie-breaking"""
        if not actions:
            return None
            
        # Prefer going to END if we have collected some rewards and budget is running low
        if 1 in actions:
            current_cost = sum(state.problem.get_distance(state.path[i], state.path[i+1]) 
                             for i in range(len(state.path)-1))
            remaining_budget = state.problem.budget - current_cost
            
            # Go to end if budget is running low or we have a decent path length
            if remaining_budget < 10 or len(state.path) > 8:
                return 1
        
        # Calculate reward/distance ratios for all actions
        action_ratios = []
        current_node = state.path[-1]
        
        for action in actions:
            if action == 1:  # END_NODE - handle separately above
                continue
                
            try:
                reward = state.problem.nodes[action].score
                distance = state.problem.get_distance(current_node, action)
                ratio = reward / (distance + 0.01)  # Small epsilon to avoid division by zero
                action_ratios.append((action, ratio))
            except (IndexError, ZeroDivisionError):
                continue
        
        if not action_ratios:
            return actions[0] if actions else None
        
        # Sort by ratio (best first)
        action_ratios.sort(key=lambda x: x[1], reverse=True)
        
        # If there are ties among top actions, break ties randomly
        best_ratio = action_ratios[0][1]
        best_actions = [action for action, ratio in action_ratios if abs(ratio - best_ratio) < 0.001]
        
        if len(best_actions) > 1:
            return random.choice(best_actions)  # Random tie-breaking
        else:
            return action_ratios[0][0]  # Single best action
    
    def _backpropagate(self, path: List[Tuple[WUOrienteeringNode, int]], reward: float):
        """Backpropagate reward up the tree"""
        discounted_reward = reward
        
        for i in reversed(range(len(path))):
            node, action = path[i]
            
            with self.tree_lock:
                node.visit_count += 1
                node.total_reward += discounted_reward
                
                # Update action-specific statistics if this isn't the root
                if action is not None and i > 0:
                    parent_node = path[i-1][0]
                    if action in parent_node.children_visit_count:
                        parent_node.children_visit_count[action] += 1
                        parent_node.Q_values[action] += discounted_reward
                        parent_node.children_completed_visit_count[action] += 1
            
            discounted_reward *= self.gamma
    
    def get_best_path(self) -> List[int]:
        """Get the best path found so far"""
        with self.tree_lock:
            if not self.root_node.children:
                return self.root_node.get_path()
            
            # Find child with highest average reward
            best_child = None
            best_score = -float('inf')
            
            for action, child in self.root_node.children.items():
                if child.visit_count > 0:
                    score = child.get_average_reward()
                    if score > best_score:
                        best_score = score
                        best_child = child
            
            if best_child is None:
                return self.root_node.get_path()
            
            # Follow the best path down the tree
            current = best_child
            while current.children:
                best_child_action = None
                best_child_score = -float('inf')
                
                for action, child in current.children.items():
                    if child.visit_count > 0:
                        score = child.get_average_reward()
                        if score > best_child_score:
                            best_child_score = score
                            best_child_action = action
                
                if best_child_action is not None:
                    current = current.children[best_child_action]
                else:
                    break
            
            return current.get_path()
    
    def get_statistics(self) -> dict:
        """Get tree statistics"""
        with self.tree_lock:
            # Get best reward from complete paths (consistent with final output)
            try:
                _, best_complete_reward = self._extract_best_complete_path()
            except:
                best_complete_reward = 0.0
            
            return {
                'simulation_count': self.simulation_count,
                'root_visits': self.root_node.visit_count,
                'root_children': len(self.root_node.children),
                'best_reward': best_complete_reward
            }
    
    def solve_complete_problem(self, max_iterations: int = 10000, 
                             verbose: bool = False) -> Tuple[List[int], float, dict]:
        """
        Solve the complete orienteering problem by finding the best complete path
        Returns: (best_path, best_reward, statistics)
        """
        start_time = time.time()
        
        if verbose:
            print(f"Starting WU-UCT solver for orienteering problem")
            print(f"Budget: {self.problem.budget}, Nodes: {len(self.problem.nodes)}")
        
        # Set up for finding complete solutions
        self.max_steps = max_iterations
        
        # Run MCTS to find the best complete path
        for iteration in range(max_iterations):
            self._perform_wu_uct_iteration()
            
            if iteration % 1000 == 0 and verbose:
                stats = self.get_statistics()
                print(f"Iteration {iteration}, simulations: {self.simulation_count}, "
                      f"best_reward: {stats.get('best_reward', 0):.2f}")
        
        # Find the best complete path (one that ends at END_NODE)
        best_path, best_reward = self._extract_best_complete_path()
        
        elapsed_time = time.time() - start_time
        
        stats = {
            'elapsed_time': elapsed_time,
            'total_iterations': max_iterations,
            'final_reward': best_reward,
            'path_length': len(best_path),
            'iterations_per_second': max_iterations / max(elapsed_time, 0.001),
            'simulation_count': self.simulation_count
        }
        
        if verbose:
            print(f"\nFinal solution:")
            print(f"Path: {best_path}")
            print(f"Reward: {best_reward}")
            print(f"Time: {elapsed_time:.2f}s")
        
        return best_path, best_reward, stats
    
    def _extract_best_complete_path(self) -> Tuple[List[int], float]:
        """Extract the best complete path that ends at END_NODE"""
        
        def find_complete_paths(node, current_path):
            """Recursively find all complete paths (ending at END_NODE)"""
            complete_paths = []
            
            if node.state.is_terminal():
                # This is a complete path
                complete_paths.append((current_path[:], node.state.get_reward()))
                return complete_paths
            
            # Look through children for complete paths
            for action, child in node.children.items():
                if child.visit_count > 0:
                    child_paths = find_complete_paths(child, current_path + [action])
                    complete_paths.extend(child_paths)
            
            return complete_paths
        
        with self.tree_lock:
            # Find all complete paths in the tree
            complete_paths = find_complete_paths(self.root_node, [0])
            
            if complete_paths:
                # Return the path with highest reward
                best_path, best_reward = max(complete_paths, key=lambda x: x[1])
                return best_path, best_reward
            
            # No complete paths found, try to construct one
            return self._construct_best_path_to_end()
    
    def _construct_best_path_to_end(self) -> Tuple[List[int], float]:
        """Construct the best path to END_NODE when no complete paths exist in tree"""
        try:
            # Start with empty state
            current_state = OrienteeringState(self.problem)
            path = [0]  # Start at node 0
            
            # Use greedy strategy to build path to end
            while not current_state.is_terminal():
                actions = current_state.get_available_actions()
                if not actions:
                    break
                
                # Prefer END_NODE if available
                if 1 in actions:
                    current_state = current_state.apply_action(1)
                    path.append(1)
                    break
                
                # Otherwise choose best reward/distance ratio
                best_action = self._select_greedy_action(current_state, actions)
                if best_action is not None:
                    current_state = current_state.apply_action(best_action)
                    path.append(best_action)
                else:
                    break
            
            # If we didn't reach END_NODE, try to add it
            if not current_state.is_terminal():
                actions = current_state.get_available_actions()
                if 1 in actions:
                    current_state = current_state.apply_action(1)
                    path.append(1)
            
            return path, current_state.get_reward()
            
        except Exception:
            # Fallback: minimal valid path
            return [0, 1], 0.0