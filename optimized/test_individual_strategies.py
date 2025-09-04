#!/usr/bin/env python3
"""
Quick test of individual simulation strategies
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from optimized.optimized_simulation_strategies import OptimizedSimulationStrategies
from orienteering.orienteering import OrienteeringProblem, OrienteeringState
import time

# Load problem and create initial state
# Handle both running from optimized/ directory and as module from parent
import os
if os.path.exists('../OP_Benchmark_Set/set_64_1/set_64_1_80.txt'):
    problem_file = '../OP_Benchmark_Set/set_64_1/set_64_1_80.txt'
else:
    problem_file = 'OP_Benchmark_Set/sample/sample_6_small.txt'

nodes, budget = OrienteeringProblem.load_problem(problem_file)
problem = OrienteeringProblem(nodes, budget)
initial_state = OrienteeringState(problem)

print("=== Testing Individual Simulation Strategies ===")
print(f"Problem: {len(nodes)} nodes, budget: {budget}")
print(f"Initial state: {initial_state}")
print()

# Test each strategy multiple times to see consistency
num_tests = 10

strategies = {
    "Greedy": OptimizedSimulationStrategies.greedy_simulation,
    "Epsilon-Greedy": OptimizedSimulationStrategies.epsilon_greedy_simulation,
    "Heavy (3 rollouts)": OptimizedSimulationStrategies.heavy_simulation,
    "Early Termination": OptimizedSimulationStrategies.early_termination_simulation
}

for name, strategy_func in strategies.items():
    print(f"Testing {name} Strategy:")
    rewards = []
    total_time = 0
    
    for i in range(num_tests):
        start = time.time()
        reward = strategy_func(initial_state)
        elapsed = time.time() - start
        total_time += elapsed
        rewards.append(reward)
    
    avg_reward = sum(rewards) / len(rewards)
    avg_time = total_time / num_tests
    
    print(f"  Average reward: {avg_reward:.1f}")
    print(f"  Best reward: {max(rewards)}")
    print(f"  Worst reward: {min(rewards)}")
    print(f"  Average time: {avg_time*1000:.3f}ms")
    print(f"  All rewards: {rewards}")
    print()

# Compare with random simulation (from original implementation)
print("Comparison with Random Simulation:")
import random
def random_simulation(state):
    current = state.copy()
    while not current.is_terminal():
        actions = current.get_available_actions()
        if not actions:
            break
        action = random.choice(actions)
        current = current.apply_action(action)
    return current.get_reward()

random_rewards = []
random_time = 0
for i in range(num_tests):
    start = time.time()
    reward = random_simulation(initial_state)
    elapsed = time.time() - start
    random_time += elapsed
    random_rewards.append(reward)

print(f"Random simulation average reward: {sum(random_rewards)/len(random_rewards):.1f}")
print(f"Random simulation average time: {random_time/num_tests*1000:.3f}ms")
print(f"Random simulation rewards: {random_rewards}")


# To run this test, use:
# python3 -m optimized.test_individual_strategies