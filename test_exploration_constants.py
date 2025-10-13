#!/usr/bin/env python3
"""
Test different exploration constants with normalized rewards (after penalty fix)
"""

from orienteering.orienteering import OrienteeringProblem
from MCTS.mcts_base import MCTSSingleThread
import time
import math

def test_exploration_constants():
    # Load test problem
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    
    print("=" * 70)
    print("EXPLORATION CONSTANT COMPARISON (With Fixed Penalties)")
    print("=" * 70)
    print(f"\nProblem: 121 nodes, budget={budget}")
    print("Penalties: 0.7× (30% penalty), Bonus: 0.15")
    print()
    
    # Test different exploration constants
    exploration_constants = [
        (0.5, "Very Low (more greedy)"),
        (0.7, "Low"),
        (1.0, "Moderate"),
        (math.sqrt(2), "Standard (√2)"),
        (2.0, "High"),
    ]
    
    results = []
    
    for c_value, description in exploration_constants:
        print(f"Testing c={c_value:.3f} ({description})...")
        
        # WITH normalization
        problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, 
                                      normalize_rewards=True)
        solver = MCTSSingleThread(problem, 
                                  iterations=5000, 
                                  exploration_constant=c_value,
                                  traditional_mcts=True)
        
        start = time.time()
        best_state = solver.run()
        elapsed = time.time() - start
        
        raw_reward = sum(problem.nodes[node_id].score 
                        for node_id in best_state.get_path())
        
        results.append({
            'c': c_value,
            'desc': description,
            'reward': raw_reward,
            'path_len': len(best_state.get_path()),
            'cost': best_state.get_cost(),
            'valid': best_state.is_terminal(),
            'time': elapsed
        })
        
        print(f"  Reward: {raw_reward}, Path: {len(best_state.get_path())} nodes, "
              f"Cost: {best_state.get_cost():.2f}, Time: {elapsed:.2f}s")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'c value':<10} {'Description':<25} {'Reward':<8} {'Nodes':<6} {'Cost':<8} {'Valid':<6}")
    print("-" * 70)
    
    best_result = max(results, key=lambda x: x['reward'])
    
    for r in results:
        marker = " ✓ BEST" if r == best_result else ""
        print(f"{r['c']:<10.3f} {r['desc']:<25} {r['reward']:<8} {r['path_len']:<6} "
              f"{r['cost']:<8.2f} {'Yes' if r['valid'] else 'No':<6}{marker}")
    
    print()
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    
    # Compare to standard √2
    std_result = [r for r in results if abs(r['c'] - math.sqrt(2)) < 0.01][0]
    
    print(f"\nStandard (c=√2) baseline: {std_result['reward']} reward")
    
    for r in results:
        if r['c'] != std_result['c']:
            diff = r['reward'] - std_result['reward']
            pct = (diff / std_result['reward'] * 100) if std_result['reward'] > 0 else 0
            direction = "better" if diff > 0 else "worse"
            print(f"  c={r['c']:.3f}: {diff:+d} ({pct:+.1f}%) {direction}")
    
    print(f"\nRecommendation: Use c={best_result['c']:.3f} ({best_result['desc']})")
    print(f"  Best reward: {best_result['reward']}")
    print(f"  Improvement over √2: {best_result['reward'] - std_result['reward']:+d} "
          f"({(best_result['reward'] - std_result['reward']) / std_result['reward'] * 100:+.1f}%)")

def test_combined_best():
    """Test the best configuration against unnormalized baseline"""
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    
    print("\n\n" + "=" * 70)
    print("FINAL COMPARISON: Best Config vs Unnormalized")
    print("=" * 70)
    
    # Unnormalized baseline
    print("\n1. WITHOUT normalization (baseline)...")
    problem_no_norm = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, 
                                         normalize_rewards=False)
    solver_no_norm = MCTSSingleThread(problem_no_norm, iterations=5000, 
                                      traditional_mcts=True)
    best_state_no_norm = solver_no_norm.run()
    raw_reward_no_norm = sum(problem_no_norm.nodes[node_id].score 
                             for node_id in best_state_no_norm.get_path())
    
    print(f"   Reward: {raw_reward_no_norm}")
    print(f"   Path: {len(best_state_no_norm.get_path())} nodes")
    print(f"   Cost: {best_state_no_norm.get_cost():.2f} / {budget}")
    
    # Best normalized config (c=1.0 tends to work well)
    print("\n2. WITH normalization (c=1.0, fixed penalties)...")
    problem_norm = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, 
                                      normalize_rewards=True)
    solver_norm = MCTSSingleThread(problem_norm, 
                                  iterations=5000,
                                  exploration_constant=1.0,
                                  traditional_mcts=True)
    best_state_norm = solver_norm.run()
    raw_reward_norm = sum(problem_norm.nodes[node_id].score 
                         for node_id in best_state_norm.get_path())
    
    print(f"   Reward: {raw_reward_norm}")
    print(f"   Path: {len(best_state_norm.get_path())} nodes")
    print(f"   Cost: {best_state_norm.get_cost():.2f} / {budget}")
    
    # Comparison
    print("\n" + "-" * 70)
    diff = raw_reward_norm - raw_reward_no_norm
    if diff > 0:
        print(f"✓ Normalized version is {diff} points better ({diff/raw_reward_no_norm*100:.1f}% improvement)")
    elif diff < 0:
        print(f"✗ Normalized version is {abs(diff)} points worse ({abs(diff)/raw_reward_no_norm*100:.1f}%)")
    else:
        print("= Both versions found same reward")

if __name__ == "__main__":
    test_exploration_constants()
    test_combined_best()
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("\nRecommended settings for normalized rewards:")
    print("  • exploration_constant = 1.0 (or best from test above)")
    print("  • penalty = 0.7× (30% penalty)")
    print("  • completion_bonus = 0.15")
