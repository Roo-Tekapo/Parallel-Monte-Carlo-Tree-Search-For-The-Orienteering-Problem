"""
Test MCTS Base with Traditional Orienteering Implementation.

This script:
1. Runs mcts_base with orienteering_traditional.py
2. Tests multiple runs to see completion rate
3. Allows experimentation with end node rewards/bonuses
4. Compares different reward strategies
"""

import time
import statistics
from MCTS.mcts_base import MCTSSingleThread
from orienteering.orienteering_traditional import (
    OrienteeringProblemTraditional,
    OrienteeringStateTraditional
)


def run_multiple_tests(problem_file, iterations=5000, num_runs=10, 
                       exploration_constant=1.414, end_bonus=100):
    """Run multiple MCTS tests and collect statistics."""
    
    nodes, budget = OrienteeringProblemTraditional.load_problem(problem_file)
    
    print(f"\n{'='*70}")
    print(f"Testing: {problem_file.split('/')[-1]}")
    print(f"{'='*70}")
    print(f"Problem: {len(nodes)} nodes, budget={budget}")
    print(f"Settings: {iterations} iterations, {num_runs} runs")
    print(f"End bonus: {end_bonus}")
    
    results = {
        'rewards': [],
        'normalized_rewards': [],
        'path_lengths': [],
        'costs': [],
        'completion_count': 0,
        'times': []
    }
    
    for run in range(num_runs):
        # Create fresh problem for each run
        problem = OrienteeringProblemTraditional(
            nodes, budget, 
            max_edge_distance=1.42, 
            normalize_rewards=True
        )
        
        solver = MCTSSingleThread(
            problem, 
            iterations=iterations,
            exploration_constant=exploration_constant,
            traditional_mcts=True
        )
        
        start = time.perf_counter()
        best_state = solver.run()
        elapsed = time.perf_counter() - start
        
        # Calculate metrics
        raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
        is_complete = best_state.is_terminal()
        
        results['rewards'].append(raw_reward)
        results['normalized_rewards'].append(best_state.get_reward())
        results['path_lengths'].append(len(best_state.get_path()))
        results['costs'].append(best_state.get_cost())
        results['times'].append(elapsed)
        
        if is_complete:
            results['completion_count'] += 1
        
        status = "✓ COMPLETE" if is_complete else "✗ INCOMPLETE"
        print(f"  Run {run+1:2d}: Reward={raw_reward:4d}, Path={len(best_state.get_path()):2d}, "
              f"Cost={best_state.get_cost():5.2f}, {status}")
    
    # Calculate statistics
    completion_rate = (results['completion_count'] / num_runs) * 100
    
    print(f"\n{'='*70}")
    print(f"{'RESULTS SUMMARY':^70}")
    print(f"{'='*70}")
    print(f"\nCompletion Rate: {results['completion_count']}/{num_runs} ({completion_rate:.1f}%)")
    
    if completion_rate < 100:
        print(f"  ⚠️  WARNING: {num_runs - results['completion_count']} runs failed to reach END!")
    else:
        print(f"  ✓ All runs successfully reached END node")
    
    print(f"\nRewards (Raw):")
    print(f"  Average: {statistics.mean(results['rewards']):.2f}")
    print(f"  Std Dev: {statistics.stdev(results['rewards']) if len(results['rewards']) > 1 else 0:.2f}")
    print(f"  Min: {min(results['rewards']):.0f}")
    print(f"  Max: {max(results['rewards']):.0f}")
    
    print(f"\nPath Lengths:")
    print(f"  Average: {statistics.mean(results['path_lengths']):.1f}")
    print(f"  Min: {min(results['path_lengths'])}")
    print(f"  Max: {max(results['path_lengths'])}")
    
    print(f"\nExecution Time:")
    print(f"  Average: {statistics.mean(results['times']):.3f}s")
    print(f"  Speed: {iterations / statistics.mean(results['times']):.1f} it/s")
    
    return results, completion_rate


