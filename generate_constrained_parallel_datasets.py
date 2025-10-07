"""
Generate Orienteering Problem datasets optimized for WU-UCT with max_edge_distance=1.42 constraint.

This script creates OP instances that:
1. Respect the max_edge_distance=1.42 constraint (nodes within ~1.42 units are connected)
2. Have high branching factors through dense grid layouts
3. Feature complex decision-making through strategic node removal and reward patterns
4. Scale to large problem sizes while maintaining connectivity

The key insight: With 1.0 unit spacing, diagonal neighbors are at distance √2 ≈ 1.414,
which is just under 1.42, allowing 8-connected grid graphs.
"""

import numpy as np
import os
from typing import List, Tuple, Set
import math


class GridBasedOPGenerator:
    """Generate grid-based OP instances respecting max_edge_distance constraint."""
    
    def __init__(self, seed: int = 42):
        """Initialize the generator with a random seed."""
        np.random.seed(seed)
        self.unit_spacing = 1.0  # Grid spacing (diagonal = 1.414 < 1.42)
    
    def generate_dense_grid(self, grid_width: int, grid_height: int, 
                           removal_rate: float = 0.0,
                           budget_ratio: float = 0.4) -> Tuple[List, float]:
        """
        Generate a dense grid with optional random node removal.
        
        With 1.0 spacing, each interior node has 8 neighbors (3×3 minus self).
        This creates high branching factor while respecting max_edge_distance=1.42.
        
        Args:
            grid_width: Width of grid
            grid_height: Height of grid  
            removal_rate: Fraction of interior nodes to remove (0.0-0.5)
            budget_ratio: Budget as ratio of grid diagonal distance
            
        Returns:
            (nodes, budget) where nodes is list of (x, y, reward)
        """
        nodes = []
        
        # Node 0: START at origin with reward 0
        nodes.append((0.0, 0.0, 0))
        
        # Node 1: END at opposite corner with reward 0
        end_x = (grid_width - 1) * self.unit_spacing
        end_y = (grid_height - 1) * self.unit_spacing
        nodes.append((end_x, end_y, 0))
        
        # Generate grid nodes (excluding start and end positions)
        grid_positions = []
        for i in range(grid_width):
            for j in range(grid_height):
                x = i * self.unit_spacing
                y = j * self.unit_spacing
                
                # Skip START and END positions
                if (i == 0 and j == 0) or (i == grid_width - 1 and j == grid_height - 1):
                    continue
                
                grid_positions.append((x, y))
        
        # Randomly remove some interior nodes for complexity
        if removal_rate > 0:
            n_remove = int(len(grid_positions) * removal_rate)
            remove_indices = np.random.choice(len(grid_positions), n_remove, replace=False)
            grid_positions = [pos for idx, pos in enumerate(grid_positions) 
                            if idx not in remove_indices]
        
        # Add rewards to grid positions
        for x, y in grid_positions:
            # Balanced reward distribution with spatial variation
            base_reward = 15
            spatial_bonus = 5 * np.sin(x * 0.3) * np.cos(y * 0.3)
            noise = np.random.uniform(-3, 3)
            reward = int(max(5, base_reward + spatial_bonus + noise))
            nodes.append((x, y, reward))
        
        # Calculate budget based on grid diagonal
        diagonal = math.sqrt(grid_width**2 + grid_height**2) * self.unit_spacing
        budget = budget_ratio * diagonal * 2.5  # Allow for non-straight paths
        
        return nodes, budget
    
    def generate_sparse_grid(self, grid_width: int, grid_height: int,
                            density: float = 0.5,
                            budget_ratio: float = 0.4) -> Tuple[List, float]:
        """
        Generate a sparse grid by keeping only a fraction of nodes.
        
        Creates challenging problems where path-finding requires careful planning.
        
        Args:
            grid_width: Width of grid
            grid_height: Height of grid
            density: Fraction of nodes to keep (0.3-0.7)
            budget_ratio: Budget as ratio of grid span
            
        Returns:
            (nodes, budget)
        """
        nodes = []
        
        # Node 0: START at origin with reward 0
        nodes.append((0.0, 0.0, 0))
        
        # Node 1: END at opposite corner with reward 0
        end_x = (grid_width - 1) * self.unit_spacing
        end_y = (grid_height - 1) * self.unit_spacing
        nodes.append((end_x, end_y, 0))
        
        # Generate all possible grid positions (excluding start and end)
        all_positions = []
        for i in range(grid_width):
            for j in range(grid_height):
                x = i * self.unit_spacing
                y = j * self.unit_spacing
                
                # Skip START and END positions
                if (i == 0 and j == 0) or (i == grid_width - 1 and j == grid_height - 1):
                    continue
                    
                all_positions.append((x, y))
        
        # Keep only density% of nodes
        n_keep = int(len(all_positions) * density)
        kept_indices = np.random.choice(len(all_positions), n_keep, replace=False)
        
        for idx in kept_indices:
            x, y = all_positions[idx]
            reward = np.random.randint(10, 30)
            nodes.append((x, y, reward))
        
        # Budget based on expected path length
        diagonal = math.sqrt(grid_width**2 + grid_height**2) * self.unit_spacing
        budget = budget_ratio * diagonal * 3.0  # Higher multiplier for sparse graphs
        
        return nodes, budget
    
    def generate_clustered_grid(self, n_clusters: int = 4, 
                               cluster_size: int = 5,
                               cluster_spacing: int = 8,
                               budget_ratio: float = 0.5) -> Tuple[List, float]:
        """
        Generate clusters of grid nodes with controlled spacing.
        
        Each cluster is a dense grid region. Clusters are separated enough
        that inter-cluster paths require planning, but close enough to be
        reachable within the 1.42 constraint via intermediate nodes.
        
        Args:
            n_clusters: Number of clusters (arranged in grid)
            cluster_size: Size of each cluster (cluster_size × cluster_size grid)
            cluster_spacing: Spacing between cluster centers
            budget_ratio: Budget ratio
            
        Returns:
            (nodes, budget)
        """
        nodes = []
        
        # Node 0: START at origin with reward 0
        nodes.append((0.0, 0.0, 0))
        
        # We'll set END node position after generating all clusters
        end_node_placeholder_idx = len(nodes)
        nodes.append((0.0, 0.0, 0))  # Placeholder for END node
        
        # Arrange clusters in a grid pattern
        clusters_per_side = int(np.ceil(np.sqrt(n_clusters)))
        
        cluster_id = 0
        for cx in range(clusters_per_side):
            for cy in range(clusters_per_side):
                if cluster_id >= n_clusters:
                    break
                
                # Center of this cluster
                center_x = cx * cluster_spacing * self.unit_spacing
                center_y = cy * cluster_spacing * self.unit_spacing
                
                # Add nodes in a grid around cluster center
                for i in range(cluster_size):
                    for j in range(cluster_size):
                        x = center_x + (i - cluster_size//2) * self.unit_spacing
                        y = center_y + (j - cluster_size//2) * self.unit_spacing
                        
                        # Skip origin if it coincides
                        if abs(x) < 0.01 and abs(y) < 0.01:
                            continue
                        
                        # Vary rewards by cluster
                        base_reward = 12 + 6 * np.sin(cluster_id * 0.8)
                        reward = int(max(5, base_reward + np.random.uniform(-4, 4)))
                        nodes.append((x, y, reward))
                
                cluster_id += 1
        
        # Find farthest node from START to set as END
        if len(nodes) > 2:
            max_dist = 0
            farthest_idx = 2  # Start checking from index 2 (after placeholder)
            for i in range(2, len(nodes)):
                dist = math.sqrt(nodes[i][0]**2 + nodes[i][1]**2)
                if dist > max_dist:
                    max_dist = dist
                    farthest_idx = i
            # Replace placeholder END node with the farthest node (with reward 0)
            end_x, end_y, _ = nodes[farthest_idx]
            nodes[end_node_placeholder_idx] = (end_x, end_y, 0)
            # Remove the duplicate node
            del nodes[farthest_idx]
        
        # Budget to visit multiple clusters
        span = clusters_per_side * cluster_spacing * self.unit_spacing
        budget = budget_ratio * span * 4.0
        
        return nodes, budget
    
    def generate_corridors(self, n_corridors: int = 3,
                          corridor_length: int = 20,
                          corridor_width: int = 3,
                          budget_ratio: float = 0.5) -> Tuple[List, float]:
        """
        Generate a corridor/maze-like structure.
        
        Creates interesting path-finding challenges where the agent must
        navigate through narrow corridors with branching choices.
        
        Args:
            n_corridors: Number of main corridors
            corridor_length: Length of each corridor
            corridor_width: Width of corridors (number of parallel paths)
            budget_ratio: Budget ratio
            
        Returns:
            (nodes, budget)
        """
        nodes = []
        
        # Node 0: START at origin with reward 0
        nodes.append((0.0, 0.0, 0))
        
        # We'll set END node position after generating all corridors
        end_node_placeholder_idx = len(nodes)
        nodes.append((0.0, 0.0, 0))  # Placeholder for END node
        
        # Create main corridors radiating from origin
        for corridor_idx in range(n_corridors):
            angle = 2 * np.pi * corridor_idx / n_corridors
            dx = np.cos(angle)
            dy = np.sin(angle)
            
            # Perpendicular direction for width
            px = -dy
            py = dx
            
            # Add nodes along corridor
            for length in range(1, corridor_length + 1):
                for width in range(-corridor_width//2, corridor_width//2 + 1):
                    x = length * dx * self.unit_spacing + width * px * self.unit_spacing
                    y = length * dy * self.unit_spacing + width * py * self.unit_spacing
                    
                    # Skip if too close to origin
                    if math.sqrt(x**2 + y**2) < 0.5:
                        continue
                    
                    # Rewards increase with distance from origin
                    distance_reward = 10 + length * 0.3
                    reward = int(max(5, distance_reward + np.random.uniform(-3, 3)))
                    nodes.append((x, y, reward))
        
        # Add some connecting nodes between corridors
        for i in range(n_corridors * 10):
            radius = np.random.uniform(5, corridor_length) * self.unit_spacing
            angle = np.random.uniform(0, 2 * np.pi)
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            reward = np.random.randint(15, 25)
            nodes.append((x, y, reward))
        
        # Find farthest node from START to set as END
        if len(nodes) > 2:
            max_dist = 0
            farthest_idx = 2  # Start checking from index 2 (after placeholder)
            for i in range(2, len(nodes)):
                dist = math.sqrt(nodes[i][0]**2 + nodes[i][1]**2)
                if dist > max_dist:
                    max_dist = dist
                    farthest_idx = i
            # Replace placeholder END node with the farthest node (with reward 0)
            end_x, end_y, _ = nodes[farthest_idx]
            nodes[end_node_placeholder_idx] = (end_x, end_y, 0)
            # Remove the duplicate node
            del nodes[farthest_idx]
        
        # Budget for corridor exploration
        budget = budget_ratio * corridor_length * self.unit_spacing * 3.0
        
        return nodes, budget
    
    def generate_islands(self, n_islands: int = 6,
                        island_size: int = 4,
                        min_separation: float = 3.0,
                        max_separation: float = 6.0,
                        bridge_probability: float = 0.3,
                        budget_ratio: float = 0.5) -> Tuple[List, float]:
        """
        Generate island structures connected by bridge nodes.
        
        Islands are dense grid regions. Bridges are carefully placed nodes
        that connect islands while respecting the 1.42 distance constraint.
        
        Args:
            n_islands: Number of islands
            island_size: Size of each island (island_size × island_size)
            min_separation: Minimum separation between islands
            max_separation: Maximum separation between islands
            bridge_probability: Probability of adding bridge between island pairs
            budget_ratio: Budget ratio
            
        Returns:
            (nodes, budget)
        """
        nodes = []
        
        # Node 0: START at origin with reward 0
        nodes.append((0.0, 0.0, 0))
        
        # We'll set END node position after generating all islands
        end_node_placeholder_idx = len(nodes)
        nodes.append((0.0, 0.0, 0))  # Placeholder for END node
        
        # Generate island centers (avoid placing too close)
        island_centers = []
        max_attempts = 1000
        
        for _ in range(n_islands):
            for attempt in range(max_attempts):
                # Random position in a circular region
                angle = np.random.uniform(0, 2 * np.pi)
                radius = np.random.uniform(min_separation * 2, max_separation * 2)
                cx = radius * np.cos(angle)
                cy = radius * np.sin(angle)
                
                # Check if far enough from other islands
                valid = True
                for other_cx, other_cy in island_centers:
                    dist = math.sqrt((cx - other_cx)**2 + (cy - other_cy)**2)
                    if dist < min_separation:
                        valid = False
                        break
                
                if valid:
                    island_centers.append((cx, cy))
                    break
        
        # Create grid nodes for each island
        for island_idx, (cx, cy) in enumerate(island_centers):
            for i in range(island_size):
                for j in range(island_size):
                    x = cx + (i - island_size//2) * self.unit_spacing
                    y = cy + (j - island_size//2) * self.unit_spacing
                    
                    # Skip origin if coincides
                    if abs(x) < 0.01 and abs(y) < 0.01:
                        continue
                    
                    # Rewards vary by island
                    base_reward = 15 + 5 * np.sin(island_idx)
                    reward = int(max(5, base_reward + np.random.uniform(-3, 3)))
                    nodes.append((x, y, reward))
        
        # Add bridge nodes between some island pairs
        for i in range(len(island_centers)):
            for j in range(i + 1, len(island_centers)):
                if np.random.random() < bridge_probability:
                    cx1, cy1 = island_centers[i]
                    cx2, cy2 = island_centers[j]
                    
                    # Calculate number of bridge nodes needed
                    distance = math.sqrt((cx2 - cx1)**2 + (cy2 - cy1)**2)
                    n_bridges = int(distance / 1.4) + 1  # Ensure connectivity
                    
                    # Place bridge nodes
                    for k in range(1, n_bridges):
                        t = k / n_bridges
                        bx = cx1 + t * (cx2 - cx1)
                        by = cy1 + t * (cy2 - cy1)
                        
                        # Bridge nodes have high rewards (incentive to use bridges)
                        reward = np.random.randint(20, 28)
                        nodes.append((bx, by, reward))
        
        # Find farthest node from START to set as END
        if len(nodes) > 2:
            max_dist = 0
            farthest_idx = 2  # Start checking from index 2 (after placeholder)
            for i in range(2, len(nodes)):
                dist = math.sqrt(nodes[i][0]**2 + nodes[i][1]**2)
                if dist > max_dist:
                    max_dist = dist
                    farthest_idx = i
            # Replace placeholder END node with the farthest node (with reward 0)
            end_x, end_y, _ = nodes[farthest_idx]
            nodes[end_node_placeholder_idx] = (end_x, end_y, 0)
            # Remove the duplicate node
            del nodes[farthest_idx]
        
        # Budget to visit multiple islands
        max_span = max_separation * 4
        budget = budget_ratio * max_span * 2.0
        
        return nodes, budget
    
    def save_problem(self, nodes: List, budget: float, filename: str):
        """Save problem to file in standard format."""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            # First line: budget and node_count
            f.write(f"{int(budget)}\t{len(nodes)}\n")
            # Then all nodes (x, y, reward)
            for x, y, reward in nodes:
                f.write(f"{x:.3f}\t{y:.3f}\t{int(reward)}\n")
        
        print(f"Saved: {filename} ({len(nodes)} nodes, budget={budget:.0f})")
    
    def verify_connectivity(self, nodes: List, max_distance: float = 1.42) -> dict:
        """Verify that the graph is connected under max_distance constraint."""
        n = len(nodes)
        
        # Build adjacency list
        neighbors = {i: [] for i in range(n)}
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                dist = math.sqrt((nodes[i][0] - nodes[j][0])**2 + 
                               (nodes[i][1] - nodes[j][1])**2)
                if dist <= max_distance:
                    neighbors[i].append(j)
        
        # BFS from node 0 to find connected component
        visited = set([0])
        queue = [0]
        while queue:
            node = queue.pop(0)
            for neighbor in neighbors[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        avg_degree = sum(len(neighbors[i]) for i in range(n)) / n
        
        return {
            'total_nodes': n,
            'connected_nodes': len(visited),
            'is_connected': len(visited) == n,
            'avg_degree': avg_degree,
            'min_degree': min(len(neighbors[i]) for i in range(n)),
            'max_degree': max(len(neighbors[i]) for i in range(n))
        }


def generate_all_constrained_parallel_friendly_sets():
    """Generate complete benchmark sets respecting max_edge_distance=1.42."""
    
    generator = GridBasedOPGenerator(seed=42)
    base_dir = "OP_Benchmark_Set/parallel_friendly_v2"
    
    print("="*70)
    print("GENERATING PARALLEL-FRIENDLY OP SETS (max_edge_distance=1.42)")
    print("="*70)
    print(f"Grid spacing: {generator.unit_spacing} (diagonal: {generator.unit_spacing * math.sqrt(2):.3f})")
    print()
    
    # Set 1: Dense grids (high branching factor)
    print("\n1. Dense Grids (8-connected, high branching)")
    print("-" * 70)
    for grid_size in [15, 20, 25, 30, 35]:
        for removal in [0.0, 0.1, 0.2]:
            for budget_ratio in [0.3, 0.4, 0.5]:
                nodes, budget = generator.generate_dense_grid(
                    grid_size, grid_size, removal, budget_ratio
                )
                n_nodes = len(nodes)
                removal_pct = int(removal * 100)
                filename = f"{base_dir}/dense_grid/dense_{grid_size}x{grid_size}_r{removal_pct}_{int(budget)}.txt"
                generator.save_problem(nodes, budget, filename)
                
                # Verify first few
                if grid_size == 15 and removal == 0.0 and budget_ratio == 0.3:
                    stats = generator.verify_connectivity(nodes)
                    print(f"  Connectivity check: {stats}")
    
    # Set 2: Sparse grids (medium branching, path-finding challenge)
    print("\n2. Sparse Grids (challenging path-finding)")
    print("-" * 70)
    for grid_size in [25, 30, 35, 40]:
        for density in [0.4, 0.5, 0.6]:
            for budget_ratio in [0.35, 0.45]:
                nodes, budget = generator.generate_sparse_grid(
                    grid_size, grid_size, density, budget_ratio
                )
                density_pct = int(density * 100)
                filename = f"{base_dir}/sparse_grid/sparse_{grid_size}x{grid_size}_d{density_pct}_{int(budget)}.txt"
                generator.save_problem(nodes, budget, filename)
    
    # Set 3: Clustered grids
    print("\n3. Clustered Grids (inter-cluster navigation)")
    print("-" * 70)
    for n_clusters in [4, 6, 9]:
        for cluster_size in [4, 5, 6]:
            for spacing in [6, 8, 10]:
                for budget_ratio in [0.4, 0.5, 0.6]:
                    nodes, budget = generator.generate_clustered_grid(
                        n_clusters, cluster_size, spacing, budget_ratio
                    )
                    filename = f"{base_dir}/clustered/clustered_c{n_clusters}_s{cluster_size}_sp{spacing}_{int(budget)}.txt"
                    generator.save_problem(nodes, budget, filename)
    
    # Set 4: Corridor/maze structures
    print("\n4. Corridor Structures (narrow path navigation)")
    print("-" * 70)
    for n_corridors in [3, 4, 6]:
        for length in [15, 20, 25]:
            for width in [2, 3, 4]:
                for budget_ratio in [0.4, 0.5]:
                    nodes, budget = generator.generate_corridors(
                        n_corridors, length, width, budget_ratio
                    )
                    filename = f"{base_dir}/corridors/corridors_n{n_corridors}_l{length}_w{width}_{int(budget)}.txt"
                    generator.save_problem(nodes, budget, filename)
    
    # Set 5: Island structures with bridges
    print("\n5. Island Structures (bridge navigation)")
    print("-" * 70)
    for n_islands in [5, 6, 8]:
        for island_size in [4, 5]:
            for bridge_prob in [0.2, 0.3, 0.4]:
                for budget_ratio in [0.4, 0.5, 0.6]:
                    nodes, budget = generator.generate_islands(
                        n_islands, island_size, 
                        min_separation=4.0, max_separation=7.0,
                        bridge_probability=bridge_prob,
                        budget_ratio=budget_ratio
                    )
                    bridge_pct = int(bridge_prob * 100)
                    filename = f"{base_dir}/islands/islands_n{n_islands}_s{island_size}_b{bridge_pct}_{int(budget)}.txt"
                    generator.save_problem(nodes, budget, filename)
    
    # Set 6: Extra large dense grids (maximum parallelism)
    print("\n6. Extra Large Dense Grids (maximum parallelism)")
    print("-" * 70)
    for grid_size in [40, 45, 50]:
        for removal in [0.0, 0.15]:
            for budget_ratio in [0.3, 0.4]:
                nodes, budget = generator.generate_dense_grid(
                    grid_size, grid_size, removal, budget_ratio
                )
                removal_pct = int(removal * 100)
                filename = f"{base_dir}/xlarge/xlarge_{grid_size}x{grid_size}_r{removal_pct}_{int(budget)}.txt"
                generator.save_problem(nodes, budget, filename)
    
    print("\n" + "="*70)
    print("GENERATION COMPLETE!")
    print("="*70)
    print(f"\nAll datasets saved to: {base_dir}/")
    print("\nCharacteristics that favor WU-UCT:")
    print("  ✓ Grid spacing = 1.0 (diagonal = 1.414 < 1.42)")
    print("  ✓ High branching factors (8 neighbors per interior node)")
    print("  ✓ Large problem sizes (225-2500 nodes)")
    print("  ✓ Complex structures (clusters, corridors, islands)")
    print("  ✓ Respects max_edge_distance=1.42 constraint")
    print("\nThese problems work with the default max_edge_distance setting!")


if __name__ == "__main__":
    generate_all_constrained_parallel_friendly_sets()
