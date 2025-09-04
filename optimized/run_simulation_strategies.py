#!/usr/bin/env python3
"""
Example of how to run different simulation strategies
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from optimized import OptimizedMCTS, AdaptiveMCTS
from orienteering.orienteering import OrienteeringProblem
import time

# Load a problem
# Handle both running from optimized/ directory and as module from parent
import os
if os.path.exists('../OP_Benchmark_Set/set_64_1/set_64_1_80.txt'):
    problem_file = '../OP_Benchmark_Set/set_64_1/set_64_1_80.txt'
else:
    problem_file = 'OP_Benchmark_Set/sample/sample_6_small.txt'

nodes, budget = OrienteeringProblem.load_problem(problem_file)
problem = OrienteeringProblem(nodes, budget)

print("=== Running Different Simulation Strategies ===\n")

# 1. Greedy simulation
print("1. Greedy Simulation Strategy:")
start = time.time()
solver = OptimizedMCTS(problem, iterations=10000, simulation_strategy="greedy")
result = solver.run(verbose=True)
elapsed = time.time() - start
print(f"Result: {result.get_path()}")
print(f"Reward: {result.get_reward()}")
print(f"Time: {elapsed:.3f}s\n")

# 2. Epsilon-greedy simulation
print("2. Epsilon-Greedy Simulation Strategy:")
start = time.time()
solver = OptimizedMCTS(problem, iterations=10000, simulation_strategy="epsilon_greedy")
result = solver.run(verbose=True)
elapsed = time.time() - start
print(f"Result: {result.get_path()}")
print(f"Reward: {result.get_reward()}")
print(f"Time: {elapsed:.3f}s\n")

# 3. Heavy simulation (multiple rollouts)
print("3. Heavy Simulation Strategy:")
start = time.time()
solver = OptimizedMCTS(problem, iterations=4000, simulation_strategy="heavy")  # Fewer iterations since it's slower
result = solver.run(verbose=True)
elapsed = time.time() - start
print(f"Result: {result.get_path()}")
print(f"Reward: {result.get_reward()}")
print(f"Time: {elapsed:.3f}s\n")

# 4. Early termination simulation
print("4. Early Termination Simulation Strategy:")
start = time.time()
solver = OptimizedMCTS(problem, iterations=10000, simulation_strategy="early_termination", max_simulation_depth=15)
result = solver.run(verbose=True)
elapsed = time.time() - start
print(f"Result: {result.get_path()}")
print(f"Reward: {result.get_reward()}")
print(f"Time: {elapsed:.3f}s\n")

# 5. Random simulation (for comparison)
print("5. Random Simulation Strategy (original):")
start = time.time()
solver = OptimizedMCTS(problem, iterations=10000, simulation_strategy="random")
result = solver.run(verbose=True)
elapsed = time.time() - start
print(f"Result: {result.get_path()}")
print(f"Reward: {result.get_reward()}")
print(f"Time: {elapsed:.3f}s")


# python3 -m optimized.run_simulation_strategies