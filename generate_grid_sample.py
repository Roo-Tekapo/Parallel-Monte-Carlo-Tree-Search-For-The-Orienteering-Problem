#!/usr/bin/env python3
"""
Generate orienteering test problems on a 10x10 grid.
Start at (5,0), end at (10,5), with random rewards for other nodes.
"""

import random
import math
import os


def generate_10x10_grid_problem(budget, output_file, seed=None):
    """
    Generate a 10x10 grid orienteering problem.
    
    Grid coordinates: (0,0) to (10,10) - 121 nodes total
    Start: (5,0) - node id 0
    End: (10,5) - node id 1  
    Other nodes: random rewards 1-20
    """
    if seed is not None:
        random.seed(seed)
    
    nodes = []
    node_id = 0
    
    # Create all grid points (0,0) to (10,10)
    grid_points = []
    for x in range(11):  # 0 to 10 inclusive
        for y in range(11):  # 0 to 10 inclusive
            grid_points.append((x, y))
    
    # Start node: (5,0) with score 0
    start_pos = (5, 0)
    nodes.append((start_pos[0], start_pos[1], 0))
    grid_points.remove(start_pos)
    node_id += 1
    
    # End node: (5,10) with score 0
    end_pos = (5, 10)
    nodes.append((end_pos[0], end_pos[1], 0))
    grid_points.remove(end_pos)
    node_id += 1
    
    # All other nodes get random rewards between 1-20
    for x, y in grid_points:
        reward = random.randint(1, 20)
        nodes.append((x, y, reward))
        node_id += 1
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write(f"{budget}\t1\n")
        for x, y, score in nodes:
            f.write(f"{x:.3f}\t{y:.3f}\t{score}\n")
    
    print(f"Generated {output_file} with {len(nodes)} nodes, budget {budget}")
    return nodes


def main():
    # Create output directory if it doesn't exist
    output_dir = "OP_Benchmark_Set/grid_sample"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate multiple test cases with different budgets
    test_cases = [
        # (budget, seed, description)
        (20, 42, "easy_20"),      # Short budget - forces selective path
        (30, 123, "medium_30"),   # Medium budget - some exploration possible
        (40, 456, "hard_40"),     # Longer budget - more strategic choices
        (50, 789, "long_50"),     # Long budget - near-optimal solutions possible
    ]
    
    print("Generating 10x10 grid orienteering problems...")
    print(f"Start: (5,0) - Node ID 0")
    print(f"End: (5,10) - Node ID 1") 
    print(f"Grid: 11x11 points (0,0) to (10,10) = 121 total nodes")
    print(f"Rewards: Random 1-20 for non-start/end nodes")
    print("=" * 60)
    
    for budget, seed, desc in test_cases:
        output_file = f"{output_dir}/grid_10x10_{desc}.txt"
        nodes = generate_10x10_grid_problem(budget, output_file, seed)
        
        # Calculate some basic stats
        total_reward = sum(score for _, _, score in nodes)
        max_reward = max(score for _, _, score in nodes)
        
        print(f"  • {desc}: Budget {budget}, Total rewards {total_reward}, Max reward {max_reward}")
    
    print("\n" + "=" * 60)
    print("✅ Grid sample problems generated successfully!")
    print("\nTo test these problems, you can run:")
    print("python3 UCT/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_easy_20.txt --algorithm wu-uct --max-iterations 10000")


if __name__ == "__main__":
    main()