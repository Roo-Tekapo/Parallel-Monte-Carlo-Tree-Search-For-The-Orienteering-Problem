#!/usr/bin/env python3
"""
Performance comparison between MCTS base implementation and UCT single-thread.
This script runs both algorithms on the same problem and compares their results.
"""

import time
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orienteering.orienteering import OrienteeringProblem
from MCTS.mcts_base import MCTSSingleThread
from UCT.uct_single_thread import UCTSingleThread


def run_comparison(problem_file, iterations=1000, num_runs=5):
    """
    Compare MCTS base vs UCT single-thread performance.
    
    Args:
        problem_file: Path to problem file
        iterations: Number of MCTS iterations per run
        num_runs: Number of test runs for averaging
    """
    print(f"Loading problem: {problem_file}")
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget)
    
    print(f"Problem: {len(nodes)} nodes, budget={budget}")
    print(f"Running {num_runs} tests with {iterations} iterations each\n")
    
    # Results storage
    mcts_results = []
    uct_results = []
    
    for run in range(num_runs):
        print(f"Run {run + 1}/{num_runs}")
        
        # Test MCTS Base
        print("  Testing MCTS Base...")
        mcts_solver = MCTSSingleThread(problem, iterations=iterations)
        start_time = time.time()
        mcts_state = mcts_solver.run()
        mcts_time = time.time() - start_time
        
        mcts_result = {
            'reward': mcts_state.get_reward(),
            'cost': mcts_state.get_cost(),
            'path_length': len(mcts_state.get_path()),
            'time': mcts_time,
            'path': mcts_state.get_path()
        }
        mcts_results.append(mcts_result)
        print(f"    Reward: {mcts_result['reward']:.2f}, Time: {mcts_time:.3f}s")
        
        # Test UCT Single Thread
        print("  Testing UCT Single Thread...")
        uct_solver = UCTSingleThread(problem, iterations=iterations)
        start_time = time.time()
        uct_state = uct_solver.run()
        uct_time = time.time() - start_time
        
        uct_result = {
            'reward': uct_state.get_reward(),
            'cost': uct_state.get_cost(),
            'path_length': len(uct_state.get_path()),
            'time': uct_time,
            'path': uct_state.get_path()
        }
        uct_results.append(uct_result)
        print(f"    Reward: {uct_result['reward']:.2f}, Time: {uct_time:.3f}s")
        print()
    
    # Calculate statistics
    def calculate_stats(results, name):
        rewards = [r['reward'] for r in results]
        times = [r['time'] for r in results]
        costs = [r['cost'] for r in results]
        path_lengths = [r['path_length'] for r in results]
        
        print(f"{name} Results:")
        print(f"  Average Reward: {sum(rewards) / len(rewards):.2f} (±{(max(rewards) - min(rewards)) / 2:.2f})")
        print(f"  Best Reward: {max(rewards):.2f}")
        print(f"  Average Time: {sum(times) / len(times):.3f}s")
        print(f"  Average Cost: {sum(costs) / len(costs):.2f}")
        print(f"  Average Path Length: {sum(path_lengths) / len(path_lengths):.1f}")
        
        # Show best path
        best_idx = rewards.index(max(rewards))
        best_path = results[best_idx]['path']
        print(f"  Best Path: {best_path}")
        
        return {
            'avg_reward': sum(rewards) / len(rewards),
            'max_reward': max(rewards),
            'avg_time': sum(times) / len(times),
            'rewards': rewards,
            'times': times
        }
    
    print("=" * 60)
    mcts_stats = calculate_stats(mcts_results, "MCTS Base")
    print()
    uct_stats = calculate_stats(uct_results, "UCT Single Thread")
    print()
    
    # Comparison
    print("COMPARISON:")
    reward_diff = uct_stats['avg_reward'] - mcts_stats['avg_reward']
    time_diff = uct_stats['avg_time'] - mcts_stats['avg_time']
    
    print(f"  Reward difference (UCT - MCTS): {reward_diff:+.2f}")
    print(f"  Time difference (UCT - MCTS): {time_diff:+.3f}s")
    
    if abs(reward_diff) > 0.5:
        winner = "UCT" if reward_diff > 0 else "MCTS"
        print(f"  🏆 {winner} performs significantly better in reward")
    else:
        print(f"  ⚖️  Similar performance in reward")
    
    if abs(time_diff) > 0.1:
        faster = "UCT" if time_diff < 0 else "MCTS"
        print(f"  ⚡ {faster} is faster")
    else:
        print(f"  ⏱️  Similar execution time")


if __name__ == "__main__":
    # Test on different problem sizes
    test_problems = [
        "OP_Benchmark_Set/set_64_1/set_64_1_80.txt",
        "OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt",
        "OP_Benchmark_Set/set_100_1/set_100_1_75.txt"
    ]
    
    for problem_file in test_problems:
        if os.path.exists(problem_file):
            print(f"\n{'='*80}")
            print(f"TESTING: {problem_file}")
            print('='*80)
            run_comparison(problem_file, iterations=5000, num_runs=3)
        else:
            print(f"❌ Problem file not found: {problem_file}")