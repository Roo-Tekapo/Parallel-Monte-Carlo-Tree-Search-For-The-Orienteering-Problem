"""
Test the effectiveness of the reward structure changes.

This script compares:
1. END_NODE reaching behavior
2. Solution quality (reward collection)
3. Path characteristics (complete vs incomplete)
4. Exploration patterns

Tests both VL and WU-UCT implementations.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from orienteering.orienteering_traditional import OrienteeringProblem, END_NODE
from VL.vl_coordinator import VirtualLossMCTS
from Simple_WU.simple_wu_coordinator import SimpleWUUCT
import time


def test_algorithm(name: str, problem_file: str, iterations: int = 10000, num_runs: int = 5):
    """Test an algorithm multiple times and collect statistics."""
    
    print(f"\n{'='*80}")
    print(f"Testing {name}")
    print(f"{'='*80}")
    
    results = []
    
    for run in range(num_runs):
        print(f"\nRun {run + 1}/{num_runs}...")
        
        # Load problem
        nodes, budget = OrienteeringProblem.load_problem(problem_file)
        problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
        
        # Run algorithm
        start_time = time.time()
        
        if name == "VL":
            algorithm = VirtualLossMCTS(
                problem=problem,
                num_workers=4,
                exploration_constant=1.414,
                virtual_loss_value=1.0
            )
            best_solution = algorithm.run(max_iterations=iterations, verbose=False)
            root = algorithm.root
        else:  # WU-UCT
            algorithm = SimpleWUUCT(
                problem=problem,
                num_workers=4,
                exploration_constant=1.414
            )
            best_solution = algorithm.run(max_iterations=iterations, verbose=False)
            root = algorithm.root
        
        elapsed = time.time() - start_time
        
        # Collect statistics
        reaches_end = best_solution.path[-1] == END_NODE
        raw_score = sum(problem.nodes[node_id].score for node_id in best_solution.path)
        
        # Count terminal nodes in tree (sample depth)
        def count_terminal_and_total(node, depth=0, max_depth=15):
            if depth > max_depth:
                return 0, 0
            terminal = 1 if node.state.is_terminal() else 0
            total = 1
            for child in node.children:
                t, tot = count_terminal_and_total(child, depth + 1, max_depth)
                terminal += t
                total += tot
            return terminal, total
        
        terminal_nodes, total_nodes = count_terminal_and_total(root)
        terminal_pct = (terminal_nodes / total_nodes * 100) if total_nodes > 0 else 0
        
        result = {
            'run': run + 1,
            'reaches_end': reaches_end,
            'path_length': len(best_solution.path),
            'normalized_reward': best_solution.reward_so_far,
            'raw_score': raw_score,
            'cost': best_solution.cost_so_far,
            'budget': budget,
            'budget_used_pct': (best_solution.cost_so_far / budget * 100),
            'terminal_nodes': terminal_nodes,
            'total_nodes': total_nodes,
            'terminal_pct': terminal_pct,
            'root_visits': root.visits,
            'elapsed_time': elapsed
        }
        
        results.append(result)
        
        print(f"  Path: {' -> '.join(map(str, best_solution.path[:5]))}...{' -> '.join(map(str, best_solution.path[-3:]))}")
        print(f"  Reaches END: {'YES' if reaches_end else 'NO'}")
        print(f"  Raw score: {raw_score}")
        print(f"  Normalized: {best_solution.reward_so_far:.4f}")
        print(f"  Budget: {best_solution.cost_so_far:.2f}/{budget:.2f} ({result['budget_used_pct']:.1f}%)")
        print(f"  Terminal nodes: {terminal_nodes}/{total_nodes} ({terminal_pct:.1f}%)")
    
    return results


def analyze_results(name: str, results: list):
    """Analyze and print summary statistics."""
    
    print(f"\n{'='*80}")
    print(f"{name} - Summary Statistics ({len(results)} runs)")
    print(f"{'='*80}")
    
    # Calculate averages
    reaches_end_count = sum(1 for r in results if r['reaches_end'])
    avg_raw_score = sum(r['raw_score'] for r in results) / len(results)
    avg_normalized = sum(r['normalized_reward'] for r in results) / len(results)
    avg_path_length = sum(r['path_length'] for r in results) / len(results)
    avg_budget_used = sum(r['budget_used_pct'] for r in results) / len(results)
    avg_terminal_pct = sum(r['terminal_pct'] for r in results) / len(results)
    avg_time = sum(r['elapsed_time'] for r in results) / len(results)
    
    # Find best
    best_raw = max(results, key=lambda r: r['raw_score'])
    best_normalized = max(results, key=lambda r: r['normalized_reward'])
    
    print(f"\nPath Completion:")
    print(f"  Reaches END: {reaches_end_count}/{len(results)} runs ({reaches_end_count/len(results)*100:.1f}%)")
    print(f"  Avg path length: {avg_path_length:.1f} nodes")
    
    print(f"\nReward Collection:")
    print(f"  Avg raw score: {avg_raw_score:.1f}")
    print(f"  Avg normalized: {avg_normalized:.4f}")
    print(f"  Best raw score: {best_raw['raw_score']} (run {best_raw['run']})")
    print(f"  Best normalized: {best_normalized['normalized_reward']:.4f} (run {best_normalized['run']})")
    
    print(f"\nBudget Usage:")
    print(f"  Avg budget used: {avg_budget_used:.1f}%")
    
    print(f"\nExploration:")
    print(f"  Avg terminal nodes: {avg_terminal_pct:.1f}%")
    
    print(f"\nPerformance:")
    print(f"  Avg time: {avg_time:.2f}s")
    
    return {
        'name': name,
        'reaches_end_rate': reaches_end_count / len(results),
        'avg_raw_score': avg_raw_score,
        'avg_normalized': avg_normalized,
        'avg_terminal_pct': avg_terminal_pct,
        'best_raw_score': best_raw['raw_score']
    }


def compare_algorithms(vl_stats: dict, wu_stats: dict):
    """Compare the two algorithms."""
    
    print(f"\n{'='*80}")
    print("COMPARISON: VL vs WU-UCT")
    print(f"{'='*80}")
    
    print(f"\nCompletion Rate:")
    print(f"  VL:     {vl_stats['reaches_end_rate']*100:.1f}%")
    print(f"  WU-UCT: {wu_stats['reaches_end_rate']*100:.1f}%")
    
    print(f"\nAverage Raw Score:")
    print(f"  VL:     {vl_stats['avg_raw_score']:.1f}")
    print(f"  WU-UCT: {wu_stats['avg_raw_score']:.1f}")
    diff = wu_stats['avg_raw_score'] - vl_stats['avg_raw_score']
    print(f"  Difference: {diff:+.1f} ({diff/vl_stats['avg_raw_score']*100:+.1f}%)")
    
    print(f"\nBest Raw Score:")
    print(f"  VL:     {vl_stats['best_raw_score']}")
    print(f"  WU-UCT: {wu_stats['best_raw_score']}")
    
    print(f"\nTerminal Node Exploration:")
    print(f"  VL:     {vl_stats['avg_terminal_pct']:.1f}%")
    print(f"  WU-UCT: {wu_stats['avg_terminal_pct']:.1f}%")
    
    print(f"\n{'='*80}")
    print("KEY FINDINGS:")
    print(f"{'='*80}")
    
    if vl_stats['avg_raw_score'] > wu_stats['avg_raw_score'] * 1.05:
        print("✓ VL finds higher-reward paths on average")
    elif wu_stats['avg_raw_score'] > vl_stats['avg_raw_score'] * 1.05:
        print("✓ WU-UCT finds higher-reward paths on average")
    else:
        print("≈ Both algorithms perform similarly")
    
    if vl_stats['reaches_end_rate'] > 0.8 or wu_stats['reaches_end_rate'] > 0.8:
        print("⚠ High completion rate - may still be biased toward reaching END")
    elif vl_stats['reaches_end_rate'] < 0.2 and wu_stats['reaches_end_rate'] < 0.2:
        print("✓ Low completion rate - properly evaluating incomplete high-reward paths")
    else:
        print("≈ Moderate completion rate - balanced exploration")
    
    if vl_stats['avg_terminal_pct'] < 5 or wu_stats['avg_terminal_pct'] < 5:
        print("⚠ Very low terminal exploration - may not be considering completion enough")
    elif vl_stats['avg_terminal_pct'] > 30 or wu_stats['avg_terminal_pct'] > 30:
        print("⚠ Very high terminal exploration - may be over-prioritizing completion")
    else:
        print("✓ Reasonable terminal exploration - balanced approach")


def main():
    """Main test function."""
    
    print("="*80)
    print("REWARD STRUCTURE EFFECTIVENESS TEST")
    print("="*80)
    print("\nThis test evaluates the changes made to:")
    print("1. END_NODE availability (neighbors only)")
    print("2. Removed harsh incomplete path penalties")
    print("3. Reduced completion bonus (0.15→0.05)")
    print("\nExpected outcomes:")
    print("- Paths respect graph structure (END only from neighbors)")
    print("- High-reward incomplete paths can beat low-reward complete paths")
    print("- Terminal exploration is reasonable (not 0%, not 100%)")
    print("- Solution quality focuses on reward collection")
    
    problem_file = 'OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt'
    iterations = 10000
    num_runs = 5
    
    # Test VL
    vl_results = test_algorithm("VL", problem_file, iterations, num_runs)
    vl_stats = analyze_results("VL", vl_results)
    
    # Test WU-UCT
    wu_results = test_algorithm("WU-UCT", problem_file, iterations, num_runs)
    wu_stats = analyze_results("WU-UCT", wu_results)
    
    # Compare
    compare_algorithms(vl_stats, wu_stats)
    
    print(f"\n{'='*80}")
    print("TEST COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
