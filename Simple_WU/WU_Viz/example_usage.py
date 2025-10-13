#!/usr/bin/env python3
"""
WU-UCT Visualization Example

This script demonstrates how to use the WU-UCT visualization tools
to observe the parallel algorithm in action.
"""

import sys
import os

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
simple_wu_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(simple_wu_dir)
sys.path.extend([project_root, simple_wu_dir])

from wu_uct_tree_viz import WUUCTTreeVisualizer
from wu_uct_parallel_viz import EnhancedWUUCTVisualizer
from wu_uct_grid_viz import WUUCTGridVisualizer


def find_problem_file(filename):
    """Find the problem file by trying multiple possible paths."""
    possible_paths = [
        f"../../OP_Benchmark_Set/grid_sample/{filename}",  # From WU_Viz directory
        f"OP_Benchmark_Set/grid_sample/{filename}",        # From project root
        f"../OP_Benchmark_Set/grid_sample/{filename}",     # From Simple_WU directory
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # If not found, raise helpful error
    raise FileNotFoundError(
        f"Could not find {filename}. Tried:\n" + 
        "\n".join(f"  - {p}" for p in possible_paths) +
        "\n\nPlease run from the project root, Simple_WU, or Simple_WU/WU_Viz directory."
    )


def run_basic_visualization():
    """Run the basic WU-UCT tree visualization."""
    print("Starting Basic WU-UCT Tree Visualization...")
    print("This shows the shared tree development with WU-UCT specific features.")
    print()
    
    problem_path = find_problem_file("grid_10x10_medium_30.txt")
    print(f"Using problem file: {problem_path}\n")
    
    visualizer = WUUCTTreeVisualizer(
        problem_path=problem_path,
        iterations=5000,
        num_workers=4,
        initial_max_depth=6,
        max_nodes=150
    )
    
    return visualizer.run()


def run_parallel_visualization():
    """Run the enhanced parallel WU-UCT visualization."""
    print("Starting Enhanced Parallel WU-UCT Visualization...")
    print("This shows detailed worker activity and parallel interaction.")
    print()
    
    problem_path = find_problem_file("grid_10x10_medium_30.txt")
    print(f"Using problem file: {problem_path}\n")
    
    visualizer = EnhancedWUUCTVisualizer(
        problem_path=problem_path,
        iterations= 10000,
        num_workers=4,
        initial_max_depth=6,
        max_nodes=120
    )
    
    return visualizer.run()


def run_grid_visualization():
    """Run the comprehensive grid WU-UCT visualization."""
    print("Starting Grid-based WU-UCT Visualization...")
    print("This shows the problem grid with real-time WU-UCT algorithm activity.")
    print("  • Each worker's exploration path shown in unique color")
    print("  • Press 'P' to toggle worker path display")
    print()
    
    problem_path = find_problem_file("grid_10x10_medium_30.txt")
    print(f"Using problem file: {problem_path}\n")
    
    visualizer = WUUCTGridVisualizer(
        problem_path=problem_path,
        iterations=12000,
        num_workers=4,
        exploration_constant=1.414,
        max_edge_distance=1.42,
        update_interval=100
    )
    
    return visualizer.run()


def main():
    """Main example function with menu selection."""
    print("WU-UCT Visualization Examples")
    print("=============================")
    print()
    print("Choose visualization type:")
    print("1. Basic Tree Visualization - Shows WU-UCT tree development")
    print("2. Parallel Worker Visualization - Shows detailed worker activity")
    print("3. Grid Visualization - Shows problem grid with real-time WU-UCT activity")
    print("4. All visualizations (sequential)")
    print()
    
    try:
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == '1':
            ani = run_basic_visualization()
        elif choice == '2':
            ani = run_parallel_visualization()
        elif choice == '3':
            ani = run_grid_visualization()
        elif choice == '4':
            print("Running basic visualization first...")
            ani1 = run_basic_visualization()
            input("Press Enter to continue to parallel visualization...")
            ani2 = run_parallel_visualization()
            input("Press Enter to continue to grid visualization...")
            ani3 = run_grid_visualization()
        else:
            print("Invalid choice. Running grid visualization by default.")
            ani = run_grid_visualization()
            
    except KeyboardInterrupt:
        print("\nVisualization interrupted by user.")
    except Exception as e:
        print(f"Error running visualization: {e}")
        print("Make sure you have matplotlib installed and the problem files exist.")


if __name__ == "__main__":
    main()