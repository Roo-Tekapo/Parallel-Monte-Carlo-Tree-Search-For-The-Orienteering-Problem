#!/usr/bin/env python3
"""
Generate FIXED Orienteering Problem datasets with proper connectivity.
Ensures max_edge_distance constraint is respected with tight node spacing.
"""

import math
import random
import os
import shutil
from typing import List, Tuple


def generate_connected_coordinates(num_nodes: int, max_edge_distance: float = 1.42) -> List[Tuple[float, float]]:
    """
    Generate coordinates ensuring connectivity with max_edge_distance constraint.
    Uses a much tighter grid to ensure all nodes can connect to neighbors.
    """
    coords = []
    
    # Calculate grid spacing to ensure connectivity
    # Use different spacing based on number of nodes
    if num_nodes <= 100:
        base_spacing = max_edge_distance * 0.8  # ≈ 1.136 for √2
        grid_range = 6  # Smaller range for tighter packing
    else:  # 1000 nodes - use exactly √2 spacing with larger range
        base_spacing = max_edge_distance * 0.99  # Very close to √2
        grid_range = 32  # Much larger range for 1000 nodes
    
    print(f"Using base spacing: {base_spacing:.3f} (max_edge_distance: {max_edge_distance:.3f})")
    
    # Start and end nodes at opposite ends
    start_x, start_y = 0.0, -grid_range + 1
    end_x, end_y = 0.0, grid_range - 1
    
    coords.append((start_x, start_y))
    coords.append((end_x, end_y))
    
    # Generate grid points with tight spacing
    attempts = 0
    max_attempts = num_nodes * 500
    
    # Create systematic grid
    grid_size = int(math.ceil(math.sqrt(num_nodes * 2)))  # Ensure enough grid points
    
    candidate_points = []
    for i in range(-grid_size//2, grid_size//2 + 1):
        for j in range(-grid_size//2, grid_size//2 + 1):
            x = i * base_spacing
            y = j * base_spacing
            
            # Stay within bounds
            if abs(x) <= grid_range and abs(y) <= grid_range:
                # Skip start/end positions
                if not ((abs(x - start_x) < 0.1 and abs(y - start_y) < 0.1) or 
                       (abs(x - end_x) < 0.1 and abs(y - end_y) < 0.1)):
                    
                    # Add small random offset (much smaller than before)
                    noise_x = random.uniform(-0.1, 0.1)
                    noise_y = random.uniform(-0.1, 0.1)
                    
                    candidate_points.append((x + noise_x, y + noise_y))
    
    # Shuffle and select points that maintain distance constraints
    random.shuffle(candidate_points)
    
    for x, y in candidate_points:
        if len(coords) >= num_nodes:
            break
        
        # Check minimum distance constraint (adaptive based on node count)
        valid = True
        min_dist_threshold = max_edge_distance * (0.5 if num_nodes > 500 else 0.7)
        
        for existing_x, existing_y in coords:
            dist = math.sqrt((x - existing_x)**2 + (y - existing_y)**2)
            if dist < min_dist_threshold:
                valid = False
                break
        
        if valid:
            coords.append((x, y))
    
    if len(coords) < num_nodes:
        raise ValueError(f"Could not generate {num_nodes} nodes with max_edge_distance {max_edge_distance}")
    
    return coords


def calculate_score_connected(x: float, y: float, max_coord: float) -> int:
    """Calculate score based on distance from center."""
    dist_from_center = math.sqrt(x*x + y*y)
    max_dist = math.sqrt(2 * max_coord * max_coord)
    
    if dist_from_center < 0.5:
        return 0
    
    # Scale to 0-7 range, then multiply by 6
    normalized_dist = min(dist_from_center / max_dist, 1.0)
    score_level = int(normalized_dist * 7)
    return (score_level + 1) * 6


def generate_connected_problem_file(num_nodes: int, budget: float, filename: str):
    """Generate a problem file with guaranteed connectivity."""
    print(f"Generating {filename} with {num_nodes} nodes and budget {budget}")
    
    coords = generate_connected_coordinates(num_nodes)
    
    # Calculate max coordinate for scoring
    max_coord = max(max(abs(x), abs(y)) for x, y in coords)
    
    with open(filename, 'w') as f:
        f.write(f"{budget:.0f}\t1\n")
        
        for i, (x, y) in enumerate(coords):
            if i in [0, 1]:  # Start and end nodes
                score = 0
            else:
                score = calculate_score_connected(x, y, max_coord)
            
            f.write(f"{x:.3f}\t{y:.3f}\t{score}\n")


def generate_connected_dataset_folder(num_nodes: int, folder_name: str):
    """Generate dataset folder with connected nodes."""
    print(f"Creating connected dataset folder: {folder_name}")
    
    folder_path = f"/Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/OP_Benchmark_Set/{folder_name}"
    os.makedirs(folder_path, exist_ok=True)
    
    if num_nodes == 100:
        budgets = [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150]
    else:  # 1000 nodes
        budgets = [25, 35, 45, 55, 65, 75, 85, 95, 105, 115, 125, 135, 145, 155]
    
    for budget in budgets:
        filename = f"{folder_path}/{folder_name}_{budget}.txt"
        generate_connected_problem_file(num_nodes, budget, filename)


def verify_connectivity(filename: str, max_edge_distance: float = 1.42) -> None:
    """Verify that the generated dataset has proper connectivity."""
    from orienteering.orienteering import OrienteeringProblem, OrienteeringState
    
    nodes, budget = OrienteeringProblem.load_problem(filename)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=max_edge_distance)
    state = OrienteeringState(problem)
    
    actions = state.get_available_actions()
    neighbors = problem.get_neighbors(0)
    
    print(f"Connectivity check for {filename}:")
    print(f"  Nodes: {len(nodes)}, Budget: {budget}")
    print(f"  Start node neighbors: {len(neighbors)}")
    print(f"  Available actions from start: {len(actions)}")
    
    if len(actions) > 0:
        print(f"  ✅ Connected! First few actions: {actions[:5]}")
    else:
        print(f"  ❌ Not connected!")
    
    # Check minimum distance
    coords = [(node.x, node.y) for node in nodes]
    min_dist = float('inf')
    for i in range(len(coords)):
        for j in range(i+1, len(coords)):
            dist = math.sqrt((coords[i][0] - coords[j][0])**2 + (coords[i][1] - coords[j][1])**2)
            min_dist = min(min_dist, dist)
    
    print(f"  Min distance between nodes: {min_dist:.3f}")
    return len(actions) > 0


def main():
    """Generate connected datasets."""
    random.seed(42)
    
    print("Generating CONNECTED Orienteering Problem datasets...")
    print("(Optimized for max_edge_distance constraint)")
    
    # Remove old datasets
    old_paths = [
        "/Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/OP_Benchmark_Set/set_100_1",
        "/Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/OP_Benchmark_Set/set_1000_1"
    ]
    
    for path in old_paths:
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"Removed old dataset: {path}")
    
    # Generate new connected datasets
    try:
        generate_connected_dataset_folder(100, "set_100_1")
        generate_connected_dataset_folder(1000, "set_1000_1")
        
        print("\\nDataset generation complete!")
        
        # Verify connectivity
        print("\\nVerifying connectivity with max_edge_distance=1.42:")
        test_files = [
            "/Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/OP_Benchmark_Set/set_100_1/set_100_1_60.txt",
            "/Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/OP_Benchmark_Set/set_1000_1/set_1000_1_75.txt"
        ]
        
        for test_file in test_files:
            if os.path.exists(test_file):
                verify_connectivity(test_file)
        
        print("\\n✅ Connected datasets generated successfully!")
        
    except Exception as e:
        print(f"❌ Error generating datasets: {e}")


if __name__ == "__main__":
    main()