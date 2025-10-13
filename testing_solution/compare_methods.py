"""
Comprehensive comparison tool: MCTS vs Optimal vs Greedy
Tests your MCTS implementation against optimal and baseline solutions
"""

import sys
import time
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from orienteering.orienteering import OrienteeringProblem
from testing_solution.validate_solution import validate_solution, greedy_nearest_neighbor, print_validation_report
from testing_solution.solve_optimal import solve_best_path
from testing_solution.benchmark_solution import run_multiple_trials, print_statistics_report


def compare_all_methods(problem: OrienteeringProblem, problem_name: str, 
                        mcts_iterations: int = 10000, num_trials: int = 5,
                        optimal_time_limit: int = 60):
    """
    Compare MCTS, Optimal solver, and Greedy baseline on a problem instance.
    """
    print("\n" + "="*80)
    print(f"COMPREHENSIVE COMPARISON: {problem_name}")
    print("="*80)
    print(f"Problem: {problem.num_nodes} nodes, Budget: {problem.budget}")
    print(f"MCTS iterations: {mcts_iterations}, Trials: {num_trials}")
    print("="*80)
    
    results = {}
    
    # 1. Find optimal/best-known solution
    print("\n[1/3] Finding optimal/best-known solution...")
    print("-"*80)
    try:
        best_path, best_reward, method_desc = solve_best_path(
            problem, method="auto", max_time_seconds=optimal_time_limit
        )
        results['Optimal/Best'] = {
            'path': best_path,
            'reward': best_reward,
            'method': method_desc,
            'validation': validate_solution(problem, best_path)
        }
        print(f"✓ {method_desc}")
        print(f"  Best reward: {best_reward:.0f}")
    except Exception as e:
        print(f"✗ Failed to find optimal: {e}")
        results['Optimal/Best'] = None
    
    # 2. Run greedy baseline
    print("\n[2/3] Testing greedy baseline...")
    print("-"*80)
    try:
        greedy_path, greedy_reward = greedy_nearest_neighbor(problem)
        results['Greedy'] = {
            'path': greedy_path,
            'reward': greedy_reward,
            'validation': validate_solution(problem, greedy_path)
        }
        print(f"✓ Greedy baseline")
        print(f"  Reward: {greedy_reward:.0f}")
    except Exception as e:
        print(f"✗ Greedy failed: {e}")
        results['Greedy'] = None
    
    # 3. Run MCTS (if available)
    print("\n[3/3] Testing MCTS solver (if available)...")
    print("-"*80)
    
    # Try to import and run MCTS
    mcts_available = False
    mcts_paths = [
        ('MCTS.wu_uct_demo', 'run_wu_uct'),
        ('MCTS.mcts_single_thread', 'run_mcts'),
        ('UCT.uct_single_thread', 'run_uct'),
    ]
    
    for module_name, func_name in mcts_paths:
        try:
            module = __import__(module_name, fromlist=[func_name])
            mcts_func = getattr(module, func_name)
            print(f"Found MCTS solver: {module_name}.{func_name}")
            
            # Create wrapper
            def mcts_solver(prob):
                result = mcts_func(prob, iterations=mcts_iterations)
                # Handle different return formats
                if isinstance(result, dict):
                    path = result.get('path') or result.get('best_path')
                    reward = result.get('reward') or result.get('best_reward')
                elif isinstance(result, tuple):
                    path, reward = result[0], result[1]
                else:
                    raise ValueError(f"Unexpected MCTS return format: {type(result)}")
                return path, reward
            
            # Run trials
            stats = run_multiple_trials(problem, mcts_solver, num_trials, "MCTS")
            results['MCTS'] = {
                'stats': stats,
                'path': stats['best_path'],
                'reward': stats['max_reward']
            }
            mcts_available = True
            break
        except (ImportError, AttributeError) as e:
            continue
    
    if not mcts_available:
        print("✗ No MCTS solver found in common locations")
        print("  Checked: MCTS.wu_uct_demo, MCTS.mcts_single_thread, UCT.uct_single_thread")
        print("  You can manually test by importing your solver.")
        results['MCTS'] = None
    
    # Print comparison table
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    
    print(f"\n{'Method':<20} {'Reward':<12} {'Valid':<8} {'Notes'}")
    print("-"*80)
    
    if results.get('Optimal/Best'):
        opt = results['Optimal/Best']
        valid = "✓" if opt['validation']['is_valid'] else "✗"
        print(f"{'Optimal/Best':<20} {opt['reward']:<12.0f} {valid:<8} {opt['method'][:40]}")
    
    if results.get('MCTS'):
        mcts = results['MCTS']
        stats = mcts['stats']
        mean_str = f"{stats['mean_reward']:.1f}±{stats['std_reward']:.1f}"
        print(f"{'MCTS (mean)':<20} {mean_str:<12} {'✓':<8} {num_trials} trials")
        print(f"{'MCTS (best)':<20} {stats['max_reward']:<12.0f} {'✓':<8} Best of {num_trials} trials")
    
    if results.get('Greedy'):
        greedy = results['Greedy']
        valid = "✓" if greedy['validation']['is_valid'] else "✗"
        print(f"{'Greedy Baseline':<20} {greedy['reward']:<12.0f} {valid:<8} Deterministic")
    
    # Calculate gaps
    print("\n" + "="*80)
    print("QUALITY METRICS")
    print("="*80)
    
    if results.get('Optimal/Best'):
        optimal_reward = results['Optimal/Best']['reward']
        
        if results.get('MCTS'):
            mcts_best = results['MCTS']['reward']
            mcts_mean = results['MCTS']['stats']['mean_reward']
            gap_best = ((optimal_reward - mcts_best) / optimal_reward * 100) if optimal_reward > 0 else 0
            gap_mean = ((optimal_reward - mcts_mean) / optimal_reward * 100) if optimal_reward > 0 else 0
            print(f"\nMCTS Best vs Optimal:")
            print(f"  Optimality gap: {gap_best:.2f}%")
            print(f"  Reward ratio: {(mcts_best/optimal_reward*100):.1f}% of optimal")
            print(f"\nMCTS Mean vs Optimal:")
            print(f"  Optimality gap: {gap_mean:.2f}%")
            print(f"  Reward ratio: {(mcts_mean/optimal_reward*100):.1f}% of optimal")
        
        if results.get('Greedy'):
            greedy_reward = results['Greedy']['reward']
            gap = ((optimal_reward - greedy_reward) / optimal_reward * 100) if optimal_reward > 0 else 0
            print(f"\nGreedy vs Optimal:")
            print(f"  Optimality gap: {gap:.2f}%")
            print(f"  Reward ratio: {(greedy_reward/optimal_reward*100):.1f}% of optimal")
    
    if results.get('MCTS') and results.get('Greedy'):
        mcts_best = results['MCTS']['reward']
        greedy_reward = results['Greedy']['reward']
        improvement = ((mcts_best - greedy_reward) / greedy_reward * 100) if greedy_reward > 0 else 0
        print(f"\nMCTS Best vs Greedy:")
        print(f"  Improvement: {improvement:+.2f}%")
    
    print("\n" + "="*80)
    
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compare_methods.py <problem_file> [mcts_iterations] [num_trials] [optimal_time]")
        print("\nExamples:")
        print("  python compare_methods.py OP_Benchmark_Set/grid_sample/grid_10x10_easy_20.txt")
        print("  python compare_methods.py OP_Benchmark_Set/set_64_1/set_64_1_80.txt 50000 10 120")
        print("\nDefault values:")
        print("  mcts_iterations = 10000")
        print("  num_trials = 5")
        print("  optimal_time = 60 seconds")
        sys.exit(1)
    
    problem_file = sys.argv[1]
    mcts_iterations = int(sys.argv[2]) if len(sys.argv) >= 3 else 10000
    num_trials = int(sys.argv[3]) if len(sys.argv) >= 4 else 5
    optimal_time = int(sys.argv[4]) if len(sys.argv) >= 5 else 60
    
    # Load problem
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)
    
    # Run comparison
    results = compare_all_methods(
        problem, 
        problem_file,
        mcts_iterations=mcts_iterations,
        num_trials=num_trials,
        optimal_time_limit=optimal_time
    )
    
    # Print detailed reports for best solutions
    print("\n" + "="*80)
    print("DETAILED VALIDATION REPORTS")
    print("="*80)
    
    if results.get('Optimal/Best'):
        print_validation_report(problem, results['Optimal/Best']['path'], "Optimal/Best Solution")
    
    if results.get('MCTS'):
        print_validation_report(problem, results['MCTS']['path'], "MCTS Best Solution")
    
    if results.get('Greedy'):
        print_validation_report(problem, results['Greedy']['path'], "Greedy Baseline")
