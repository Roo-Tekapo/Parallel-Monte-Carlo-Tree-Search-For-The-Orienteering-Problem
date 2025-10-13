#!/usr/bin/env python3
"""
Diagnostic test to identify why normalized rewards give worse results
"""

from orienteering.orienteering import OrienteeringProblem
from MCTS.mcts_base import MCTSSingleThread
import time

def test_normalization_comparison():
    # Load a test problem
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    
    print("=" * 70)
    print("NORMALIZATION COMPARISON TEST")
    print("=" * 70)
    
    # Analyze the problem structure
    max_score = max(n.score for n in nodes)
    min_score = min(n.score for n in nodes if n.score > 0)
    avg_score = sum(n.score for n in nodes) / len(nodes)
    
    print(f"\nProblem Stats:")
    print(f"  Nodes: {len(nodes)}")
    print(f"  Budget: {budget}")
    print(f"  Max node score: {max_score}")
    print(f"  Min node score: {min_score}")
    print(f"  Avg node score: {avg_score:.1f}")
    print(f"  Score range: {min_score}-{max_score} (ratio: {max_score/min_score:.1f}:1)")
    
    # Test WITHOUT normalization
    print("\n" + "=" * 70)
    print("1. Testing WITHOUT normalization...")
    print("=" * 70)
    problem_no_norm = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, 
                                         normalize_rewards=False)
    solver_no_norm = MCTSSingleThread(problem_no_norm, iterations=5000, 
                                      traditional_mcts=True)
    start = time.time()
    best_state_no_norm = solver_no_norm.run()
    time_no_norm = time.time() - start
    
    raw_reward_no_norm = sum(problem_no_norm.nodes[node_id].score 
                             for node_id in best_state_no_norm.get_path())
    
    print(f"   Path: {best_state_no_norm.get_path()}")
    print(f"   Path length: {len(best_state_no_norm.get_path())} nodes")
    print(f"   Raw reward: {raw_reward_no_norm}")
    print(f"   MCTS reward: {best_state_no_norm.get_reward()}")
    print(f"   Cost: {best_state_no_norm.get_cost():.2f} / {budget}")
    print(f"   Valid (complete): {best_state_no_norm.is_terminal()}")
    print(f"   Time: {time_no_norm:.2f}s")
    
    # Test WITH normalization
    print("\n" + "=" * 70)
    print("2. Testing WITH normalization...")
    print("=" * 70)
    problem_norm = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, 
                                      normalize_rewards=True)
    
    print(f"   Normalization scale: {problem_norm.reward_scale:.6f}")
    print(f"   Max node normalized: {max_score * problem_norm.reward_scale:.4f}")
    print(f"   Avg node normalized: {avg_score * problem_norm.reward_scale:.4f}")
    
    solver_norm = MCTSSingleThread(problem_norm, iterations=5000, 
                                  traditional_mcts=True)
    start = time.time()
    best_state_norm = solver_norm.run()
    time_norm = time.time() - start
    
    raw_reward_norm = sum(problem_norm.nodes[node_id].score 
                         for node_id in best_state_norm.get_path())
    
    print(f"   Path: {best_state_norm.get_path()}")
    print(f"   Path length: {len(best_state_norm.get_path())} nodes")
    print(f"   Raw reward: {raw_reward_norm}")
    print(f"   Normalized reward: {best_state_norm.get_reward():.4f}")
    print(f"   Cost: {best_state_norm.get_cost():.2f} / {budget}")
    print(f"   Valid (complete): {best_state_norm.is_terminal()}")
    print(f"   Time: {time_norm:.2f}s")
    
    # UCT Analysis
    print("\n" + "=" * 70)
    print("UCT BALANCE ANALYSIS")
    print("=" * 70)
    
    # Simulate typical UCT values
    import math
    parent_visits = 100
    child_visits = 10
    c = math.sqrt(2)
    
    print("\nTypical UCT components (parent=100 visits, child=10 visits, c=√2):")
    
    # Without normalization
    typical_reward_no_norm = 50  # Typical node score
    exploit_no_norm = typical_reward_no_norm
    explore = c * math.sqrt(math.log(parent_visits) / child_visits)
    print(f"\nWITHOUT normalization:")
    print(f"  Exploit term: {exploit_no_norm:.2f}")
    print(f"  Explore term: {explore:.2f}")
    print(f"  Ratio (exploit:explore): {exploit_no_norm/explore:.1f}:1")
    print(f"  → {'EXPLOITATION dominates' if exploit_no_norm > explore * 2 else 'Balanced'}")
    
    # With normalization
    typical_reward_norm = 0.5  # Typical normalized score
    exploit_norm = typical_reward_norm
    print(f"\nWITH normalization:")
    print(f"  Exploit term: {exploit_norm:.2f}")
    print(f"  Explore term: {explore:.2f}")
    print(f"  Ratio (explore:exploit): {explore/exploit_norm:.1f}:1")
    print(f"  → {'EXPLORATION dominates' if explore > exploit_norm * 2 else 'Balanced'}")
    
    # Comparison
    print("\n" + "=" * 70)
    print("RESULT COMPARISON")
    print("=" * 70)
    print(f"Raw reward WITHOUT norm: {raw_reward_no_norm}")
    print(f"Raw reward WITH norm:    {raw_reward_norm}")
    print(f"Difference: {raw_reward_no_norm - raw_reward_norm}")
    
    if raw_reward_no_norm != raw_reward_norm:
        pct_diff = abs(raw_reward_no_norm - raw_reward_norm) / max(raw_reward_no_norm, raw_reward_norm) * 100
        print(f"Percentage difference: {pct_diff:.1f}%")
    
    print()
    if raw_reward_no_norm > raw_reward_norm:
        print("❌ WITHOUT normalization performed BETTER")
        print("\nLikely reasons:")
        print("  1. Normalized penalties too harsh (0.3× = 70% penalty)")
        print("  2. Normalized bonus too small (0.01)")
        print("  3. Exploration dominates (c=√2 too large for normalized rewards)")
        print("\nRecommended fixes:")
        print("  • Change penalty to 0.5× (50% penalty)")
        print("  • Change bonus to 0.1 (10% of typical node)")
        print("  • Reduce exploration constant to 0.7-1.0")
    elif raw_reward_norm > raw_reward_no_norm:
        print("✓ WITH normalization performed BETTER")
        pct_better = (raw_reward_norm - raw_reward_no_norm) / raw_reward_no_norm * 100
        print(f"  Improvement: {pct_better:.1f}%")
    else:
        print("= TIED (same solution)")

def test_penalty_sensitivity():
    """Test different penalty/bonus configurations"""
    print("\n\n" + "=" * 70)
    print("PENALTY SENSITIVITY TEST")
    print("=" * 70)
    
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    
    configs = [
        (0.3, 0.01, "Current (harsh)"),
        (0.5, 0.05, "Moderate"),
        (0.6, 0.1, "Lenient"),
        (0.7, 0.15, "Very lenient"),
    ]
    
    print("\nTesting different penalty/bonus configurations...")
    print("(penalty_mult, completion_bonus, description)")
    print()
    
    # This would require modifying the code to accept these as parameters
    # For now, just explain what we'd test
    print("Configuration tests to try:")
    for penalty, bonus, desc in configs:
        print(f"  • {desc}: penalty={penalty}× ({(1-penalty)*100:.0f}%), bonus=+{bonus}")
    
    print("\nTo test these, modify mcts_base.py lines 217-228:")
    print("  reward *= PENALTY_MULT  # instead of 0.3")
    print("  reward += COMPLETION_BONUS  # instead of 0.01")

if __name__ == "__main__":
    test_normalization_comparison()
    test_penalty_sensitivity()
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
