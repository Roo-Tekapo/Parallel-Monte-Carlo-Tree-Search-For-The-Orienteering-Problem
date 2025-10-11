#!/usr/bin/env python3
"""
Quick test for the WU-UCT Grid Visualization
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


def quick_test():
    """Quick test with fewer iterations."""
    print("🚀 Quick WU-UCT Grid Visualization Test")
    print("=" * 40)
    
    visualizer = WUUCTGridVisualizer(
        problem_path="../../OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt",
        iterations=10000,  # More iterations to see workers in action
        num_workers=4,     # 4 workers for good visual diversity
        exploration_constant=math.sqrt(2),
        max_edge_distance=1.42,
        update_interval=100,  # Fast updates to see workers in action
        grid_size=(14, 9)
    )
    
    return visualizer.run()


if __name__ == "__main__":
    try:
        ani = quick_test()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user.")
    except Exception as e:
        print(f"❌ Error: {e}")