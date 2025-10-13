#!/usr/bin/env python3
"""
Deep dive into WU-UCT formula values during selection.

This test examines the actual numerical values of:
- Exploitation term: V_c = total_reward / N_c  
- Exploration term: β * sqrt(2*log(N_n + O_n) / (N_c + O_c))
- Total WU-UCT value

To understand why workers still converge despite virtual loss.
"""

import sys
import os
import math

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.extend([project_root, current_dir])

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from UCT.wu_uct_node import WUUCTNode
from simple_wu_coordinator import SimpleWUUCT


def analyze_uct_values_at_root(root, exploration_constant=math.sqrt(2)):
    """Analyze UCT values for root children to see the effect of virtual loss."""
    
    if not root.children:
        print("No children to analyze")
        return
    
    print("\n" + "=" * 80)
    print("WU-UCT VALUE BREAKDOWN AT ROOT")
    print("=" * 80)
    
    N_parent = root.visits
    O_parent = root.pending_simulations
    
    print(f"\nParent (Root) Stats:")
    print(f"  N_parent (actual visits): {N_parent}")
    print(f"  O_parent (pending sims): {O_parent}")
    print(f"  Total (N + O): {N_parent + O_parent}")
    
    if N_parent + O_parent == 0:
        print("\n⚠ Parent has no visits yet")
        return
    
    log_term = math.log(N_parent + O_parent)
    print(f"  log(N_parent + O_parent): {log_term:.4f}")
    
    print(f"\nChildren Analysis (sorted by WU-UCT value):")
    print("-" * 80)
    
    # Calculate WU-UCT for each child
    child_data = []
    for i, child in enumerate(root.children):
        N_child = child.visits
        O_child = child.pending_simulations
        denominator = N_child + O_child
        
        if N_child > 0:
            exploitation = child.total_reward / N_child
        else:
            exploitation = 0.0
        
        if denominator > 0:
            exploration = exploration_constant * math.sqrt(2 * log_term / denominator)
        else:
            exploration = float('inf')
        
        wu_uct_value = exploitation + exploration
        
        child_data.append({
            'index': i,
            'N': N_child,
            'O': O_child,
            'total': denominator,
            'reward': child.total_reward,
            'exploitation': exploitation,
            'exploration': exploration,
            'wu_uct': wu_uct_value,
            'path': child.state.path[-1] if child.state.path else None
        })
    
    # Sort by WU-UCT value (descending)
    child_data.sort(key=lambda x: x['wu_uct'], reverse=True)
    
    print(f"{'Rank':<5} {'Node':<8} {'N':<6} {'O':<6} {'N+O':<8} "
          f"{'Exploit':<10} {'Explore':<10} {'WU-UCT':<10} {'Selected?':<10}")
    print("-" * 80)
    
    for rank, data in enumerate(child_data, 1):
        is_best = "⭐" if rank == 1 else ""
        print(f"{rank:<5} {str(data['path']):<8} {data['N']:<6} {data['O']:<6} {data['total']:<8} "
              f"{data['exploitation']:<10.4f} {data['exploration']:<10.4f} "
              f"{data['wu_uct']:<10.4f} {is_best:<10}")
    
    # Key insights
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    
    best_child = child_data[0]
    second_child = child_data[1] if len(child_data) > 1 else None
    
    print(f"\n1️⃣ Most Selected Child (Node {best_child['path']}):")
    print(f"   - Exploitation: {best_child['exploitation']:.4f}")
    print(f"   - Exploration: {best_child['exploration']:.4f}")
    print(f"   - WU-UCT Total: {best_child['wu_uct']:.4f}")
    print(f"   - Has {best_child['O']} pending simulations (virtual loss)")
    
    if second_child:
        print(f"\n2️⃣ Second Best Child (Node {second_child['path']}):")
        print(f"   - Exploitation: {second_child['exploitation']:.4f}")
        print(f"   - Exploration: {second_child['exploration']:.4f}")
        print(f"   - WU-UCT Total: {second_child['wu_uct']:.4f}")
        print(f"   - Has {second_child['O']} pending simulations")
        
        gap = best_child['wu_uct'] - second_child['wu_uct']
        print(f"\n   📊 Gap between best and second: {gap:.4f}")
        
        if gap > 1.0:
            print(f"   ⚠ Large gap! Best child dominates even with virtual loss.")
        elif gap > 0.1:
            print(f"   ℹ️  Moderate gap. Virtual loss has some effect.")
        else:
            print(f"   ✓ Small gap. Good diversity potential.")
    
    # Check if virtual loss is significant
    if best_child['O'] > 0:
        # Calculate what WU-UCT would be without virtual loss
        N_only = best_child['N']
        if N_only > 0:
            exploit_no_vl = best_child['reward'] / N_only
            explore_no_vl = exploration_constant * math.sqrt(2 * log_term / N_only)
            wu_uct_no_vl = exploit_no_vl + explore_no_vl
            
            vl_effect = wu_uct_no_vl - best_child['wu_uct']
            print(f"\n3️⃣ Virtual Loss Effect on Best Child:")
            print(f"   - WU-UCT without virtual loss: {wu_uct_no_vl:.4f}")
            print(f"   - WU-UCT with virtual loss: {best_child['wu_uct']:.4f}")
            print(f"   - Reduction: {vl_effect:.4f} ({100*vl_effect/wu_uct_no_vl:.1f}%)")
            
            if vl_effect < 0.1:
                print(f"   ⚠ Virtual loss has minimal effect (<0.1)")
            elif vl_effect < 0.5:
                print(f"   ℹ️  Virtual loss has moderate effect")
            else:
                print(f"   ✓ Virtual loss has strong effect")


def test_wu_uct_formula():
    """Run WU-UCT and analyze the formula values."""
    
    print("🔬 WU-UCT Formula Deep Dive")
    print("=" * 80)
    print("Analyzing the actual numerical values in the WU-UCT formula")
    print("to understand why workers converge despite virtual loss.")
    print("=" * 80)
    
    # Load problem
    problem_path = "../OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt"
    nodes, budget = OrienteeringProblem.load_problem(problem_path)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)
    
    print(f"\nProblem: {len(nodes)} nodes, budget={budget}")
    
    # Run WU-UCT for a short time
    wu_uct = SimpleWUUCT(
        problem=problem,
        num_workers=4,
        exploration_constant=math.sqrt(2),
        max_distance=1.42
    )
    
    print(f"\nRunning WU-UCT with 4 workers, 400 iterations...")
    best_solution = wu_uct.run(max_iterations=400, verbose=False)
    
    # Analyze the formula values at the root
    analyze_uct_values_at_root(wu_uct.root, exploration_constant=math.sqrt(2))
    
    print("\n" + "=" * 80)
    print("🎯 RECOMMENDATIONS")
    print("=" * 80)
    print()
    print("Based on the analysis above:")
    print()
    print("1. If the gap between best and second child is large (>1.0):")
    print("   → Increase exploration_constant to encourage more exploration")
    print()
    print("2. If virtual loss effect is minimal (<10%):")
    print("   → The virtual loss weight might need to be increased")
    print("   → Or the exploitation term is too dominant")
    print()
    print("3. If one child has >>90% of visits:")
    print("   → The problem may require progressive widening or forced diversity")


if __name__ == "__main__":
    try:
        test_wu_uct_formula()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
