#!/usr/bin/env python3
"""
Test different penalty and bonus values for parallel WU-UCT implementation.
This tests whether the parallel nature and virtual loss mechanism of WU-UCT
requires different penalty/bonus tuning compared to single-threaded MCTS.
"""

from orienteering.orienteering import OrienteeringProblem
from Simple_WU.simple_wu_coordinator import SimpleWUUCT
import time
import sys
import os

def test_penalty_bonus_grid():
    """Test a grid of penalty/bonus combinations"""
    
    # Load test problem
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    
    print("=" * 80)
    print("WU-UCT PENALTY/BONUS PARAMETER TUNING")
    print("=" * 80)
    print(f"\nProblem: 121 nodes, budget={budget}")
    print("Workers: 4 parallel workers")
    print("Iterations: 5000 total")
    print()
    
    # Define test configurations
    # Format: (penalty_multiplier, completion_bonus, description)
    configs = [
        # Very harsh (current old values)
        (0.3, 0.01, "Very Harsh (old)"),
        
        # Harsh
        (0.4, 0.05, "Harsh"),
        (0.5, 0.05, "Moderate-Harsh"),
        
        # Moderate (current new values)
        (0.6, 0.10, "Moderate"),
        (0.7, 0.15, "Moderate-Lenient (new)"),
        
        # Lenient
        (0.75, 0.20, "Lenient"),
        (0.8, 0.25, "Very Lenient"),
        
        # Minimal penalty
        (0.9, 0.30, "Minimal Penalty"),
    ]
    
    results = []
    
    for penalty_mult, completion_bonus, description in configs:
        print(f"\nTesting: {description}")
        print(f"  Penalty: {penalty_mult}× ({(1-penalty_mult)*100:.0f}% penalty)")
        print(f"  Bonus: +{completion_bonus}")
        print("-" * 80)
        
        # Temporarily modify the penalty/bonus in simple_wu_worker.py
        # We'll need to pass these as parameters
        # For now, we'll manually test by modifying the file
        
        problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
        
        # Create WU-UCT coordinator with 4 workers
        coordinator = SimpleWUUCT(
            problem=problem,
            num_workers=4,
            virtual_loss=1.0
        )
        
        start_time = time.time()
        
        try:
            # Run with max iterations
            solution = coordinator.run(max_iterations=5000, time_limit=30.0)
            elapsed = time.time() - start_time
            
            # Calculate raw reward
            raw_reward = sum(problem.nodes[node_id].score for node_id in solution.path)
            normalized_reward = solution.reward_so_far
            
            result = {
                'penalty_mult': penalty_mult,
                'completion_bonus': completion_bonus,
                'description': description,
                'raw_reward': raw_reward,
                'normalized_reward': normalized_reward,
                'path_length': len(solution.path),
                'cost': solution.cost_so_far,
                'valid': solution.is_terminal(),
                'iterations': coordinator.global_iteration,
                'time': elapsed,
                'success': True
            }
            
            print(f"  ✓ Raw reward: {raw_reward}")
            print(f"    Normalized: {normalized_reward:.4f}")
            print(f"    Path: {len(solution.path)} nodes")
            print(f"    Cost: {solution.cost_so_far:.2f} / {budget}")
            print(f"    Valid: {solution.is_terminal()}")
            print(f"    Iterations: {coordinator.global_iteration}")
            print(f"    Time: {elapsed:.2f}s")
            
        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")
            result = {
                'penalty_mult': penalty_mult,
                'completion_bonus': completion_bonus,
                'description': description,
                'raw_reward': 0,
                'normalized_reward': 0,
                'path_length': 0,
                'cost': 0,
                'valid': False,
                'iterations': 0,
                'time': 0,
                'success': False,
                'error': str(e)
            }
        
        results.append(result)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY - WU-UCT Penalty/Bonus Results")
    print("=" * 80)
    print()
    
    # Filter successful results
    successful_results = [r for r in results if r['success']]
    valid_results = [r for r in successful_results if r['valid']]
    
    if not successful_results:
        print("⚠️  No successful runs!")
        return
    
    # Find best configurations
    best_raw = max(successful_results, key=lambda x: x['raw_reward'])
    best_valid = max(valid_results, key=lambda x: x['raw_reward']) if valid_results else None
    
    # Print table
    print(f"{'Penalty':<8} {'Bonus':<7} {'Description':<22} {'Reward':<8} {'Nodes':<6} {'Valid':<6} {'Iters':<7} {'Time':<6}")
    print("-" * 80)
    
    for r in results:
        if not r['success']:
            marker = " ✗ ERROR"
        elif r == best_valid:
            marker = " ✓ BEST"
        elif r == best_raw and not best_valid:
            marker = " ⚠ BEST*"
        else:
            marker = ""
        
        penalty_pct = f"{(1-r['penalty_mult'])*100:.0f}%"
        print(f"{penalty_pct:<8} {r['completion_bonus']:<7.2f} {r['description']:<22} "
              f"{r['raw_reward']:<8} {r['path_length']:<6} "
              f"{'Yes' if r['valid'] else 'No':<6} {r['iterations']:<7} "
              f"{r['time']:<6.2f}{marker}")
    
    # Analysis
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    
    if best_valid:
        print(f"\n✓ Best Valid Configuration:")
        print(f"  Description: {best_valid['description']}")
        print(f"  Penalty: {best_valid['penalty_mult']}× ({(1-best_valid['penalty_mult'])*100:.0f}% penalty)")
        print(f"  Bonus: +{best_valid['completion_bonus']}")
        print(f"  Raw Reward: {best_valid['raw_reward']}")
        print(f"  Path Length: {best_valid['path_length']} nodes")
        print(f"  Cost: {best_valid['cost']:.2f} / {budget}")
    else:
        print("\n⚠️  No valid solutions found!")
    
    if best_raw != best_valid and best_raw:
        print(f"\n⚠  Highest Reward (but invalid):")
        print(f"  Description: {best_raw['description']}")
        print(f"  Raw Reward: {best_raw['raw_reward']}")
        print(f"  (Path incomplete - not usable)")
    
    # Compare with standard values
    standard = [r for r in results if abs(r['penalty_mult'] - 0.7) < 0.01 
                and abs(r['completion_bonus'] - 0.15) < 0.01]
    
    if standard and best_valid:
        std = standard[0]
        if std['success']:
            diff = best_valid['raw_reward'] - std['raw_reward']
            if diff > 0:
                print(f"\n📊 Best config is {diff} points better than standard (0.7×, 0.15)")
                print(f"   Improvement: {diff/std['raw_reward']*100:.1f}%")
            elif diff < 0:
                print(f"\n📊 Standard (0.7×, 0.15) is {abs(diff)} points better than best found")
                print(f"   Standard is {abs(diff)/best_valid['raw_reward']*100:.1f}% better")
            else:
                print(f"\n📊 Best config matches standard (0.7×, 0.15)")
    
    # Patterns
    print("\n" + "=" * 80)
    print("PATTERNS OBSERVED")
    print("=" * 80)
    
    # Analyze penalty impact
    valid_by_penalty = {}
    for r in valid_results:
        p = r['penalty_mult']
        if p not in valid_by_penalty:
            valid_by_penalty[p] = []
        valid_by_penalty[p].append(r['raw_reward'])
    
    if len(valid_by_penalty) > 1:
        print("\nPenalty Impact:")
        for penalty in sorted(valid_by_penalty.keys()):
            avg_reward = sum(valid_by_penalty[penalty]) / len(valid_by_penalty[penalty])
            print(f"  {penalty}× ({(1-penalty)*100:.0f}% penalty): avg reward = {avg_reward:.0f}")
    
    # Path length analysis
    if valid_results:
        avg_path_len = sum(r['path_length'] for r in valid_results) / len(valid_results)
        max_path = max(r['path_length'] for r in valid_results)
        min_path = min(r['path_length'] for r in valid_results)
        
        print(f"\nPath Length Statistics (valid solutions):")
        print(f"  Average: {avg_path_len:.1f} nodes")
        print(f"  Range: {min_path}-{max_path} nodes")
        
        # Correlation with reward
        if len(valid_results) > 2:
            import statistics
            rewards = [r['raw_reward'] for r in valid_results]
            path_lens = [r['path_length'] for r in valid_results]
            
            # Simple correlation indicator
            reward_std = statistics.stdev(rewards) if len(rewards) > 1 else 0
            if reward_std > 0:
                print(f"  Note: Reward varies significantly ({min(rewards)}-{max(rewards)})")
                print(f"        Penalty/bonus choice matters for parallel WU-UCT!")

