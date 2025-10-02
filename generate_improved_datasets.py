#!/usr/bin/env python3
"""
Generate improved Orienteering Problem datasets with 100 and 1000 nodes.
Uses semi-regular grid with controlled randomness to emulate set_64_1 but less strictly.
"""

import math
import random
import os
from typing import List, Tuple


def generate_semi_regular_coordinates(num_nodes: int, min_distance: float = math.sqrt(2)) -> List[Tuple[float, float]]:
    """
    Generate coordinates with semi-regular spacing like set_64_1 but with controlled variation.
    
    Args:
        num_nodes: Total number of nodes to generate
        min_distance: Minimum distance between any two nodes
        
    Returns:
        List of (x, y) coordinate tuples
    """
    coords = []
    
    # Determine grid spacing and size based on number of nodes
    if num_nodes <= 100:
        base_spacing = 1.8  # Larger spacing to ensure we can fit nodes
        grid_range = 12  # Grid from -12 to +12
    else:  # 1000 nodes
        base_spacing = 2.0
        grid_range = 32  # Grid from -32 to +32
    
    # Start and end nodes (similar to set_64_1 pattern)
    start_x, start_y = 0.0, -grid_range + 1
    end_x, end_y = 0.0, grid_range - 1
    
    coords.append((start_x, start_y))
    coords.append((end_x, end_y))
    
    # Generate a semi-regular grid with controlled randomness
    used_positions = set()
    attempts = 0
    max_attempts = num_nodes * 200
    
    # Create a more systematic approach
    # Start with a regular grid, then add controlled noise
    grid_points = []
    
    # Generate regular grid points
    steps = int(math.ceil(math.sqrt(num_nodes * 1.5)))  # Ensure enough candidate points
    for i in range(-steps//2, steps//2 + 1):
        for j in range(-steps//2, steps//2 + 1):
            if abs(i * base_spacing) <= grid_range and abs(j * base_spacing) <= grid_range:
                # Add controlled randomness to make it less strict
                noise_x = random.uniform(-0.4, 0.4)  # Small random offset
                noise_y = random.uniform(-0.4, 0.4)
                
                x = i * base_spacing + noise_x
                y = j * base_spacing + noise_y
                
                # Skip if too close to start/end nodes
                if (abs(x - start_x) < 0.5 and abs(y - start_y) < 0.5) or \
                   (abs(x - end_x) < 0.5 and abs(y - end_y) < 0.5):
                    continue
                
                grid_points.append((x, y))
    
    # Shuffle and select points that maintain minimum distance
    random.shuffle(grid_points)
    
    for x, y in grid_points:
        if len(coords) >= num_nodes:
            break
            
        # Check minimum distance constraint (more lenient)
        valid = True
        for existing_x, existing_y in coords:
            dist = math.sqrt((x - existing_x)**2 + (y - existing_y)**2)
            if dist < min_distance * 0.9:  # 10% more lenient than strict √2
                valid = False
                break
        
        if valid:
            coords.append((x, y))
            attempts = 0
        else:
            attempts += 1
            
        if attempts > 1000:  # Prevent infinite loops
            break
    
    # If we still need more nodes, try a different approach
    while len(coords) < num_nodes and attempts < max_attempts:
        # Generate random points in valid range
        x = random.uniform(-grid_range, grid_range)
        y = random.uniform(-grid_range, grid_range)
        
        # Check minimum distance constraint (more lenient)
        valid = True
        for existing_x, existing_y in coords:
            dist = math.sqrt((x - existing_x)**2 + (y - existing_y)**2)
            if dist < min_distance * 0.9:  # 10% more lenient than strict √2
                valid = False
                break
        
        if valid:
            coords.append((x, y))
        
        attempts += 1
    
    if len(coords) < num_nodes:
        raise ValueError(f"Could not generate {num_nodes} nodes with minimum distance {min_distance}")
    
    return coords


def calculate_score_improved(x: float, y: float, max_coord: float) -> int:
    """
    Calculate score based on distance from center, similar to set_64_1 pattern.
    """
    # Distance from center (0, 0)
    dist_from_center = math.sqrt(x*x + y*y)
    max_dist = math.sqrt(2 * max_coord * max_coord)
    
    # Normalize distance and scale to score range
    # set_64_1 had scores: [0, 6, 12, 18, 24, 30, 36, 42]
    if dist_from_center < 0.5:
        return 0  # Start/end nodes or very close to center
    
    # Scale to 0-7 range, then multiply by 6
    normalized_dist = min(dist_from_center / max_dist, 1.0)
    score_level = int(normalized_dist * 7)
    return (score_level + 1) * 6


def generate_problem_file_improved(num_nodes: int, budget: float, filename: str):
    """Generate a single problem file with improved spacing."""
    print(f"Generating {filename} with {num_nodes} nodes and budget {budget}")
    
    coords = generate_semi_regular_coordinates(num_nodes)
    
    # Calculate max coordinate for scoring
    max_coord = max(max(abs(x), abs(y)) for x, y in coords)
    
    with open(filename, 'w') as f:
        # Write header: budget and number of nodes
        f.write(f"{budget:.0f}\t1\n")
        
        # Write coordinates and scores
        for i, (x, y) in enumerate(coords):
            if i in [0, 1]:  # Start and end nodes have score 0
                score = 0
            else:
                score = calculate_score_improved(x, y, max_coord)
            
            f.write(f"{x:.3f}\t{y:.3f}\t{score}\n")


def generate_dataset_folder_improved(num_nodes: int, folder_name: str):
    """Generate a complete dataset folder with improved spacing."""
    print(f"Creating improved dataset folder: {folder_name}")
    
    # Create folder
    folder_path = f"/Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/OP_Benchmark_Set/{folder_name}"
    os.makedirs(folder_path, exist_ok=True)
    
    # Generate budget values based on problem size
    if num_nodes == 100:
        # For 100 nodes, use budget range similar to set_64_1 but scaled up appropriately
        budgets = [25, 35, 45, 55, 65, 75, 85, 95, 105, 115, 125, 135, 145, 155]
    else:  # 1000 nodes
        # For 1000 nodes, use much larger budget range
        budgets = [60, 90, 120, 150, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800]
    
    for budget in budgets:
        filename = f"{folder_path}/{folder_name}_{budget}.txt"
        generate_problem_file_improved(num_nodes, budget, filename)


def analyze_spacing(filename: str) -> None:
    """Analyze the spacing of generated coordinates."""
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    coords = []
    for i in range(1, len(lines)):
        line = lines[i].strip()
        if line:
            x, y, _ = line.split()
            coords.append((float(x), float(y)))
    
    # Calculate all pairwise distances
    distances = []
    for i in range(len(coords)):
        for j in range(i+1, len(coords)):
            dist = math.sqrt((coords[i][0] - coords[j][0])**2 + (coords[i][1] - coords[j][1])**2)
            distances.append(dist)
    
    distances.sort()
    min_dist = distances[0]
    
    # Count distances in ranges
    sqrt2 = math.sqrt(2)
    close_to_sqrt2 = sum(1 for d in distances if abs(d - sqrt2) < 0.2)
    
    print(f"{filename}:")
    print(f"  Nodes: {len(coords)}")
    print(f"  Min distance: {min_dist:.3f}")
    print(f"  Distances close to √2 ({sqrt2:.3f}): {close_to_sqrt2}/{len(distances)}")
    print(f"  Average nearest neighbor distance: {sum(distances[:len(coords)-1])/len(coords):.3f}")


def main():
    """Generate both improved 100-node and 1000-node datasets."""
    random.seed(42)  # For reproducible results
    
    print("Generating improved Orienteering Problem datasets...")
    print("(Semi-regular spacing with controlled variation)")
    
    # Remove old datasets first
    import shutil
    old_paths = [
        "/Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/OP_Benchmark_Set/set_100_1",
        "/Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/OP_Benchmark_Set/set_1000_1"
    ]
    
    for path in old_paths:
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"Removed old dataset: {path}")
    
    # Generate improved datasets
    generate_dataset_folder_improved(100, "set_100_1")
    generate_dataset_folder_improved(1000, "set_1000_1")
    
    print("Dataset generation complete!")
    
    # Analyze spacing in generated files
    print("\nSpacing analysis:")
    test_files = [
        "/Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/OP_Benchmark_Set/set_100_1/set_100_1_75.txt",
        "/Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/OP_Benchmark_Set/set_1000_1/set_1000_1_300.txt"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            analyze_spacing(test_file)
    
    # Compare with original set_64_1
    print("\nComparison with original set_64_1:")
    analyze_spacing("/Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/OP_Benchmark_Set/set_64_1/set_64_1_80.txt")


if __name__ == "__main__":
    main()