def test_different_strategies(problem_file, iterations=5000, num_runs=10):
    """Test different reward strategies to improve completion rate."""
    
    print(f"\n{'#'*70}")
    print(f"{'TESTING DIFFERENT REWARD STRATEGIES':^70}")
    print(f"{'#'*70}")
    print(f"\nGoal: Find best strategy to maximize completion rate while maintaining quality")
    
    strategies = []
    
    # Strategy 1: Current default (bonus in simulate method)
    print(f"\n{'='*70}")
    print("Strategy 1: Default (bonus handled in simulate method)")
    print(f"{'='*70}")
    results1, comp1 = run_multiple_tests(problem_file, iterations, num_runs)
    strategies.append(("Default", comp1, statistics.mean(results1['rewards'])))
    
    # Strategy 2: Higher exploration constant (favor exploration)
    print(f"\n{'='*70}")
    print("Strategy 2: Higher Exploration Constant (C=2.0)")
    print(f"{'='*70}")
    print("Rationale: More exploration might find paths to END")
    
    nodes, budget = OrienteeringProblemTraditional.load_problem(problem_file)
    
    results2 = {
        'rewards': [],
        'completion_count': 0,
    }
    
    for run in range(num_runs):
        problem = OrienteeringProblemTraditional(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
        solver = MCTSSingleThread(problem, iterations=iterations, exploration_constant=2.0, traditional_mcts=True)
        best_state = solver.run()
        raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
        results2['rewards'].append(raw_reward)
        if best_state.is_terminal():
            results2['completion_count'] += 1
        status = "✓" if best_state.is_terminal() else "✗"
        print(f"  Run {run+1:2d}: Reward={raw_reward:4d}, {status}")
    
    comp2 = (results2['completion_count'] / num_runs) * 100
    print(f"\nCompletion Rate: {results2['completion_count']}/{num_runs} ({comp2:.1f}%)")
    strategies.append(("High Exploration (C=2.0)", comp2, statistics.mean(results2['rewards'])))
    
    # Strategy 3: Lower exploration (favor exploitation)
    print(f"\n{'='*70}")
    print("Strategy 3: Lower Exploration Constant (C=0.7)")
    print(f"{'='*70}")
    print("Rationale: Focus on exploiting good paths that might reach END")
    
    results3 = {
        'rewards': [],
        'completion_count': 0,
    }
    
    for run in range(num_runs):
        problem = OrienteeringProblemTraditional(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
        solver = MCTSSingleThread(problem, iterations=iterations, exploration_constant=0.7, traditional_mcts=True)
        best_state = solver.run()
        raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
        results3['rewards'].append(raw_reward)
        if best_state.is_terminal():
            results3['completion_count'] += 1
        status = "✓" if best_state.is_terminal() else "✗"
        print(f"  Run {run+1:2d}: Reward={raw_reward:4d}, {status}")
    
    comp3 = (results3['completion_count'] / num_runs) * 100
    print(f"\nCompletion Rate: {results3['completion_count']}/{num_runs} ({comp3:.1f}%)")
    strategies.append(("Low Exploration (C=0.7)", comp3, statistics.mean(results3['rewards'])))
    
    # Strategy 4: Soft end bias
    print(f"\n{'='*70}")
    print("Strategy 4: Soft End Bias (bias toward END when budget low)")
    print(f"{'='*70}")
    print("Rationale: Bias simulations toward END when budget is running out")
    
    results4 = {
        'rewards': [],
        'completion_count': 0,
    }
    
    for run in range(num_runs):
        problem = OrienteeringProblemTraditional(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
        solver = MCTSSingleThread(problem, iterations=iterations, exploration_constant=1.414, 
                                 traditional_mcts=True, soft_end_bias=True)
        best_state = solver.run()
        raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
        results4['rewards'].append(raw_reward)
        if best_state.is_terminal():
            results4['completion_count'] += 1
        status = "✓" if best_state.is_terminal() else "✗"
        print(f"  Run {run+1:2d}: Reward={raw_reward:4d}, {status}")
    
    comp4 = (results4['completion_count'] / num_runs) * 100
    print(f"\nCompletion Rate: {results4['completion_count']}/{num_runs} ({comp4:.1f}%)")
    strategies.append(("Soft End Bias", comp4, statistics.mean(results4['rewards'])))
    
    # Summary comparison
    print(f"\n{'='*70}")
    print(f"{'STRATEGY COMPARISON':^70}")
    print(f"{'='*70}")
    print(f"\n{'Strategy':<30} {'Completion %':<15} {'Avg Reward':<15}")
    print(f"{'-'*70}")
    
    for name, comp_rate, avg_reward in strategies:
        print(f"{name:<30} {comp_rate:>6.1f}%         {avg_reward:>8.1f}")
    
    # Find best strategy
    best_completion = max(strategies, key=lambda x: x[1])
    best_quality = max(strategies, key=lambda x: x[2])
    
    print(f"\n{'='*70}")
    print("Recommendations:")
    print(f"{'='*70}")
    print(f"Best Completion Rate: {best_completion[0]} ({best_completion[1]:.1f}%)")
    print(f"Best Quality: {best_quality[0]} (avg reward: {best_quality[2]:.1f})")
    
    if best_completion[1] < 80:
        print(f"\n⚠️  WARNING: Even the best strategy has low completion rate!")
        print("Suggestions:")
        print("  1. Check if problem is feasible (can END be reached?)")
        print("  2. Increase end node bonus in simulate() method")
        print("  3. Consider using Conservative MCTS instead")
        print("  4. Add stronger bias toward END in late game")


def analyze_incomplete_paths(problem_file, num_runs=5):
    """Analyze why paths don't reach END."""
    
    print(f"\n{'='*70}")
    print("ANALYZING INCOMPLETE PATHS")
    print(f"{'='*70}")
    
    nodes, budget = OrienteeringProblemTraditional.load_problem(problem_file)
    problem = OrienteeringProblemTraditional(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
    
    print(f"\nProblem Stats:")
    print(f"  Total nodes: {len(nodes)}")
    print(f"  Budget: {budget}")
    print(f"  Distance START to END: {problem.get_distance(0, 1):.2f}")
    print(f"  Min possible cost: {problem.get_distance(0, 1):.2f}")
    
    incomplete_paths = []
    
    for run in range(num_runs):
        problem = OrienteeringProblemTraditional(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
        solver = MCTSSingleThread(problem, iterations=5000, traditional_mcts=True)
        best_state = solver.run()
        
        if not best_state.is_terminal():
            last_node = best_state.get_path()[-1]
            cost_to_end = problem.get_distance(last_node, 1)
            remaining_budget = budget - best_state.get_cost()
            
            incomplete_paths.append({
                'path': best_state.get_path(),
                'cost': best_state.get_cost(),
                'last_node': last_node,
                'cost_to_end': cost_to_end,
                'remaining_budget': remaining_budget,
                'could_reach_end': remaining_budget >= cost_to_end
            })
    
    if incomplete_paths:
        print(f"\n⚠️  Found {len(incomplete_paths)} incomplete paths:")
        for i, path_info in enumerate(incomplete_paths, 1):
            print(f"\n  Incomplete Path {i}:")
            print(f"    Last node: {path_info['last_node']}")
            print(f"    Cost used: {path_info['cost']:.2f} / {budget}")
            print(f"    Remaining budget: {path_info['remaining_budget']:.2f}")
            print(f"    Distance to END: {path_info['cost_to_end']:.2f}")
            if path_info['could_reach_end']:
                print(f"    ✓ Could have reached END! (budget sufficient)")
            else:
                print(f"    ✗ Cannot reach END (insufficient budget)")
    else:
        print(f"\n✓ All {num_runs} runs successfully reached END!")


if __name__ == "__main__":
    print("="*70)
    print("MCTS BASE WITH TRADITIONAL ORIENTEERING - Completion Analysis")
    print("="*70)
    
    problem_file = "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    
    # Run initial test
    print("\nPhase 1: Initial test with default settings")
    results, completion_rate = run_multiple_tests(problem_file, iterations=5000, num_runs=10)
    
    # Analyze incomplete paths if completion rate is low
    if completion_rate < 100:
        print(f"\n⚠️  Completion rate is {completion_rate:.1f}% - analyzing failures...")
        analyze_incomplete_paths(problem_file, num_runs=5)
    
    # Test different strategies
    print("\n\nPhase 2: Testing different strategies to improve completion rate")
    test_different_strategies(problem_file, iterations=5000, num_runs=10)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("  1. If completion rate is low, check the analysis above")
    print("  2. Try the recommended strategy")
    print("  3. Adjust end node bonuses in MCTS.mcts_base.simulate() if needed")
    print("  4. Consider using soft_end_bias or higher exploration constant")
