"""
Test the optimized end node bonus (0.30) across multiple problem instances
to verify it achieves high completion rates while maintaining solution quality.
"""

import time
from orienteering.orienteering import OrienteeringProblem
from MCTS.mcts_base import MCTSSingleThread

def test_problem(problem_file, iterations=5000, num_runs=10):
    """Test a problem with the optimized reward settings"""
    print(f"\n{'='*70}")
    print(f"Testing: {problem_file}")
    print(f"{'='*70}")
    
    # Load problem
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
    
    print(f"Problem stats: {len(nodes)} nodes, budget={budget}")
    
    # Run multiple times to check consistency
    completed = 0
    total_reward = 0
    total_raw_reward = 0
    total_cost = 0
    total_path_length = 0
    total_time = 0
    
    for run in range(num_runs):
        start_time = time.perf_counter()
        
        solver = MCTSSingleThread(problem, iterations=iterations, traditional_mcts=True)
        best_state = solver.run()
        
        elapsed = time.perf_counter() - start_time
        total_time += elapsed
        
        # Calculate metrics
        path = best_state.get_path()
        normalized_reward = best_state.get_reward()
        raw_reward = sum(problem.nodes[node_id].score for node_id in path)
        cost = best_state.get_cost()
        is_complete = best_state.is_terminal()
        
        if is_complete:
            completed += 1
        
        total_reward += normalized_reward
        total_raw_reward += raw_reward
        total_cost += cost
        total_path_length += len(path)
        
        # Print individual run (first 3 runs only to avoid clutter)
        if run < 3:
            status = "✓ COMPLETE" if is_complete else "✗ INCOMPLETE"
            print(f"  Run {run+1}: {status}, Raw Reward: {raw_reward:.1f}, Path Length: {len(path)}, Cost: {cost:.2f}")
    
    # Print summary
    completion_rate = (completed / num_runs) * 100
    avg_reward = total_reward / num_runs
    avg_raw_reward = total_raw_reward / num_runs
    avg_cost = total_cost / num_runs
    avg_path_length = total_path_length / num_runs
    avg_time = total_time / num_runs
    iterations_per_sec = iterations / avg_time
    
    print(f"\n{'─'*70}")
    print(f"SUMMARY ({num_runs} runs):")
    print(f"  Completion Rate: {completion_rate:.1f}%")
    print(f"  Avg Normalized Reward: {avg_reward:.2f}")
    print(f"  Avg Raw Reward: {avg_raw_reward:.1f}")
    print(f"  Avg Path Length: {avg_path_length:.1f} nodes")
    print(f"  Avg Cost: {avg_cost:.2f} / {budget}")
    print(f"  Avg Time: {avg_time:.3f}s ({iterations_per_sec:.0f} it/s)")
    
    return {
        'problem': problem_file.split('/')[-1],
        'completion_rate': completion_rate,
        'avg_raw_reward': avg_raw_reward,
        'avg_path_length': avg_path_length,
        'iterations_per_sec': iterations_per_sec
    }

def main():
    print("="*70)
    print("TESTING OPTIMIZED END NODE BONUS (0.30) ACROSS MULTIPLE PROBLEMS")
    print("="*70)
    print("\nThis tests the new reward settings (0.30 bonus, 0.7x penalty)")
    print("across different problem types to verify consistent performance.")
    
    # Test problems
    test_problems = [
        # Original test problem
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt",
        
        # Long budget problem
        "OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt",
        
        # Grid pattern problems
        "OP_Benchmark_Set/grid_patterns/grid_corners_b40.txt",
        "OP_Benchmark_Set/grid_patterns/grid_diagonal_b40.txt",
        "OP_Benchmark_Set/grid_patterns/grid_center_b40.txt",
        "OP_Benchmark_Set/grid_patterns/grid_edges_b40.txt",
    ]
    
    results = []
    
    for problem_file in test_problems:
        try:
            result = test_problem(problem_file, iterations=5000, num_runs=10)
            results.append(result)
        except FileNotFoundError:
            print(f"\n⚠ Warning: File not found: {problem_file}")
        except Exception as e:
            print(f"\n⚠ Error testing {problem_file}: {e}")
    
    # Print overall summary
    print("\n" + "="*70)
    print("OVERALL SUMMARY")
    print("="*70)
    print(f"\n{'Problem':<35} {'Comp %':>8} {'Reward':>8} {'Path':>6} {'Speed':>10}")
    print("─"*70)
    
    total_completion = 0
    for result in results:
        print(f"{result['problem']:<35} {result['completion_rate']:>7.1f}% "
              f"{result['avg_raw_reward']:>8.1f} {result['avg_path_length']:>6.1f} "
              f"{result['iterations_per_sec']:>9.0f}/s")
        total_completion += result['completion_rate']
    
    if results:
        avg_completion = total_completion / len(results)
        print("─"*70)
        print(f"Average Completion Rate: {avg_completion:.1f}%")
        
        if avg_completion >= 95:
            print("\n✓ SUCCESS: Optimized rewards achieve excellent completion rates!")
        elif avg_completion >= 85:
            print("\n✓ GOOD: Optimized rewards achieve good completion rates.")
        else:
            print("\n⚠ WARNING: Completion rate may need further tuning.")

if __name__ == "__main__":
    main()
