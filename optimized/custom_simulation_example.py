#!/usr/bin/env python3
"""
Example of using simulation strategies directly with your existing MCTS
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from MCTS.mcts_base import MCTSSingleThread
from optimized.optimized_simulation_strategies import OptimizedSimulationStrategies
from orienteering.orienteering import OrienteeringProblem, OrienteeringState
import time

# Create a custom MCTS that uses optimized simulation
class CustomOptimizedMCTS(MCTSSingleThread):
    def __init__(self, problem, iterations, simulation_strategy="greedy"):
        super().__init__(problem, iterations)
        self.simulation_strategy = simulation_strategy
        
        # Map strategy names to functions
        self.strategies = {
            "greedy": OptimizedSimulationStrategies.greedy_simulation,
            "epsilon_greedy": OptimizedSimulationStrategies.epsilon_greedy_simulation,
            "heavy": OptimizedSimulationStrategies.heavy_simulation,
            "early_termination": OptimizedSimulationStrategies.early_termination_simulation
        }
    
    def simulate(self, state: OrienteeringState) -> float:
        """Override the simulate method to use optimized strategies"""
        if self.simulation_strategy in self.strategies:
            return self.strategies[self.simulation_strategy](state)
        else:
            # Fall back to original random simulation
            return super().simulate(state)

# Example usage
if __name__ == "__main__":
    # Load problem
    # Handle both running from optimized/ directory and as module from parent
    import os
    if os.path.exists('../OP_Benchmark_Set/set_64_1/set_64_1_80.txt'):
        problem_file = '../OP_Benchmark_Set/set_64_1/set_64_1_80.txt'
    else:
        problem_file = 'OP_Benchmark_Set/sample/sample_6_small.txt'
        print(f"Warning: Could not find set_64_1_80.txt, using {problem_file} instead")
    
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget)
    
    print("=== Custom MCTS with Optimized Simulation ===")
    print(f"Problem: {len(nodes)} nodes, budget: {budget}")
    print(f"File: {problem_file}")
    print()
    
    # Use more iterations for the larger problem
    iterations = 10000 if "set_64_1" in problem_file else 3000
    print(f"Running {iterations} iterations per strategy...\n")
    
    strategies = ["greedy", "epsilon_greedy", "heavy", "early_termination"]
    
    for strategy in strategies:
        print(f"Testing {strategy} strategy:")
        start = time.time()
        solver = CustomOptimizedMCTS(problem, iterations=3000, simulation_strategy=strategy)
        result = solver.run()
        elapsed = time.time() - start
        
        print(f"  Path: {result.get_path()}")
        print(f"  Reward: {result.get_reward()}")
        print(f"  Time: {elapsed:.3f}s\n")

# To run this example, use:
# python3 -m optimized.custom_simulation_example