def test_comparison_with_single_thread():
    """Compare parallel WU-UCT with single-threaded MCTS using same configs"""
    
    from MCTS.mcts_base import MCTSSingleThread
    
    print("\n\n" + "=" * 80)
    print("PARALLEL WU-UCT vs SINGLE-THREADED MCTS")
    print("=" * 80)
    print("\nComparing penalty/bonus sensitivity between implementations")
    print()
    
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    
    # Test a few key configurations
    configs = [
        (0.5, 0.05, "Harsh"),
        (0.7, 0.15, "Standard (new)"),
        (0.8, 0.25, "Lenient"),
    ]
    
    print(f"{'Config':<20} {'Single-Thread':<15} {'Parallel WU-UCT':<15} {'Difference':<12}")
    print("-" * 80)
    
    for penalty_mult, completion_bonus, description in configs:
        # NOTE: This comparison requires manually changing the penalty values
        # in both implementations. For now, we'll show the structure.
        
        # Single-threaded MCTS
        problem_st = OrienteeringProblem(nodes, budget, normalize_rewards=True)
        solver_st = MCTSSingleThread(problem_st, iterations=5000, traditional_mcts=True)
        best_st = solver_st.run()
        reward_st = sum(problem_st.nodes[n].score for n in best_st.get_path())
        
        # Parallel WU-UCT
        problem_wu = OrienteeringProblem(nodes, budget, normalize_rewards=True)
        coordinator_wu = SimpleWUUCT(problem=problem_wu, num_workers=4)
        solution_wu = coordinator_wu.run(max_iterations=5000, time_limit=30.0)
        reward_wu = sum(problem_wu.nodes[n].score for n in solution_wu.path)
        
        diff = reward_wu - reward_st
        diff_pct = (diff / reward_st * 100) if reward_st > 0 else 0
        
        print(f"{description:<20} {reward_st:<15} {reward_wu:<15} "
              f"{diff:+d} ({diff_pct:+.1f}%)")
    
    print("\n" + "-" * 80)
    print("NOTE: Currently using standard penalties (0.7×, 0.15)")
    print("      To test other configs, modify the values in simple_wu_worker.py")

