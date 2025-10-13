#!/usr/bin/env python3
"""
Detailed comparison of simulation strategies between MCTS Base and UCT Single Thread.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from MCTS.mcts_base import MCTSSingleThread
from UCT.uct_single_thread import UCTSingleThread


def analyze_simulation_differences():
    """Analyze how the different simulation penalties affect performance."""
    
    # Load test problem
    nodes, budget = OrienteeringProblem.load_problem("OP_Benchmark_Set/set_64_1/set_64_1_80.txt")
    problem = OrienteeringProblem(nodes, budget)
    
    print("SIMULATION PENALTY ANALYSIS")
    print("="*50)
    print(f"Problem: {len(nodes)} nodes, budget={budget}\n")
    
    # Test different penalty rates by modifying simulation methods
    class MCTSWithCustomPenalty(MCTSSingleThread):
        def __init__(self, problem, iterations, penalty_rate=0.5):
            super().__init__(problem, iterations)
            self.penalty_rate = penalty_rate
            
        def simulate(self, state):
            # Copy the simulation but with custom penalty
            current = state.copy()
            max_simulation_steps = 1000
            steps = 0
            
            while not current.is_terminal() and steps < max_simulation_steps:
                steps += 1
                actions = current.get_available_actions()
                if not actions:
                    current_node = current.path[-1]
                    if current_node != 0:  # END_NODE
                        cost_to_end = current.problem.get_distance(current_node, 0)
                        if current.cost_so_far + cost_to_end <= current.problem.budget:
                            try:
                                current = current.apply_action(0)
                                break
                            except ValueError:
                                pass
                    return current.get_reward() * self.penalty_rate
                
                import random
                action = random.choice(actions)
                current = current.apply_action(action)
            return current.get_reward()
    
    # Test different penalty rates
    penalty_rates = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    iterations = 2000
    
    print("Testing different dead-end penalty rates:")
    print("(Lower penalty = harsher punishment for incomplete paths)\n")
    
    for penalty in penalty_rates:
        rewards = []
        print(f"Penalty Rate: {penalty} (MCTS Base uses 0.5, UCT uses 0.8)")
        
        for run in range(3):
            solver = MCTSWithCustomPenalty(problem, iterations, penalty)
            result = solver.run()
            reward = result.get_reward()
            rewards.append(reward)
            print(f"  Run {run+1}: {reward}")
        
        avg_reward = sum(rewards) / len(rewards)
        print(f"  Average: {avg_reward:.1f}\n")
    
    print("\nCOMPARISON WITH STANDARD IMPLEMENTATIONS:")
    print("-" * 50)
    
    # Standard MCTS Base
    mcts_rewards = []
    for run in range(3):
        solver = MCTSSingleThread(problem, iterations)
        result = solver.run()
        mcts_rewards.append(result.get_reward())
    
    # Standard UCT
    uct_rewards = []
    for run in range(3):
        solver = UCTSingleThread(problem, iterations)
        result = solver.run()
        uct_rewards.append(result.get_reward())
    
    print(f"MCTS Base (0.5 penalty): {sum(mcts_rewards)/len(mcts_rewards):.1f}")
    print(f"UCT Single Thread (0.8 penalty): {sum(uct_rewards)/len(uct_rewards):.1f}")
    
    penalty_diff = 0.8 - 0.5
    reward_diff = sum(uct_rewards)/len(uct_rewards) - sum(mcts_rewards)/len(mcts_rewards)
    
    print(f"\nPenalty difference: {penalty_diff:+.1f}")
    print(f"Reward difference: {reward_diff:+.1f}")
    
    if abs(reward_diff) > 10:
        print(f"🔍 Penalty rate appears to significantly impact performance!")
    else:
        print(f"🤔 Penalty rate has moderate impact - other factors more important")


if __name__ == "__main__":
    analyze_simulation_differences()