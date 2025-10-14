"""
Test if increasing exploration constant improves budget usage
while maintaining completion rate.
"""

import time
from orienteering.orienteering import OrienteeringProblem
from MCTS.mcts_base import MCTSSingleThread


def test_exploration_constant(problem_file, exploration_constant, iterations=5000, num_runs=10):
    """Test with different exploration constants."""
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
    
    completed = 0
    total_reward = 0
    total_cost = 0
    total_budget_usage = 0
    
    for _ in range(num_runs):
        solver = MCTSSingleThread(
            problem, iterations=iterations, traditional_mcts=True,
            exploration_constant=exploration_constant
        )
        best_state = solver.run()
        
        path = best_state.get_path()
        raw_reward = sum(problem.nodes[node_id].score for node_id in path)
        cost = best_state.get_cost()
        is_complete = best_state.is_terminal()
        
        if is_complete:
            completed += 1
        
        total_reward += raw_reward
        total_cost += cost
        total_budget_usage += (cost / budget) * 100
    
    completion_rate = (completed / num_runs) * 100
    avg_reward = total_reward / num_runs
    avg_budget_usage = total_budget_usage / num_runs
    
    return {
        'completion_rate': completion_rate,
        'avg_reward': avg_reward,
        'avg_budget_usage': avg_budget_usage,
        'exploration_constant': exploration_constant
    }


def main():
    print("="*80)
    print("TESTING EXPLORATION CONSTANT vs BUDGET USAGE")
    print("="*80)
    print("\nHigher exploration = more trying alternatives = higher budget usage?")
    print("Current: C=√2≈1.414 gives ~80% budget usage\n")
    
    problem_file = "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    
    # Test different exploration constants
    exploration_values = [
        (0.5, "Very Low (greedy)"),
        (0.7, "Low"),
        (1.0, "Medium-Low"),
        (1.414, "Default (√2)"),
        (1.8, "Medium-High"),
        (2.0, "High"),
        (2.5, "Very High"),
        (3.0, "Extremely High"),
    ]
    
    print(f"{'Description':<25} {'C Value':>8} {'Comp%':>7} {'Reward':>8} {'Budget%':>9}")
    print("="*80)
    
    results = []
    
    for c_value, description in exploration_values:
        result = test_exploration_constant(problem_file, c_value, iterations=5000, num_runs=10)
        results.append((description, result))
        
        print(f"{description:<25} {c_value:>8.3f} "
              f"{result['completion_rate']:>6.0f}% {result['avg_reward']:>8.1f} "
              f"{result['avg_budget_usage']:>8.1f}%")
    
    print("="*80)
    print("\nANALYSIS:")
    print("-"*80)
    
    # Find best budget usage with good completion
    good_completion = [r for r in results if r[1]['completion_rate'] >= 90]
    
    if good_completion:
        best_budget = max(good_completion, key=lambda x: x[1]['avg_budget_usage'])
        print(f"\n✓ Best Budget Usage (with ≥90% completion): {best_budget[0]}")
        print(f"   C = {best_budget[1]['exploration_constant']:.3f}")
        print(f"   Completion: {best_budget[1]['completion_rate']:.0f}%")
        print(f"   Budget Usage: {best_budget[1]['avg_budget_usage']:.1f}%")
        print(f"   Avg Reward: {best_budget[1]['avg_reward']:.1f}")
        
        # Find best reward with good completion
        best_reward = max(good_completion, key=lambda x: x[1]['avg_reward'])
        print(f"\n✓ Best Reward (with ≥90% completion): {best_reward[0]}")
        print(f"   C = {best_reward[1]['exploration_constant']:.3f}")
        print(f"   Completion: {best_reward[1]['completion_rate']:.0f}%")
        print(f"   Budget Usage: {best_reward[1]['avg_budget_usage']:.1f}%")
        print(f"   Avg Reward: {best_reward[1]['avg_reward']:.1f}")
    
    print("\n" + "="*80)
    print("CONCLUSION:")
    print("="*80)
    
    # Check if exploration constant helps
    default_result = next(r for r in results if abs(r[1]['exploration_constant'] - 1.414) < 0.01)
    best_result = max(results, key=lambda x: x[1]['avg_budget_usage'])
    
    if best_result[1]['avg_budget_usage'] > default_result[1]['avg_budget_usage'] + 5:
        print(f"\n✓ Increasing exploration constant HELPS!")
        print(f"  Recommend using C = {best_result[1]['exploration_constant']:.3f}")
    else:
        print(f"\n⚠ Exploration constant doesn't significantly affect budget usage.")
        print(f"  Issue is likely reward structure, not exploration.")
        print(f"\n  The 75-80% budget usage appears to be inherent to traditional MCTS")
        print(f"  when prioritizing completion. This may be acceptable trade-off.")


if __name__ == "__main__":
    main()