if __name__ == "__main__":
    print("⚠️  IMPORTANT SETUP NOTE ⚠️")
    print("-" * 80)
    print("This test requires manually changing penalty/bonus values in:")
    print("  Simple_WU/simple_wu_worker.py (lines ~271-279)")
    print()
    print("Current values in code: penalty=0.7×, bonus=0.15")
    print()
    print("For each test config, you need to:")
    print("  1. Edit simple_wu_worker.py with test values")
    print("  2. Run this script")
    print("  3. Record results")
    print("  4. Repeat for next config")
    print()
    print("Alternatively, we'll test with current values and provide analysis.")
    print("-" * 80)
    print()
    
    response = input("Continue with current values (0.7×, 0.15)? [Y/n]: ")
    if response.lower() == 'n':
        print("Exiting. Modify values in simple_wu_worker.py and re-run.")
        sys.exit(0)
    
    print("\nProceeding with current values only...")
    print()
    
    # For now, just test current values
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    
    problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
    
    print("Testing current configuration (0.7×, 0.15)...")
    coordinator = SimpleWUUCT(problem=problem, num_workers=4)
    solution = coordinator.run(max_iterations=5000, time_limit=30.0)
    
    raw_reward = sum(problem.nodes[node_id].score for node_id in solution.path)
    
    print(f"\nResults:")
    print(f"  Raw reward: {raw_reward}")
    print(f"  Path length: {len(solution.path)} nodes")
    print(f"  Cost: {solution.cost_so_far:.2f} / {budget}")
    print(f"  Valid: {solution.is_terminal()}")
    print(f"  Iterations: {coordinator.global_iteration}")
    
    print("\n" + "=" * 80)
    print("To test other penalty/bonus configurations:")
    print("=" * 80)
    print()
    print("Create a modified version of simple_wu_worker.py that accepts")
    print("penalty_mult and completion_bonus as parameters, or manually")
    print("test each configuration by editing the file.")
    print()
    print("Suggested test matrix:")
    print("  Harsh:         penalty=0.5×, bonus=0.05")
    print("  Moderate:      penalty=0.7×, bonus=0.15  ← Current")
    print("  Lenient:       penalty=0.8×, bonus=0.25")
    print("  Very Lenient:  penalty=0.9×, bonus=0.30")
