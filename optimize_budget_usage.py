"""
Find optimal end bonus that achieves BOTH:
1. High completion rate (>95%)
2. High budget usage (>85%)

The current 0.30 bonus achieves 94% completion but only 80% budget usage.
We need to lower the bonus slightly to encourage more exploration.
"""

import time
import statistics
from MCTS.mcts_base import MCTSSingleThread
from orienteering.orienteering import OrienteeringProblem


class MCTSWithCustomRewards(MCTSSingleThread):
    """MCTS with customizable end node rewards."""
    
    def __init__(self, problem, iterations, exploration_constant=1.414, epsilon=0.0, 
                 traditional_mcts=True, soft_end_bias=False, bias_decay_factor=10.0,
                 normalized_end_bonus=0.15, normalized_penalty=0.7):
        super().__init__(problem, iterations, exploration_constant, epsilon,
                        traditional_mcts, soft_end_bias, bias_decay_factor)
        self.normalized_end_bonus = normalized_end_bonus
        self.normalized_penalty = normalized_penalty
    
    def simulate(self, state) -> float:
        """Override simulate with custom reward bonuses."""
        import random
        from orienteering.orienteering import END_NODE
        
        current = state.copy()
        max_simulation_steps = 1000
        steps = 0
        
        while not current.is_terminal() and steps < max_simulation_steps:
            steps += 1
            actions = current.get_available_actions(traditional_mcts=self.traditional_mcts)
            if not actions:
                break
            else:
                if self.soft_end_bias:
                    action = self._choose_biased_action(current, actions)
                else:
                    action = random.choice(actions)
                current = current.apply_action(action, traditional_mcts=self.traditional_mcts)
        
        reward = current.get_reward()
        
        if self.problem.normalize_rewards:
            if current.is_terminal():
                reward += self.normalized_end_bonus  # CUSTOMIZABLE
            elif len(current.path) > 2:
                reward *= self.normalized_penalty    # CUSTOMIZABLE
        else:
            if current.is_terminal():
                reward += 100
            elif len(current.path) > 2:
                reward *= 0.1
        
        return reward


def test_bonus_setting(problem_file, bonus, penalty, iterations=5000, num_runs=10):
    """Test a specific bonus/penalty setting."""
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
    
    completed = 0
    total_reward = 0
    total_cost = 0
    total_budget_usage = 0
    
    for _ in range(num_runs):
        solver = MCTSWithCustomRewards(
            problem, iterations=iterations, traditional_mcts=True,
            normalized_end_bonus=bonus, normalized_penalty=penalty
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
        'bonus': bonus,
        'penalty': penalty
    }


def main():
    print("="*70)
    print("OPTIMIZING FOR COMPLETION RATE + BUDGET USAGE")
    print("="*70)
    print("\nGoal: Find bonus that achieves >95% completion AND >85% budget usage")
    print("Current problem: 0.30 bonus gives 94% completion but only 80% budget usage\n")
    
    problem_file = "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    
    # Test different bonus values from 0.15 to 0.30
    # Lower bonus = more exploration = higher budget usage (but lower completion)
    # Higher bonus = less exploration = lower budget usage (but higher completion)
    
    test_configs = [
        # (bonus, penalty, description)
        (0.15, 0.7, "Original Default"),
        (0.18, 0.7, "Slight Increase"),
        (0.20, 0.7, "Low-Medium"),
        (0.22, 0.7, "Medium"),
        (0.25, 0.7, "Medium-High"),
        (0.27, 0.7, "High"),
        (0.30, 0.7, "Current Setting"),
        
        # Try with stronger penalties too
        (0.20, 0.6, "Medium bonus + Stronger penalty"),
        (0.22, 0.6, "Medium bonus + Stronger penalty"),
        (0.25, 0.5, "Medium-High bonus + Strong penalty"),
    ]
    
    print(f"{'Description':<35} {'Bonus':>6} {'Penalty':>8} {'Comp%':>7} {'Reward':>8} {'Budget%':>9}")
    print("="*90)
    
    results = []
    
    for bonus, penalty, description in test_configs:
        result = test_bonus_setting(problem_file, bonus, penalty, iterations=5000, num_runs=10)
        results.append((description, result))
        
        print(f"{description:<35} {bonus:>6.2f} {penalty:>8.1f}x "
              f"{result['completion_rate']:>6.0f}% {result['avg_reward']:>8.1f} "
              f"{result['avg_budget_usage']:>8.1f}%")
    
    print("="*90)
    print("\nANALYSIS:")
    print("-"*90)
    
    # Find configurations that meet both criteria
    good_configs = []
    for desc, result in results:
        if result['completion_rate'] >= 90 and result['avg_budget_usage'] >= 85:
            good_configs.append((desc, result))
    
    if good_configs:
        print("\n✓ Configurations meeting BOTH criteria (>90% completion, >85% budget):")
        for desc, result in good_configs:
            print(f"  • {desc}: {result['completion_rate']:.0f}% completion, "
                  f"{result['avg_budget_usage']:.1f}% budget, "
                  f"{result['avg_reward']:.1f} reward")
        
        # Recommend the one with best balance
        best = max(good_configs, key=lambda x: x[1]['avg_reward'])
        print(f"\n🏆 RECOMMENDED: {best[0]}")
        print(f"   Bonus: {best[1]['bonus']:.2f}, Penalty: {best[1]['penalty']:.1f}x")
        print(f"   Completion: {best[1]['completion_rate']:.0f}%")
        print(f"   Budget Usage: {best[1]['avg_budget_usage']:.1f}%")
        print(f"   Avg Reward: {best[1]['avg_reward']:.1f}")
    else:
        print("\n⚠ No configuration met both criteria perfectly.")
        print("   Finding best trade-offs...\n")
        
        # Find best completion rate
        best_completion = max(results, key=lambda x: x[1]['completion_rate'])
        print(f"Best Completion Rate: {best_completion[0]}")
        print(f"  {best_completion[1]['completion_rate']:.0f}% completion, "
              f"{best_completion[1]['avg_budget_usage']:.1f}% budget\n")
        
        # Find best budget usage with reasonable completion
        reasonable_completion = [r for r in results if r[1]['completion_rate'] >= 85]
        if reasonable_completion:
            best_budget = max(reasonable_completion, key=lambda x: x[1]['avg_budget_usage'])
            print(f"Best Budget Usage (with >85% completion): {best_budget[0]}")
            print(f"  {best_budget[1]['completion_rate']:.0f}% completion, "
                  f"{best_budget[1]['avg_budget_usage']:.1f}% budget")
    
    print("\n" + "="*90)
    print("HOW TO APPLY:")
    print("="*90)
    print("\nModify MCTS/mcts_base.py, line ~218:")
    print("  Change: reward += 0.30")
    print("  To:     reward += <YOUR_CHOSEN_BONUS>")
    print("\nAnd optionally line ~222:")
    print("  Change: reward *= 0.7")
    print("  To:     reward *= <YOUR_CHOSEN_PENALTY>")


if __name__ == "__main__":
    main()
