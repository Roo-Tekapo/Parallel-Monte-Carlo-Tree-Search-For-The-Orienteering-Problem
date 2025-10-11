#!/usr/bin/env python3
"""
Test WU-UCT on long grid to verify diverse exploration
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


def test_long_grid():
    """Test with long grid to see diverse exploration."""
    print("🚀 Testing WU-UCT on Long Grid (50 nodes)")
    print("=" * 50)
    print("This test should show workers exploring alternative paths")
    print("even after finding good solutions to the end node.")
    print("=" * 50)
    
    visualizer = WUUCTGridVisualizer(
        problem_path="../../OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt",
        iterations=5000,   # Enough iterations to see behavior
        num_workers=4,     # 4 workers for diverse exploration
        exploration_constant=math.sqrt(2),
        max_edge_distance=1.42,
        update_interval=100,
        grid_size=(16, 10)
    )
    
    return visualizer.run()


if __name__ == "__main__":
    try:
        ani = test_long_grid()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
