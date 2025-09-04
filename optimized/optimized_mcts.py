"""
High-performance MCTS implementation with multiple optimization techniques
"""
import random
import math
import time
from typing import List, Optional

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from MCTS.mcts_node import MCTSNode
from .optimized_simulation_strategies import OptimizedSimulationStrategies


class OptimizedMCTS:
    def __init__(self, problem: OrienteeringProblem, iterations: int, 
                 exploration_constant: float = math.sqrt(2), 
                 epsilon: float = 0.05,
                 simulation_strategy: str = "greedy",
                 max_simulation_depth: int = None):
        self.problem = problem
        self.iterations = iterations
        self.const = exploration_constant
        self.epsilon = epsilon
        self.max_simulation_depth = max_simulation_depth
        
        # Choose simulation strategy
        self.simulation_strategies = {
            "random": self._random_simulation,
            "greedy": OptimizedSimulationStrategies.greedy_simulation,
            "epsilon_greedy": OptimizedSimulationStrategies.epsilon_greedy_simulation,
            "heavy": OptimizedSimulationStrategies.heavy_simulation,
            "early_termination": OptimizedSimulationStrategies.early_termination_simulation
        }
        self.simulate = self.simulation_strategies.get(simulation_strategy, self._random_simulation)
        
        self.root = None
        self.iteration = 0
        
        # Performance tracking
        self.stats = {
            "total_simulations": 0,
            "total_simulation_time": 0,
            "total_selection_time": 0,
            "total_expansion_time": 0,
            "total_backprop_time": 0,
            "avg_simulation_length": 0
        }

    def _random_simulation(self, state: OrienteeringState) -> float:
        """Original random simulation for comparison"""
        current = state.copy()
        steps = 0
        while not current.is_terminal():
            actions = current.get_available_actions()
            if not actions:
                break
            action = random.choice(actions)
            current = current.apply_action(action)
            steps += 1
            if self.max_simulation_depth and steps >= self.max_simulation_depth:
                break
        
        # Update average simulation length
        self.stats["avg_simulation_length"] = (
            (self.stats["avg_simulation_length"] * self.stats["total_simulations"] + steps) /
            (self.stats["total_simulations"] + 1)
        )
        return current.get_reward()

    def tree_policy(self, node: MCTSNode) -> MCTSNode:
        """Optimized tree policy with timing"""
        start_time = time.perf_counter()
        
        current = node
        while not current.state.is_terminal():
            if not current.is_fully_expanded():
                result = self.expand(current)
                self.stats["total_selection_time"] += time.perf_counter() - start_time
                return result
            elif current.children:
                current = current.uct_best_child(self.const, self.epsilon)
            else:
                break
        
        self.stats["total_selection_time"] += time.perf_counter() - start_time
        return current
    
    def expand(self, node: MCTSNode) -> MCTSNode:
        """Optimized expansion with timing"""
        start_time = time.perf_counter()
        
        if not node.untried_actions:
            self.stats["total_expansion_time"] += time.perf_counter() - start_time
            return node
            
        action = node.untried_actions.pop()
        new_state = node.state.apply_action(action)
        child_node = MCTSNode(new_state, parent=node)
        node.children.append(child_node)
        
        self.stats["total_expansion_time"] += time.perf_counter() - start_time
        return child_node

    def backpropagate(self, node: MCTSNode, reward: float):
        """Optimized backpropagation with timing"""
        start_time = time.perf_counter()
        
        current = node
        while current is not None:
            current.visits += 1
            current.total_reward += reward
            current = current.parent
        
        self.stats["total_backprop_time"] += time.perf_counter() - start_time

    def best_descendant(self, node: MCTSNode) -> MCTSNode:
        """Find best path from root using highest average reward"""
        current = node
        while current.children:
            current = max(
                current.children, 
                key=lambda c: c.total_reward / c.visits if c.visits > 0 else float("-inf")
            )
        return current

    def run(self, verbose: bool = False) -> OrienteeringState:
        """Main MCTS run with performance tracking"""
        start_time = time.perf_counter()
        
        root_state = OrienteeringState(self.problem)
        root = MCTSNode(root_state)

        for i in range(self.iterations):
            # Selection and Expansion
            leaf = self.tree_policy(root)
            
            # Simulation
            sim_start = time.perf_counter()
            reward = self.simulate(leaf.state)
            self.stats["total_simulation_time"] += time.perf_counter() - sim_start
            self.stats["total_simulations"] += 1
            
            # Backpropagation
            self.backpropagate(leaf, reward)
            
            if verbose and (i + 1) % 10000 == 0:
                print(f"Iteration {i + 1}/{self.iterations}")

        total_time = time.perf_counter() - start_time
        
        if verbose:
            self.print_performance_stats(total_time)

        best_leaf = self.best_descendant(root)
        return best_leaf.state

    def print_performance_stats(self, total_time: float):
        """Print detailed performance statistics"""
        print(f"\n=== Performance Statistics ===")
        print(f"Total runtime: {total_time:.3f}s")
        print(f"Iterations per second: {self.iterations / total_time:.0f}")
        print(f"Average simulation time: {self.stats['total_simulation_time'] / self.stats['total_simulations'] * 1000:.3f}ms")
        print(f"Average simulation length: {self.stats['avg_simulation_length']:.1f} steps")
        print(f"Time breakdown:")
        print(f"  Selection: {self.stats['total_selection_time'] / total_time * 100:.1f}%")
        print(f"  Expansion: {self.stats['total_expansion_time'] / total_time * 100:.1f}%")
        print(f"  Simulation: {self.stats['total_simulation_time'] / total_time * 100:.1f}%")
        print(f"  Backpropagation: {self.stats['total_backprop_time'] / total_time * 100:.1f}%")


