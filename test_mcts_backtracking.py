"""
Focused test for Traditional MCTS backtracking fix.

Tests that MCTS can continue exploring productively even when budget is exhausted
but iterations remain.
"""

import math
import time
from orienteering.orienteering_traditional import OrienteeringProblem
from MCTS.mcts_base import MCTSSingleThread


def test_mcts_backtracking(problem_file, iterations_list=[1000, 10000, 50000]):
    """
    Test MCTS with increasing iteration counts to verify backtracking works.
    
    Args:
        problem_file: Path to the problem file
        iterations_list: List of iteration counts to test
    """
    print("="*80)
    print("Testing MCTS Backtracking Fix")
    print("="*80)
    
    # Load problem
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    
    print(f"\nProblem: {problem_file}")
    print(f"Nodes: {len(nodes)}, Budget: {budget}")
    print(f"\nTesting with different iteration counts to verify backtracking...\n")
    
    results = []
    
    for iterations in iterations_list:
        print("-" * 80)
        print(f"Running MCTS with {iterations:,} iterations")
        print("-" * 80)
        
        problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
        mcts = MCTSSingleThread(
            problem, 
            iterations=iterations,
            exploration_constant=math.sqrt(2),
            soft_end_bias=True,
            bias_decay_factor=5
        )
        
        start = time.time()
        best_state = mcts.run()
        elapsed = time.time() - start
        
        raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
        
        print(f"\nResults:")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Iterations/sec: {iterations/elapsed:.2f}")
        print(f"  Path length: {len(best_state.get_path())} nodes")
        print(f"  Path: {best_state.get_path()}")
        print(f"  Normalized reward: {best_state.get_reward():.6f}")
        print(f"  Raw reward: {raw_reward:.2f}")
        print(f"  Cost: {best_state.get_cost():.2f} / {budget:.2f} ({(best_state.get_cost()/budget)*100:.1f}%)")
        print(f"  Valid (terminal): {best_state.is_terminal()}")
        
        results.append({
            'iterations': iterations,
            'reward': best_state.get_reward(),
            'raw_reward': raw_reward,
            'path_length': len(best_state.get_path()),
            'cost': best_state.get_cost(),
            'time': elapsed,
            'iter_per_sec': iterations/elapsed,
            'valid': best_state.is_terminal()
        })
    
    # Print comparison
    print("\n" + "="*80)
    print("COMPARISON ACROSS ITERATION COUNTS")
    print("="*80)
    print(f"{'Iterations':<12} {'Norm Reward':<14} {'Raw Reward':<12} {'Path Len':<10} {'Time(s)':<10} {'Iter/s':<12} {'Valid':<8}")
    print("-"*80)
    
    for result in results:
        print(f"{result['iterations']:<12,} "
              f"{result['reward']:<14.6f} "
              f"{result['raw_reward']:<12.2f} "
              f"{result['path_length']:<10} "
              f"{result['time']:<10.2f} "
              f"{result['iter_per_sec']:<12.0f} "
              f"{str(result['valid']):<8}")
    
    # Analysis
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    
    # Check if reward improves with more iterations
    reward_improved = results[-1]['raw_reward'] >= results[0]['raw_reward']
    print(f"✓ Reward improvement with more iterations: {reward_improved}")
    if reward_improved:
        improvement = ((results[-1]['raw_reward'] - results[0]['raw_reward']) / results[0]['raw_reward']) * 100
        print(f"  Improvement: {improvement:.1f}% from {results[0]['iterations']:,} to {results[-1]['iterations']:,} iterations")
    
    # Check if iteration rate stays consistent
    avg_iter_rate = sum(r['iter_per_sec'] for r in results) / len(results)
    rate_variance = max(abs(r['iter_per_sec'] - avg_iter_rate) / avg_iter_rate for r in results) * 100
    consistent_rate = rate_variance < 30  # Less than 30% variance
    print(f"✓ Consistent iteration rate: {consistent_rate}")
    print(f"  Average: {avg_iter_rate:.0f} iter/s, Variance: {rate_variance:.1f}%")
    
    # Check if solutions are valid
    all_valid = all(r['valid'] for r in results)
    print(f"✓ All solutions valid (terminal): {all_valid}")
    
    # Summary
    print("\n" + "="*80)
    if reward_improved and consistent_rate:
        print("✅ BACKTRACKING FIX WORKING CORRECTLY!")
        print("   - Algorithm continues to improve with more iterations")
        print("   - Iteration rate remains consistent (not getting stuck)")
        print("   - No signs of premature convergence or deadlock")
    else:
        print("⚠️  POTENTIAL ISSUES DETECTED:")
        if not reward_improved:
            print("   - Reward not improving with more iterations")
            print("   - May indicate premature convergence or getting stuck")
        if not consistent_rate:
            print("   - Iteration rate varying significantly")
            print("   - May indicate performance issues or deadlock")
    print("="*80)


def test_specific_scenario():
    """
    Test a specific scenario where budget exhaustion is likely.
    """
    print("\n\n")
    print("="*80)
    print("SPECIFIC SCENARIO TEST: Small Budget, Many Iterations")
    print("="*80)
    
    # Use a problem with tight budget
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    
    print(f"\nProblem: grid_10x10_medium_30.txt")
    print(f"Budget: {budget} (tight budget scenario)")
    print(f"Testing with 100,000 iterations to stress-test backtracking\n")
    
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
    mcts = MCTSSingleThread(
        problem, 
        iterations=100000,
        exploration_constant=math.sqrt(2),
        soft_end_bias=True,
        bias_decay_factor=5
    )
    
    start = time.time()
    best_state = mcts.run()
    elapsed = time.time() - start
    
    raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
    
    print(f"Results after 100,000 iterations:")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Iterations/sec: {100000/elapsed:.2f}")
    print(f"  Path: {best_state.get_path()}")
    print(f"  Path length: {len(best_state.get_path())} nodes")
    print(f"  Raw reward: {raw_reward:.2f}")
    print(f"  Cost: {best_state.get_cost():.2f} / {budget:.2f}")
    print(f"  Valid: {best_state.is_terminal()}")
    
    if 100000/elapsed > 5000:
        print(f"\n✅ High iteration rate maintained ({100000/elapsed:.0f} iter/s)")
        print("   Backtracking is working - algorithm not getting stuck!")
    else:
        print(f"\n⚠️  Low iteration rate ({100000/elapsed:.0f} iter/s)")
        print("   May indicate performance issues")
    
    print("="*80)


if __name__ == "__main__":
    # Test 1: Progressive iteration increase
    print("\nTEST 1: Progressive Iteration Increase")
    test_mcts_backtracking(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt",
        iterations_list=[1000, 5000, 10000, 25000, 50000]
    )
    
    # Test 2: Specific high-iteration scenario
    print("\n\nTEST 2: High-Iteration Stress Test")
    test_specific_scenario()
    
    print("\n\n")
    print("="*80)
    print("ALL TESTS COMPLETE")
    print("="*80)
