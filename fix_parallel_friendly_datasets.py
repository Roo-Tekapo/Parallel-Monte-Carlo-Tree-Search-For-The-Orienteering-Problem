"""
Fix parallel_friendly_v2 datasets to have proper START and END nodes.

Issue: Node 1 (END) should have reward 0 and be positioned far from START.
Currently, node 1 might have a reward and be close to START.

Fix: For each file, ensure node 1 (second node) is positioned far from node 0
and has reward 0.
"""

import os
import math
from typing import List, Tuple


def read_problem_file(filename: str) -> Tuple[int, List[Tuple[float, float, int]]]:
    """Read an OP problem file."""
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # First line: budget and node count
    budget, node_count = map(int, lines[0].strip().split())
    
    # Read all nodes
    nodes = []
    for i in range(1, len(lines)):
        if lines[i].strip():
            parts = lines[i].strip().split()
            x, y, reward = float(parts[0]), float(parts[1]), int(parts[2])
            nodes.append((x, y, reward))
    
    return budget, nodes


def find_farthest_node(start_pos: Tuple[float, float], nodes: List[Tuple[float, float, int]]) -> int:
    """Find the index of the node farthest from start position."""
    max_dist = 0
    farthest_idx = -1
    
    for i, (x, y, reward) in enumerate(nodes):
        if i == 0:  # Skip start node itself
            continue
        dist = math.sqrt((x - start_pos[0])**2 + (y - start_pos[1])**2)
        if dist > max_dist:
            max_dist = dist
            farthest_idx = i
    
    return farthest_idx


def fix_problem_file(filename: str, verbose: bool = True):
    """
    Fix a problem file to ensure proper START and END nodes.
    
    - Node 0: START at its current position with reward 0
    - Node 1: END at position farthest from START with reward 0
    - Other nodes: Keep as intermediate nodes
    """
    budget, nodes = read_problem_file(filename)
    
    if len(nodes) < 2:
        if verbose:
            print(f"⚠ Skipping {filename}: Too few nodes ({len(nodes)})")
        return False
    
    # Node 0 should be START with reward 0
    start_x, start_y, start_reward = nodes[0]
    if start_reward != 0:
        if verbose:
            print(f"⚠ Warning: {filename} - Node 0 has reward {start_reward}, setting to 0")
        nodes[0] = (start_x, start_y, 0)
    
    # Find the node farthest from START to be END
    farthest_idx = find_farthest_node((start_x, start_y), nodes)
    
    if farthest_idx == -1 or farthest_idx == 0:
        if verbose:
            print(f"⚠ Error: {filename} - Could not find valid END node")
        return False
    
    # Get the farthest node
    end_x, end_y, end_reward = nodes[farthest_idx]
    distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
    
    # Create new node list with proper ordering
    new_nodes = []
    new_nodes.append((start_x, start_y, 0))  # Node 0: START
    new_nodes.append((end_x, end_y, 0))       # Node 1: END (with reward 0)
    
    # Add all other nodes (excluding the one we moved to position 1)
    for i, node in enumerate(nodes):
        if i == 0:  # Skip START (already added)
            continue
        if i == farthest_idx:  # Skip END (already added)
            continue
        new_nodes.append(node)
    
    # Save the fixed file
    with open(filename, 'w') as f:
        f.write(f"{budget}\t{len(new_nodes)}\n")
        for x, y, reward in new_nodes:
            f.write(f"{x:.3f}\t{y:.3f}\t{int(reward)}\n")
    
    if verbose:
        old_node1_x, old_node1_y, old_node1_reward = nodes[1]
        old_dist = math.sqrt((old_node1_x - start_x)**2 + (old_node1_y - start_y)**2)
        print(f"✓ Fixed {os.path.basename(filename)}")
        print(f"  Old node 1: ({old_node1_x:.1f}, {old_node1_y:.1f}) reward={old_node1_reward}, dist={old_dist:.2f}")
        print(f"  New node 1: ({end_x:.1f}, {end_y:.1f}) reward=0, dist={distance:.2f}")
    
    return True


def fix_all_datasets(base_dir: str = "OP_Benchmark_Set/parallel_friendly_v2"):
    """Fix all datasets in the parallel_friendly_v2 directory."""
    
    print("="*70)
    print("FIXING PARALLEL_FRIENDLY_V2 DATASETS")
    print("="*70)
    print("Ensuring node 0 = START and node 1 = END (reward 0, far from START)")
    print()
    
    # Find all .txt files in subdirectories
    fixed_count = 0
    error_count = 0
    
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.txt'):
                filepath = os.path.join(root, file)
                try:
                    if fix_problem_file(filepath, verbose=True):
                        fixed_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    print(f"✗ Error processing {filepath}: {e}")
                    error_count += 1
                print()
    
    print("="*70)
    print("FIX COMPLETE!")
    print("="*70)
    print(f"Files fixed: {fixed_count}")
    print(f"Errors: {error_count}")
    print()


def verify_dataset(filename: str):
    """Verify a dataset has correct START/END structure."""
    budget, nodes = read_problem_file(filename)
    
    if len(nodes) < 2:
        return False, "Too few nodes"
    
    start_x, start_y, start_reward = nodes[0]
    end_x, end_y, end_reward = nodes[1]
    
    issues = []
    
    if start_reward != 0:
        issues.append(f"Node 0 (START) has reward {start_reward}, should be 0")
    
    if end_reward != 0:
        issues.append(f"Node 1 (END) has reward {end_reward}, should be 0")
    
    distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
    if distance < 5.0:  # Arbitrary threshold
        issues.append(f"END node too close to START (distance={distance:.2f})")
    
    if issues:
        return False, "; ".join(issues)
    
    return True, f"OK (START-END distance={distance:.2f})"


def verify_all_datasets(base_dir: str = "OP_Benchmark_Set/parallel_friendly_v2"):
    """Verify all datasets have correct structure."""
    
    print("="*70)
    print("VERIFYING DATASETS")
    print("="*70)
    
    ok_count = 0
    error_count = 0
    
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.txt'):
                filepath = os.path.join(root, file)
                try:
                    is_ok, message = verify_dataset(filepath)
                    if is_ok:
                        ok_count += 1
                        print(f"✓ {os.path.basename(filepath)}: {message}")
                    else:
                        error_count += 1
                        print(f"✗ {os.path.basename(filepath)}: {message}")
                except Exception as e:
                    error_count += 1
                    print(f"✗ {os.path.basename(filepath)}: Error - {e}")
    
    print()
    print("="*70)
    print(f"Valid files: {ok_count}")
    print(f"Invalid files: {error_count}")
    print("="*70)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_all_datasets()
    else:
        fix_all_datasets()
        print("\nRunning verification...")
        verify_all_datasets()
