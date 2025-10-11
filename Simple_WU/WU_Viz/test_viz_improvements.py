#!/usr/bin/env python3
"""
Quick test script for the improved WU-UCT grid visualization.
This script creates a minimal test case to verify the visualization works.
"""

import sys
import os
import math

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
simple_wu_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(simple_wu_dir)
sys.path.extend([project_root, simple_wu_dir])

from wu_uct_grid_viz import WUUCTGridVisualizer

def test_visualization():
    """Test the visualization with a small problem."""
    print("="*60)
    print("WU-UCT Visualization Test")
    print("="*60)
    print()
    
    # Use a small problem for quick testing
    problem_path = "../../OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    
    if not os.path.exists(problem_path):
        print(f"❌ Problem file not found: {problem_path}")
        print("Please run from Simple_WU/WU_Viz directory")
        return False
    
    print(f"✓ Problem file found: {problem_path}")
    print()
    
    # Create visualizer with step-by-step mode
    print("Creating visualizer...")
    visualizer = WUUCTGridVisualizer(
        problem_path=problem_path,
        iterations=500,  # Small number for quick test
        num_workers=2,   # Just 2 workers for simplicity
        exploration_constant=math.sqrt(2),
        max_edge_distance=1.42,
        update_interval=100,  # 100ms updates
        grid_size=(12, 8),
        step_by_step=True,  # Enable step-by-step
        iterations_per_frame=2  # 2 iterations per frame
    )
    
    print("✓ Visualizer created successfully")
    print()
    print("Configuration:")
    print(f"  - Mode: Step-by-step")
    print(f"  - Workers: {visualizer.num_workers}")
    print(f"  - Iterations: {visualizer.iterations}")
    print(f"  - Iterations/frame: {visualizer.iterations_per_frame}")
    print(f"  - Update interval: {visualizer.update_interval}ms")
    print()
    
    print("Starting visualization...")
    print("(Close the window to end the test)")
    print()
    
    try:
        visualizer.run()
        print()
        print("✅ Visualization test completed successfully!")
        return True
    except Exception as e:
        print()
        print(f"❌ Visualization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_visualization()
    sys.exit(0 if success else 1)
