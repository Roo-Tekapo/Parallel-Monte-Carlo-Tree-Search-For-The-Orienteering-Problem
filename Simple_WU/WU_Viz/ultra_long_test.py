#!/usr/bin/env python3
"""
WU-UCT Grid Visualization - ULTRA LONG Test

This test runs 200,000 iterations with slower updates so you can 
DEFINITELY see the workers exploring. Should run for 30-60 seconds.
"""

import sys
import os
import math

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
simple_wu_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(simple_wu_dir)
sys.path.extend([project_root, simple_wu_dir])

from wu_uct_grid_viz import WUUCTGridVisualizer


def ultra_long_test():
    """
    ULTRA long test with 200,000 iterations.
    This will run for 30-60 seconds - you'll definitely see the action!
    """
    print("=" * 70)
    print("🚀🚀🚀 WU-UCT Grid Visualization - ULTRA LONG TEST 🚀🚀🚀")
    print("=" * 70)
    print()
    print("⏱️  This test runs 200,000 iterations (~30-60 seconds)")
    print()
    print("You will DEFINITELY see:")
    print()
    print("  🔴 Red dashed lines = Worker 0 exploring different paths")
    print("  🔵 Teal dashed lines = Worker 1 exploring different paths")
    print("  🔵 Blue dashed lines = Worker 2 exploring different paths")
    print("  🟢 Green dashed lines = Worker 3 exploring different paths")
    print()
    print("  🟡 Gold solid line = Current best solution (updates as algorithm improves)")
    print()
    print("Watch closely:")
    print("  • Dashed worker lines will change and move around the grid")
    print("  • Statistics will update showing progress")
    print("  • Best path (gold) may change as better solutions are found")
    print("  • Tree size will grow from ~100 to ~400+ nodes")
    print()
    print("💡 TIP: Press 'P' to toggle worker paths ON/OFF during the run")
    print()
    print("Starting... Window will open in a moment!")
    print("=" * 70)
    print()
    
    visualizer = WUUCTGridVisualizer(
        problem_path="../../OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt",
        iterations=200000,  # ULTRA LONG - 200k iterations!
        num_workers=4,      # 4 parallel workers
        exploration_constant=math.sqrt(2),
        max_edge_distance=1.42,
        update_interval=150,  # Slightly slower updates (every 150ms)
        grid_size=(16, 10)
    )
    
    return visualizer.run()


if __name__ == "__main__":
    try:
        ani = ultra_long_test()
    except KeyboardInterrupt:
        print("\n✅ Test interrupted - but you should have seen the workers!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
