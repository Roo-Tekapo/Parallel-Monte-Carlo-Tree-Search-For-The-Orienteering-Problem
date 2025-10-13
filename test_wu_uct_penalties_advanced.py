#!/usr/bin/env python3
"""
Advanced test for WU-UCT penalty/bonus parameter tuning.
This version monkey-patches the simulation method to test different configurations.
"""

from orienteering.orienteering import OrienteeringProblem
from Simple_WU.simple_wu_coordinator import SimpleWUUCT
from Simple_WU.simple_wu_worker import SimpleWUWorker
import time
import types

def create_custom_simulation(penalty_mult, completion_bonus):
    """Create a custom simulation method with specific penalty/bonus values"""
    
    def simulation(self, state):
        """Modified simulation with custom penalty/bonus"""
        from orienteering.orienteering import OrienteeringState
        import random
        
        start_time = time.time()
        
        # Copy the state for simulation
        simulation_state = state.copy()
        
        max_steps = 1000
        steps = 0
        
        # Random playout
        while not simulation_state.is_terminal() and steps < max_steps:
            steps += 1
            actions = simulation_state.get_available_actions()
            
            if not actions:
                break
            
            action = random.choice(actions)
            simulation_state = simulation_state.apply_action(action)
            
        # Calculate final reward with CUSTOM completion bonus/penalty
        reward = simulation_state.reward_so_far
        
        if simulation_state.is_terminal():
            # Completion bonus
            if self.problem.normalize_rewards:
                reward += completion_bonus  # CUSTOM VALUE
            else:
                reward += 100
        else:
            # Penalty for incomplete paths
            if len(simulation_state.path) > 2:
                if self.problem.normalize_rewards:
                    reward *= penalty_mult  # CUSTOM VALUE
                else:
                    reward *= 0.1
        
        # Update timing statistics
        self.total_simulation_time += time.time() - start_time
        
        return reward
    
    return simulation

