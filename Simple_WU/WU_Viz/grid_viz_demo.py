#!/usr/bin/env python3
"""
WU-UCT Grid Visualization Demo

A comprehensive demonstration of the new grid-based visualization
for the WU-UCT parallel orienteering problem solver.

This demo showcases:
1. Problem grid display with nodes and connections
2. Real-time best path highlighting 
3. Worker activity monitoring
4. Live algorithm statistics
5. Multi-panel informational layout

Author: GitHub Copilot
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


def demo_small_problem():
    """Demo with a small grid problem for quick visualization."""
    print("🎯 Small Grid Demo")
    print("=" * 30)
    print("Quick demonstration with a small 10x10 grid")
    print("⏱️  Duration: ~30 seconds")
    print()
    
    visualizer = WUUCTGridVisualizer(
        problem_path="../../OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt",
        iterations=5000,
        num_workers=3,
        exploration_constant=1.414,
        max_edge_distance=1.42,
        update_interval=150,  # Slightly slower for better observation
        grid_size=(14, 9)
    )
    
    return visualizer.run()


def demo_medium_problem():
    """Demo with a medium-sized problem for comprehensive visualization."""
    print("🎯 Medium Grid Demo")  
    print("=" * 30)
    print("Comprehensive demonstration with more iterations")
    print("⏱️  Duration: ~60 seconds")
    print()
    
    visualizer = WUUCTGridVisualizer(
        problem_path="../../OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt",
        iterations=15000,
        num_workers=4,
        exploration_constant=math.sqrt(2),
        max_edge_distance=1.42,
        update_interval=100,
        grid_size=(16, 10)
    )
    
    return visualizer.run()


def demo_high_performance():
    """Demo optimized for performance observation."""
    print("🚀 High Performance Demo")
    print("=" * 30) 
    print("Fast-paced visualization focusing on algorithm performance")
    print("⏱️  Duration: ~45 seconds")
    print()
    
    visualizer = WUUCTGridVisualizer(
        problem_path="../../OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt",
        iterations=25000,
        num_workers=6,
        exploration_constant=1.414,
        max_edge_distance=1.42,
        update_interval=75,  # Fast updates
        grid_size=(15, 10)
    )
    
    return visualizer.run()


def main():
    """Main demo selection menu."""
    print("🔬 WU-UCT Grid Visualization Demonstration")
    print("=" * 50)
    print()
    print("This demonstration shows the new grid-based visualization")
    print("for the WU-UCT parallel orienteering problem solver.")
    print()
    print("📋 Features demonstrated:")
    print("  • Problem grid with nodes, connections, and scoring")
    print("  • Real-time best path highlighting with golden arrows")  
    print("  • Multi-panel layout with comprehensive statistics")
    print("  • Live worker activity monitoring")
    print("  • Algorithm performance metrics")
    print("  • Interactive visual feedback")
    print()
    
    print("🎮 Choose a demonstration:")
    print("1. Small Grid Demo - Quick overview (~30s)")
    print("2. Medium Grid Demo - Comprehensive view (~60s)")
    print("3. High Performance Demo - Fast-paced analysis (~45s)")
    print()
    
    try:
        choice = input("Enter your choice (1-3): ").strip()
        print()
        
        if choice == '1':
            ani = demo_small_problem()
        elif choice == '2':
            ani = demo_medium_problem()
        elif choice == '3':
            ani = demo_high_performance()
        else:
            print("Invalid choice. Running medium demo by default.")
            ani = demo_medium_problem()
            
    except KeyboardInterrupt:
        print("\n🛑 Demonstration interrupted by user.")
    except FileNotFoundError as e:
        print(f"❌ Error: Problem file not found.")
        print("📁 Make sure you're running from the Simple_WU/WU_Viz directory")
        print("📁 Expected file: ../../OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt")
    except Exception as e:
        print(f"❌ Error running demonstration: {e}")
        print("🔧 Make sure you have matplotlib installed and all dependencies available.")


if __name__ == "__main__":
    main()