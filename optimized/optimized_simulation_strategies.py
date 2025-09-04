"""
Optimized simulation strategies for MCTS to improve speed and quality
"""
import random
import math
from orienteering.orienteering import OrienteeringState


class OptimizedSimulationStrategies:
    
    @staticmethod
    def greedy_simulation(state: OrienteeringState) -> float:
        """
        Greedy simulation: always choose the action with highest reward/cost ratio
        Much faster than random and often better quality
        """
        current = state.copy()
        while not current.is_terminal():
            actions = current.get_available_actions()
            if not actions:
                break
            
            # If END_NODE is available and we have collected some reward, consider taking it
            if 1 in actions and len(current.path) > 2:  # END_NODE = 1, and we've visited some nodes
                # Calculate if we should end now or continue
                current_efficiency = current.get_reward() / max(current.get_cost(), 0.01)
                if current_efficiency > 5:  # Threshold for ending early
                    current = current.apply_action(1)
                    break
            
            # Choose action with best reward/distance ratio
            best_action = None
            best_ratio = -1
            current_node = current.path[-1]
            
            for action in actions:
                if action == 1:  # END_NODE - consider but don't prioritize too early
                    if len(current.path) > 3:  # Only after visiting a few nodes
                        best_action = action
                        best_ratio = float('inf')  # High priority if we have some path
                    continue
                    
                reward = current.problem.nodes[action].score
                distance = current.problem.get_distance(current_node, action)
                ratio = reward / (distance + 0.01)  # Small epsilon to avoid division by zero
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_action = action
            
            if best_action is not None:
                current = current.apply_action(best_action)
            else:
                break
        return current.get_reward()
    
    @staticmethod
    def epsilon_greedy_simulation(state: OrienteeringState, epsilon: float = 0.2) -> float:
        """
        Mix of greedy and random for better exploration/exploitation balance
        """
        current = state.copy()
        while not current.is_terminal():
            actions = current.get_available_actions()
            if not actions:
                break
            
            if random.random() < epsilon:
                # Random choice
                action = random.choice(actions)
            else:
                # Greedy choice
                best_action = None
                best_ratio = -1
                current_node = current.path[-1]
                
                for action in actions:
                    if action == 1:  # END_NODE
                        best_action = action
                        break
                    reward = current.problem.nodes[action].score
                    distance = current.problem.get_distance(current_node, action)
                    ratio = reward / (distance + 0.01)
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_action = action
                action = best_action
            
            if action is not None:
                current = current.apply_action(action)
            else:
                break
        return current.get_reward()
    
    @staticmethod
    def heavy_simulation(state: OrienteeringState, num_rollouts: int = 3) -> float:
        """
        Multiple rollouts from the same state, return average
        More accurate but slower
        """
        total_reward = 0
        for _ in range(num_rollouts):
            total_reward += OptimizedSimulationStrategies.greedy_simulation(state)
        return total_reward / num_rollouts
    
    @staticmethod
    def early_termination_simulation(state: OrienteeringState, max_depth: int = 10) -> float:
        """
        Limit simulation depth to avoid very long rollouts
        """
        current = state.copy()
        depth = 0
        while not current.is_terminal() and depth < max_depth:
            actions = current.get_available_actions()
            if not actions:
                break
            action = random.choice(actions)
            current = current.apply_action(action)
            depth += 1
        return current.get_reward()