def test_penalty_bonus_configurations():
    """Test different penalty/bonus configurations for parallel WU-UCT"""
    
    # Load test problem
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    
    print("=" * 85)
    print("WU-UCT PENALTY/BONUS PARAMETER SENSITIVITY ANALYSIS")
    print("=" * 85)
    print(f"\nProblem: 121 nodes, budget={budget}")
    print("Workers: 4 parallel workers")
    print("Iterations: 5000 per configuration")
    print("Method: Monkey-patching simulation with custom penalties")
    print()
    
    # Define test configurations
    configs = [
        # Very harsh
        (0.3, 0.01, "Very Harsh (original)"),
        (0.4, 0.05, "Harsh"),
        
        # Moderate
        (0.5, 0.10, "Moderate"),
        (0.6, 0.12, "Moderate+"),
        (0.7, 0.15, "Standard (current)"),
        
        # Lenient
        (0.75, 0.18, "Lenient-"),
        (0.8, 0.20, "Lenient"),
        (0.85, 0.25, "Very Lenient"),
        
        # Minimal penalty
        (0.9, 0.30, "Minimal Penalty"),
    ]
    
    results = []
    
    for penalty_mult, completion_bonus, description in configs:
        print(f"\n{'─'*85}")
        print(f"Testing: {description}")
        print(f"  Penalty multiplier: {penalty_mult}× ({(1-penalty_mult)*100:.0f}% penalty)")
        print(f"  Completion bonus: +{completion_bonus}")
        print(f"{'─'*85}")
        
        try:
            # Create problem
            problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
            
            # Create WU-UCT coordinator with the problem
            coordinator = SimpleWUUCT(
                problem=problem,
                num_workers=4
            )
            
            # Monkey-patch the simulation method for all workers
            custom_sim = create_custom_simulation(penalty_mult, completion_bonus)
            for worker in coordinator.workers:
                worker.simulation = types.MethodType(custom_sim, worker)
            
            # Run
            start_time = time.time()
            solution = coordinator.run(max_iterations=5000, max_time=60.0)
            elapsed = time.time() - start_time
            
            # Calculate results
            raw_reward = sum(problem.nodes[node_id].score for node_id in solution.path)
            normalized_reward = solution.reward_so_far
            path_length = len(solution.path)
            cost = solution.cost_so_far
            valid = solution.is_terminal()
            iterations = sum(worker.iterations_completed for worker in coordinator.workers)
            
            result = {
                'penalty_mult': penalty_mult,
                'penalty_pct': (1-penalty_mult)*100,
                'completion_bonus': completion_bonus,
                'description': description,
                'raw_reward': raw_reward,
                'normalized_reward': normalized_reward,
                'path_length': path_length,
                'cost': cost,
                'budget_usage': (cost / budget) * 100,
                'valid': valid,
                'iterations': iterations,
                'time': elapsed,
                'reward_per_node': raw_reward / path_length if path_length > 0 else 0,
                'success': True
            }
            
            # Print results
            status = "✓" if valid else "⚠"
            print(f"\n{status} Results:")
            print(f"    Raw reward: {raw_reward}")
            print(f"    Normalized: {normalized_reward:.4f}")
            print(f"    Path: {path_length} nodes")
            print(f"    Cost: {cost:.2f} / {budget} ({cost/budget*100:.1f}% used)")
            print(f"    Valid: {'Yes' if valid else 'No (INCOMPLETE)'}")
            print(f"    Iterations: {iterations}")
            print(f"    Time: {elapsed:.2f}s")
            print(f"    Reward/node: {raw_reward/path_length:.1f}")
            
        except Exception as e:
            print(f"\n✗ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            result = {
                'penalty_mult': penalty_mult,
                'penalty_pct': (1-penalty_mult)*100,
                'completion_bonus': completion_bonus,
                'description': description,
                'raw_reward': 0,
                'normalized_reward': 0,
                'path_length': 0,
                'cost': 0,
                'budget_usage': 0,
                'valid': False,
                'iterations': 0,
                'time': 0,
                'reward_per_node': 0,
                'success': False,
                'error': str(e)
            }
        
        results.append(result)
    
    # Generate summary
    print("\n\n" + "=" * 85)
    print("SUMMARY TABLE")
    print("=" * 85)
    print()
    
    # Filter and sort
    successful = [r for r in results if r['success']]
    valid_solutions = [r for r in successful if r['valid']]
    
    if not successful:
        print("⚠️  No successful runs!")
        return results
    
    # Find best
    best_valid = max(valid_solutions, key=lambda x: x['raw_reward']) if valid_solutions else None
    best_overall = max(successful, key=lambda x: x['raw_reward'])
    
    # Print table header
    print(f"{'Penalty':<9} {'Bonus':<7} {'Description':<22} {'Reward':<8} {'Nodes':<6} "
          f"{'Budget%':<8} {'Valid':<7} {'Time':<6}")
    print("─" * 85)
    
    for r in results:
        if not r['success']:
            marker = " ✗"
            reward_str = "ERROR"
        else:
            if r == best_valid:
                marker = " ✓✓"
            elif r == best_overall and not best_valid:
                marker = " ⚠"
            else:
                marker = ""
            reward_str = str(r['raw_reward'])
        
        penalty_str = f"{r['penalty_pct']:.0f}%"
        valid_str = "Yes" if r['valid'] else "No"
        budget_str = f"{r['budget_usage']:.1f}%" if r['success'] else "-"
        
        print(f"{penalty_str:<9} {r['completion_bonus']:<7.2f} {r['description']:<22} "
              f"{reward_str:<8} {r['path_length']:<6} {budget_str:<8} "
              f"{valid_str:<7} {r['time']:<6.2f}{marker}")
    
    # Analysis section
    print("\n" + "=" * 85)
    print("DETAILED ANALYSIS")
    print("=" * 85)
    
    if best_valid:
        print(f"\n✓✓ BEST VALID CONFIGURATION:")
        print(f"  {best_valid['description']}")
        print(f"  Penalty: {best_valid['penalty_mult']}× ({best_valid['penalty_pct']:.0f}% penalty)")
        print(f"  Bonus: +{best_valid['completion_bonus']}")
        print(f"  Raw Reward: {best_valid['raw_reward']}")
        print(f"  Path Length: {best_valid['path_length']} nodes")
        print(f"  Budget Usage: {best_valid['budget_usage']:.1f}%")
        print(f"  Reward/Node: {best_valid['reward_per_node']:.1f}")
    
    if best_overall != best_valid and best_overall:
        print(f"\n⚠  HIGHEST REWARD (Invalid - incomplete path):")
        print(f"  {best_overall['description']}")
        print(f"  Raw Reward: {best_overall['raw_reward']}")
        print(f"  (Not usable - path doesn't reach END_NODE)")
    
    # Compare with standard
    standard = [r for r in results if r['description'] == "Standard (current)"]
    if standard and standard[0]['success']:
        std = standard[0]
        print(f"\n📊 COMPARISON WITH STANDARD (0.7×, 0.15):")
        print(f"  Standard Reward: {std['raw_reward']}")
        
        if best_valid and best_valid != std:
            diff = best_valid['raw_reward'] - std['raw_reward']
            pct = (diff / std['raw_reward'] * 100) if std['raw_reward'] > 0 else 0
            
            if diff > 0:
                print(f"  Best is {diff} points better ({pct:+.1f}% improvement)")
                print(f"  Recommendation: Consider using {best_valid['description']}")
            elif diff < 0:
                print(f"  Standard is {abs(diff)} points better ({abs(pct):.1f}%)")
                print(f"  Recommendation: Keep standard configuration")
            else:
                print(f"  Best matches standard (no improvement found)")
        elif best_valid == std:
            print(f"  ✓ Standard configuration is optimal!")
    
    # Pattern analysis
    print("\n" + "=" * 85)
    print("PATTERN ANALYSIS")
    print("=" * 85)
    
    if valid_solutions:
        # Group by penalty range
        penalty_groups = {
            'harsh': [r for r in valid_solutions if r['penalty_mult'] < 0.6],
            'moderate': [r for r in valid_solutions if 0.6 <= r['penalty_mult'] < 0.8],
            'lenient': [r for r in valid_solutions if r['penalty_mult'] >= 0.8]
        }
        
        print("\n1. Penalty Severity Impact:")
        for group_name, group_results in penalty_groups.items():
            if group_results:
                avg_reward = sum(r['raw_reward'] for r in group_results) / len(group_results)
                avg_path = sum(r['path_length'] for r in group_results) / len(group_results)
                avg_budget = sum(r['budget_usage'] for r in group_results) / len(group_results)
                print(f"  {group_name.capitalize():<12} "
                      f"Avg Reward: {avg_reward:>6.0f}  "
                      f"Avg Path: {avg_path:>4.1f} nodes  "
                      f"Budget: {avg_budget:>4.1f}%")
        
        # Bonus impact
        print("\n2. Completion Bonus Impact:")
        bonus_sorted = sorted(valid_solutions, key=lambda x: x['completion_bonus'])
        if len(bonus_sorted) >= 3:
            low_bonus = bonus_sorted[:len(bonus_sorted)//3]
            high_bonus = bonus_sorted[-len(bonus_sorted)//3:]
            
            low_avg = sum(r['raw_reward'] for r in low_bonus) / len(low_bonus)
            high_avg = sum(r['raw_reward'] for r in high_bonus) / len(high_bonus)
            
            print(f"  Low bonus configs (<{bonus_sorted[len(bonus_sorted)//3]['completion_bonus']:.2f}):  "
                  f"Avg reward = {low_avg:.0f}")
            print(f"  High bonus configs (>{bonus_sorted[-len(bonus_sorted)//3]['completion_bonus']:.2f}): "
                  f"Avg reward = {high_avg:.0f}")
            
            if high_avg > low_avg:
                diff_pct = ((high_avg - low_avg) / low_avg * 100)
                print(f"  → Higher bonuses correlate with {diff_pct:+.1f}% better rewards")
            else:
                diff_pct = ((low_avg - high_avg) / high_avg * 100)
                print(f"  → Lower bonuses correlate with {diff_pct:+.1f}% better rewards")
        
        # Path length correlation
        print("\n3. Path Length Distribution:")
        min_path = min(r['path_length'] for r in valid_solutions)
        max_path = max(r['path_length'] for r in valid_solutions)
        avg_path = sum(r['path_length'] for r in valid_solutions) / len(valid_solutions)
        
        print(f"  Range: {min_path} - {max_path} nodes")
        print(f"  Average: {avg_path:.1f} nodes")
        
        # Find config with longest path
        longest_path_config = max(valid_solutions, key=lambda x: x['path_length'])
        print(f"  Longest path: {longest_path_config['path_length']} nodes "
              f"({longest_path_config['description']})")
        print(f"    Reward: {longest_path_config['raw_reward']}")
    
    print("\n" + "=" * 85)
    print("RECOMMENDATIONS FOR WU-UCT")
    print("=" * 85)
    
    if best_valid:
        if best_valid['description'] == "Standard (current)":
            print("\n✓ Current configuration (0.7×, 0.15) is optimal!")
            print("  No changes needed.")
        else:
            print(f"\n💡 Consider switching to: {best_valid['description']}")
            print(f"   Penalty: {best_valid['penalty_mult']}×")
            print(f"   Bonus: +{best_valid['completion_bonus']}")
            print(f"   Expected improvement: {best_valid['raw_reward'] - std['raw_reward']} points")
    
    print("\nGeneral observations:")
    if valid_solutions:
        avg_all = sum(r['raw_reward'] for r in valid_solutions) / len(valid_solutions)
        std_dev = (sum((r['raw_reward'] - avg_all)**2 for r in valid_solutions) / len(valid_solutions))**0.5
        
        if std_dev / avg_all > 0.1:  # >10% variation
            print("  • Penalty/bonus choice significantly affects WU-UCT performance")
            print("  • Parallel nature makes the algorithm sensitive to these parameters")
        else:
            print("  • WU-UCT performance is relatively stable across configurations")
            print("  • Virtual loss mechanism may be compensating for different penalties")
    
    return results

if __name__ == "__main__":
    print("\n" + "=" * 85)
    print(" WU-UCT PENALTY/BONUS PARAMETER TUNING - AUTOMATED TEST")
    print("=" * 85)
    print("\nThis test uses monkey-patching to test different configurations")
    print("without modifying the source code.")
    print()
    
    results = test_penalty_bonus_configurations()
    
    print("\n" + "=" * 85)
    print("TEST COMPLETE")
    print("=" * 85)
    print("\nResults saved in memory. To export, run:")
    print("  import json")
    print("  with open('wu_uct_penalty_results.json', 'w') as f:")
    print("      json.dump(results, f, indent=2)")
