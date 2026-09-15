#!/usr/bin/env python3
"""
Non-visual test to verify diverse exploration behavior
Prints statistics about node exploration diversity
"""

import sys
import os
import math
from collections import defaultdict

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Simple_WU.orienteering_adapter import OrienteeringProblem
from Simple_WU.simple_wu_coordinator import SimpleWUUCT


def analyze_tree_diversity(node, depth=0, stats=None):
    """Recursively analyze tree to measure exploration diversity."""
    if stats is None:
        stats = {
            'total_nodes': 0,
            'depth_distribution': defaultdict(int),
            'visit_distribution': [],
            'max_depth': 0,
            'terminal_nodes': 0
        }
    
    stats['total_nodes'] += 1
    stats['depth_distribution'][depth] += 1
    stats['max_depth'] = max(stats['max_depth'], depth)
    stats['visit_distribution'].append(node.visits)
    
    # Check if this is a terminal node (reaches end)
    if hasattr(node.state, 'is_terminal') and node.state.is_terminal():
        stats['terminal_nodes'] += 1
    
    # Recurse on children
    for child in node.children:
        analyze_tree_diversity(child, depth + 1, stats)
    
    return stats


def test_exploration_diversity():
    """Test exploration diversity with the diversity bonus fix."""
    print("🔍 Testing WU-UCT Exploration Diversity")
    print("=" * 60)
    
    # Load the long grid problem
    problem_path = os.path.join(project_root, "OP_Benchmark_Set", "grid_sample", "grid_10x10_long_50.txt")
    nodes, budget = OrienteeringProblem.load_problem(problem_path)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)
    
    print(f"Problem: {len(nodes)} nodes, budget={budget}")
    print(f"Running WU-UCT with 4 workers, 5000 iterations...")
    print()
    
    # Run WU-UCT
    wu_uct = SimpleWUUCT(
        problem=problem,
        num_workers=4,
        exploration_constant=math.sqrt(2),
        max_distance=1.42
    )
    
    best_solution = wu_uct.run(max_iterations=5000, verbose=True)
    
    print("\n" + "=" * 60)
    print("📊 Tree Exploration Analysis")
    print("=" * 60)
    
    # Analyze tree diversity
    stats = analyze_tree_diversity(wu_uct.root)
    
    print(f"\nTotal nodes in tree: {stats['total_nodes']}")
    print(f"Maximum depth: {stats['max_depth']}")
    print(f"Terminal nodes found: {stats['terminal_nodes']}")
    
    print(f"\nDepth distribution:")
    for depth in sorted(stats['depth_distribution'].keys()):
        count = stats['depth_distribution'][depth]
        print(f"  Depth {depth}: {count} nodes")
    
    # Analyze visit distribution
    visits = sorted(stats['visit_distribution'], reverse=True)
    print(f"\nVisit distribution:")
    print(f"  Most visited node: {visits[0]} visits")
    print(f"  Median visits: {visits[len(visits)//2]} visits")
    print(f"  Least visited node: {visits[-1]} visits")
    
    # Calculate Gini coefficient for visit inequality
    n = len(visits)
    if n > 0:
        sorted_visits = sorted(visits)
        cumsum = sum((i + 1) * v for i, v in enumerate(sorted_visits))
        total_visits = sum(sorted_visits)
        if total_visits > 0:
            gini = (2 * cumsum) / (n * total_visits) - (n + 1) / n
            print(f"  Gini coefficient (visit inequality): {gini:.3f}")
            print(f"    (0 = perfectly equal, 1 = perfectly unequal)")
    
    # Count nodes with different visit ranges
    low_visit = sum(1 for v in visits if v < 10)
    medium_visit = sum(1 for v in visits if 10 <= v < 50)
    high_visit = sum(1 for v in visits if v >= 50)
    
    print(f"\nVisit range distribution:")
    print(f"  Low visits (<10): {low_visit} nodes ({100*low_visit/len(visits):.1f}%)")
    print(f"  Medium visits (10-49): {medium_visit} nodes ({100*medium_visit/len(visits):.1f}%)")
    print(f"  High visits (>=50): {high_visit} nodes ({100*high_visit/len(visits):.1f}%)")
    
    print(f"\n✅ Best solution found:")
    print(f"   Path: {best_solution.path}")
    print(f"   Reward: {best_solution.reward_so_far}")
    print(f"   Cost: {best_solution.cost_so_far:.2f} / {budget}")
    
    # Check if we have diverse exploration
    print(f"\n🎯 Diversity Assessment:")
    if stats['total_nodes'] > 100:
        print(f"   ✓ Good tree size: {stats['total_nodes']} nodes")
    else:
        print(f"   ⚠ Small tree size: {stats['total_nodes']} nodes (expected >100)")
    
    if gini < 0.7:
        print(f"   ✓ Good visit distribution (Gini={gini:.3f})")
    else:
        print(f"   ⚠ Unequal visit distribution (Gini={gini:.3f})")
    
    if low_visit < 0.5 * len(visits):
        print(f"   ✓ Most nodes well-explored (<50% with <10 visits)")
    else:
        print(f"   ⚠ Many under-explored nodes ({100*low_visit/len(visits):.1f}% with <10 visits)")


if __name__ == "__main__":
    try:
        test_exploration_diversity()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