class ParallelMCTS:
    """
    Multi-threaded MCTS implementation using root parallelization
    Each thread runs independent MCTS and results are combined
    """
    def __init__(self, problem: OrienteeringProblem, iterations: int, num_threads: int = 4,
                 **mcts_kwargs):
        self.problem = problem
        self.iterations = iterations
        self.num_threads = num_threads
        self.mcts_kwargs = mcts_kwargs

    def run(self, verbose: bool = False) -> OrienteeringState:
        """Run parallel MCTS using multiple processes"""
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor, as_completed
        
        iterations_per_thread = self.iterations // self.num_threads
        remaining_iterations = self.iterations % self.num_threads
        
        # Create tasks for each thread
        tasks = []
        for i in range(self.num_threads):
            thread_iterations = iterations_per_thread
            if i < remaining_iterations:
                thread_iterations += 1
            tasks.append((self.problem, thread_iterations, self.mcts_kwargs))
        
        # Run in parallel
        best_states = []
        with ProcessPoolExecutor(max_workers=self.num_threads) as executor:
            futures = [executor.submit(self._run_single_thread, task) for task in tasks]
            
            for future in as_completed(futures):
                best_states.append(future.result())
        
        # Return the best result across all threads
        best_state = max(best_states, key=lambda s: s.get_reward())
        
        if verbose:
            rewards = [s.get_reward() for s in best_states]
            print(f"Thread results: {rewards}")
            print(f"Best reward: {best_state.get_reward()}")
        
        return best_state
    
    @staticmethod
    def _run_single_thread(task):
        """Run MCTS in a single thread"""
        problem, iterations, mcts_kwargs = task
        solver = OptimizedMCTS(problem, iterations, **mcts_kwargs)
        return solver.run()


if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    # Performance comparison
    nodes, budget = OrienteeringProblem.load_problem(
        "../OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    )
    problem = OrienteeringProblem(nodes, budget)
    
    print("=== Performance Comparison ===")
    
    # Test different strategies
    strategies = ["random", "greedy", "epsilon_greedy"]
    iterations = 10000
    
    for strategy in strategies:
        print(f"\nTesting {strategy} simulation:")
        start_time = time.perf_counter()
        solver = OptimizedMCTS(problem, iterations, simulation_strategy=strategy)
        best_state = solver.run(verbose=True)
        end_time = time.perf_counter()
        
        print(f"Best path: {best_state.get_path()}")
        print(f"Total reward: {best_state.get_reward()}")
        print(f"Runtime: {end_time - start_time:.3f}s")
    
    # Test parallel version
    print(f"\nTesting parallel MCTS (4 threads):")
    start_time = time.perf_counter()
    parallel_solver = ParallelMCTS(problem, iterations, num_threads=4, simulation_strategy="greedy")
    best_state = parallel_solver.run(verbose=True)
    end_time = time.perf_counter()
    
    print(f"Best path: {best_state.get_path()}")
    print(f"Total reward: {best_state.get_reward()}")
    print(f"Runtime: {end_time - start_time:.3f}s")
