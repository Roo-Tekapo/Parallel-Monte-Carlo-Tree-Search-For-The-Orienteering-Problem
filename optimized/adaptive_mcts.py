"""
Advanced MCTS optimizations: early stopping, adaptive parameters, and progressive strategies
"""
import math
import time
from typing import List, Tuple
from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from .optimized_mcts import OptimizedMCTS


class AdaptiveMCTS(OptimizedMCTS):
    """
    MCTS with adaptive parameters and early stopping criteria
    """
    def __init__(self, problem: OrienteeringProblem, max_iterations: int, 
                 time_limit: float = None,
                 convergence_threshold: float = 0.001,
                 convergence_window: int = 1000,
                 adaptive_exploration: bool = True,
                 **kwargs):
        super().__init__(problem, max_iterations, **kwargs)
        self.max_iterations = max_iterations
        self.time_limit = time_limit
        self.convergence_threshold = convergence_threshold
        self.convergence_window = convergence_window
        self.adaptive_exploration = adaptive_exploration
        
        # Tracking for convergence detection
        self.best_rewards_history: List[float] = []
        self.initial_exploration_constant = self.const

    def has_converged(self) -> bool:
        """Check if the search has converged"""
        if len(self.best_rewards_history) < self.convergence_window:
            return False
        
        recent_rewards = self.best_rewards_history[-self.convergence_window:]
        reward_variance = self._calculate_variance(recent_rewards)
        
        return reward_variance < self.convergence_threshold

    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values"""
        if len(values) < 2:
            return float('inf')
        
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)

    def update_exploration_constant(self, iteration: int):
        """Adaptively reduce exploration as search progresses"""
        if not self.adaptive_exploration:
            return
        
        # Reduce exploration constant over time (more exploitation later)
        progress = iteration / self.max_iterations
        self.const = self.initial_exploration_constant * (1 - 0.5 * progress)

    def run(self, verbose: bool = False) -> OrienteeringState:
        """Run adaptive MCTS with early stopping"""
        start_time = time.perf_counter()
        
        root_state = OrienteeringState(self.problem)
        root = self.create_root_node(root_state)
        
        for i in range(self.max_iterations):
            # Check time limit
            if self.time_limit and (time.perf_counter() - start_time) > self.time_limit:
                if verbose:
                    print(f"Stopped due to time limit at iteration {i}")
                break
            
            # Update exploration parameter
            self.update_exploration_constant(i)
            
            # Standard MCTS iteration
            leaf = self.tree_policy(root)
            reward = self.simulate(leaf.state)
            self.backpropagate(leaf, reward)
            
            # Track best reward for convergence detection
            if i % 100 == 0:  # Check every 100 iterations
                current_best = self.get_current_best_reward(root)
                self.best_rewards_history.append(current_best)
                
                # Check convergence
                if self.has_converged():
                    if verbose:
                        print(f"Converged at iteration {i}")
                    break
            
            if verbose and (i + 1) % 10000 == 0:
                current_best = self.get_current_best_reward(root)
                print(f"Iteration {i + 1}: Best reward = {current_best:.1f}, "
                      f"Exploration = {self.const:.3f}")

        total_time = time.perf_counter() - start_time
        
        if verbose:
            self.print_performance_stats(total_time)
            print(f"Final exploration constant: {self.const:.3f}")

        best_leaf = self.best_descendant(root)
        return best_leaf.state

    def create_root_node(self, root_state):
        """Create root node - can be overridden for custom initialization"""
        from MCTS.mcts_node import MCTSNode
        return MCTSNode(root_state)

    def get_current_best_reward(self, root) -> float:
        """Get the current best reward from the root's children"""
        if not root.children:
            return 0.0
        
        best_child = max(
            root.children,
            key=lambda c: c.total_reward / c.visits if c.visits > 0 else float("-inf")
        )
        return best_child.total_reward / best_child.visits if best_child.visits > 0 else 0.0


class ProgressiveMCTS:
    """
    Progressive MCTS that starts with fewer iterations and increases based on problem complexity
    """
    def __init__(self, problem: OrienteeringProblem, base_iterations: int = 1000,
                 max_iterations: int = 100000, **kwargs):
        self.problem = problem
        self.base_iterations = base_iterations
        self.max_iterations = max_iterations
        self.kwargs = kwargs

    def estimate_problem_complexity(self) -> int:
        """Estimate problem complexity to determine appropriate iteration count"""
        num_nodes = self.problem.num_nodes
        budget_ratio = self.problem.budget / self._estimate_max_path_length()
        
        # Simple heuristic: more nodes and higher budget ratio = more complex
        complexity_factor = math.log(num_nodes) * budget_ratio
        iterations = int(self.base_iterations * complexity_factor)
        
        return min(max(iterations, self.base_iterations), self.max_iterations)

    def _estimate_max_path_length(self) -> float:
        """Rough estimate of maximum possible path length"""
        # Calculate diameter of the problem (max distance between any two nodes)
        max_dist = 0
        for i in range(self.problem.num_nodes):
            for j in range(i + 1, self.problem.num_nodes):
                dist = self.problem.get_distance(i, j)
                max_dist = max(max_dist, dist)
        return max_dist * self.problem.num_nodes  # Worst case: visit all nodes

    def run(self, verbose: bool = False) -> OrienteeringState:
        """Run progressive MCTS with adaptive iteration count"""
        iterations = self.estimate_problem_complexity()
        
        if verbose:
            print(f"Estimated problem complexity: {iterations} iterations")
        
        solver = AdaptiveMCTS(self.problem, iterations, **self.kwargs)
        return solver.run(verbose=verbose)


if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    # Test adaptive and progressive strategies
    nodes, budget = OrienteeringProblem.load_problem(
        "../OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    )
    problem = OrienteeringProblem(nodes, budget)
    
    print("=== Testing Adaptive MCTS ===")
    
    # Test adaptive MCTS with time limit
    solver = AdaptiveMCTS(
        problem, 
        max_iterations=50000,
        time_limit=5.0,  # 5 second time limit
        simulation_strategy="greedy",
        adaptive_exploration=True
    )
    
    start_time = time.perf_counter()
    best_state = solver.run(verbose=True)
    end_time = time.perf_counter()
    
    print(f"Best path: {best_state.get_path()}")
    print(f"Total reward: {best_state.get_reward()}")
    print(f"Runtime: {end_time - start_time:.3f}s")
    
    print("\n=== Testing Progressive MCTS ===")
    
    # Test progressive MCTS
    progressive_solver = ProgressiveMCTS(
        problem,
        base_iterations=1000,
        max_iterations=20000,
        simulation_strategy="greedy"
    )
    
    start_time = time.perf_counter()
    best_state = progressive_solver.run(verbose=True)
    end_time = time.perf_counter()
    
    print(f"Best path: {best_state.get_path()}")
    print(f"Total reward: {best_state.get_reward()}")
    print(f"Runtime: {end_time - start_time:.3f}s")
