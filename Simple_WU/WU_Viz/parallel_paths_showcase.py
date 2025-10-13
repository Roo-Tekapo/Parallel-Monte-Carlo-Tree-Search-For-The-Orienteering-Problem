#!/usr/bin/env python3
"""
WU-UCT Grid Visualization - Parallel Worker Path Showcase

This demo is specifically designed to show the parallel worker path tracking
feature of the grid visualization, where you can see each worker exploring
different parts of the solution space in real-time.

Each worker is assigned a unique color and their current exploration path
is drawn with dashed lines on the grid.
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


def showcase_parallel_paths():
    """
    Showcase parallel worker path tracking with optimal settings
    for visual observation.
    """
    print("=" * 60)
    print("🎨 WU-UCT Parallel Worker Path Visualization")
    print("=" * 60)
    print()
    print("This visualization shows:")
    print("  • Each worker exploring different paths (colored dashed lines)")
    print("  • Real-time algorithm progress and statistics")
    print("  • The best solution found (golden solid line with arrows)")
    print("  • Worker status and completion progress")
    print()
    print("🎮 Interactive Controls:")
    print("  • Press 'P' to toggle worker path display ON/OFF")
    print()
    print("📊 Visual Guide:")
    print("  • Red dashed line   = Worker 0's current exploration")
    print("  • Teal dashed line  = Worker 1's current exploration")
    print("  • Blue dashed line  = Worker 2's current exploration")
    print("  • Green dashed line = Worker 3's current exploration")
    print("  • Gold solid line   = Best path found (with arrows)")
    print()
    print("⏱️  Running 8,000 iterations with 4 workers...")
    print("    Watch the workers explore different parts of the grid!")
    print()
    
    visualizer = WUUCTGridVisualizer(
        problem_path="../../OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt",
        iterations=8000,
        num_workers=4,
        exploration_constant=math.sqrt(2),
        max_edge_distance=1.42,
        update_interval=100,  # Fast updates to see workers moving
        grid_size=(16, 10)
    )
    
    return visualizer.run()


def main():
    """Main showcase function."""
    try:
        ani = showcase_parallel_paths()
    except KeyboardInterrupt:
        print("\n✅ Visualization completed!")
        print("   You saw parallel workers exploring the solution space!")
    except FileNotFoundError:
        print("❌ Error: Problem file not found.")
        print("   Make sure you're running from the Simple_WU/WU_Viz directory")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()