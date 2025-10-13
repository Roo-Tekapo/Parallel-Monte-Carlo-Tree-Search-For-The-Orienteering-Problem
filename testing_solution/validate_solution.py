"""
Solution Validation Tool for Orienteering Problem
Validates solutions and provides quality metrics
"""

import math
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from orienteering.orienteering import OrienteeringProblem, Node, START_NODE, END_NODE
import numpy as np


def validate_solution(problem: OrienteeringProblem, path: List[int]) -> Dict:
    """
    Validates that a solution satisfies all OP constraints.
    Returns dict with validation results and metrics.
    """
    errors = []
    warnings = []
    
    # Check 1: Path exists and is not empty
    if not path:
        errors.append("Path is empty")
        return {
            'is_valid': False,
            'errors': errors,
            'warnings': warnings,
            'total_reward': 0,
            'total_distance': 0,
            'budget': problem.budget,
            'budget_used_pct': 0,
            'path_length': 0,
            'nodes_visited': 0
        }
    
    # Check 2: Path starts at START_NODE (0) and ends at END_NODE (1)
    if path[0] != START_NODE:
        errors.append(f"Path must start at node {START_NODE}, but starts at {path[0]}")
    if path[-1] != END_NODE:
        errors.append(f"Path must end at node {END_NODE}, but ends at {path[-1]}")
    
    # Check 3: No repeated nodes
    if len(path) != len(set(path)):
        seen = set()
        duplicates = []
        for node in path:
            if node in seen:
                duplicates.append(node)
            seen.add(node)
        errors.append(f"Path contains duplicate nodes: {duplicates}")
    
    # Check 4: All nodes exist in problem
    for node in path:
        if node < 0 or node >= problem.num_nodes:
            errors.append(f"Node {node} does not exist in problem (valid range: 0-{problem.num_nodes-1})")
    
    # Check 5: Budget constraint
    total_distance = 0.0
    for i in range(len(path) - 1):
        if path[i] < problem.num_nodes and path[i+1] < problem.num_nodes:
            total_distance += problem.get_distance(path[i], path[i+1])
    
    if total_distance > problem.budget + 1e-6:  # Small tolerance for floating point
        errors.append(f"Path exceeds budget: {total_distance:.4f} > {problem.budget:.4f} (over by {total_distance - problem.budget:.4f})")
    
    # Check 6: Edge constraints (if max_edge_distance is set)
    if problem.max_edge_distance is not None:
        for i in range(len(path) - 1):
            if path[i] >= problem.num_nodes or path[i+1] >= problem.num_nodes:
                continue
            edge_dist = problem.get_distance(path[i], path[i+1])
            if edge_dist > problem.max_edge_distance + 1e-6:
                errors.append(f"Edge ({path[i]}, {path[i+1]}) exceeds max distance: {edge_dist:.4f} > {problem.max_edge_distance:.4f}")
            
            # Check if nodes are neighbors in graph
            neighbors = problem.get_neighbors(path[i])
            if path[i+1] not in neighbors:
                errors.append(f"Node {path[i+1]} not reachable from {path[i]} (not in neighbor list)")
    
    # Check 7: Calculate total reward
    total_reward = 0
    for node in path:
        if 0 <= node < problem.num_nodes:
            total_reward += problem.nodes[node].score
    
    # Calculate budget utilization
    budget_used_pct = (total_distance / problem.budget) * 100 if problem.budget > 0 else 0
    
    # Warnings for suboptimal solutions
    if budget_used_pct < 50:
        warnings.append(f"Low budget utilization: {budget_used_pct:.1f}% - solution may be suboptimal")
    
    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'total_reward': total_reward,
        'total_distance': total_distance,
        'budget': problem.budget,
        'budget_used_pct': budget_used_pct,
        'slack': problem.budget - total_distance,
        'path_length': len(path),
        'nodes_visited': len(set(path))
    }


def calculate_upper_bound(problem: OrienteeringProblem) -> Tuple[float, str]:
    """
    Compute a meaningful upper-bound estimate for the instance.

    Uses a simple greedy heuristic that provides a loose but reasonable upper bound:
    - Sorts all nodes by score (highest first)
    - Greedily adds nodes assuming we pay only the minimum edge distance to reach each one
    - This is optimistic because real paths must connect nodes sequentially
    
    This bound is guaranteed to be >= any feasible solution because:
    1. We assume the most optimistic distances (minimum edges)
    2. Real solutions must pay for full sequential routing
    
    Returns (upper_bound_reward, explanation)
    """
    available_nodes = [n for n in problem.nodes if n.id not in [START_NODE, END_NODE]]
    
    # Sort by score (highest first)
    sorted_nodes = sorted(available_nodes, key=lambda n: n.score, reverse=True)
    
    # Start with base reward and minimum distance (start to end)
    upper_bound_reward = problem.nodes[START_NODE].score + problem.nodes[END_NODE].score
    budget_used = problem.get_distance(START_NODE, END_NODE)
    selected_count = 0
    
    for node in sorted_nodes:
        # Optimistic minimum distance to visit this node:
        # Assume we can reach it via the shortest possible edge from start
        # and return via shortest edge to end
        dist_from_start = problem.get_distance(START_NODE, node.id)
        dist_to_end = problem.get_distance(node.id, END_NODE)
        
        # Optimistic detour cost (ignores that we can't actually insert optimally)
        # Assume we replace the direct start->end with start->node->end
        detour_cost = dist_from_start + dist_to_end
        
        if detour_cost <= problem.budget:
            # Can we afford to add this node's detour to our current path?
            # Use even more optimistic assumption: just the minimum edge to this node
            min_edge_to_node = min(problem.get_distance(i, node.id) 
                                  for i in range(len(problem.nodes)) 
                                  if i != node.id)
            
            # Very optimistic: assume we only pay the min edge cost
            if budget_used + min_edge_to_node <= problem.budget:
                upper_bound_reward += node.score
                budget_used += min_edge_to_node
                selected_count += 1

    explanation = (
        f"Optimistic greedy bound: selected top {selected_count} nodes by score, "
        f"assuming minimum edge distances (ignores sequential routing constraints)."
    )

    return float(upper_bound_reward), explanation


def _can_reach_end_with_bfs(problem: OrienteeringProblem, from_node: int, 
                            current_cost: float, visited: set) -> Tuple[bool, List[int], float]:
    """
    Use BFS to find shortest path to END_NODE that respects graph connectivity.
    Returns (can_reach, path_to_end, additional_cost)
    """
    from collections import deque
    
    if from_node == END_NODE:
        return True, [], 0.0
    
    # BFS to find shortest path to END
    queue = deque([(from_node, [from_node], 0.0)])
    bfs_visited = {from_node}
    
    while queue:
        node, path_so_far, cost_so_far = queue.popleft()
        
        neighbors = problem.get_neighbors(node)
        
        for neighbor in neighbors:
            if neighbor in visited and neighbor != END_NODE:
                continue  # Don't revisit nodes in main path
            if neighbor in bfs_visited and neighbor != END_NODE:
                continue
            
            edge_cost = problem.get_distance(node, neighbor)
            new_cost = cost_so_far + edge_cost
            
            if current_cost + new_cost > problem.budget:
                continue  # Would exceed budget
            
            if neighbor == END_NODE:
                # Found path to end!
                return True, path_so_far[1:] + [END_NODE], new_cost
            
            bfs_visited.add(neighbor)
            queue.append((neighbor, path_so_far + [neighbor], new_cost))
    
    return False, [], 0.0


def greedy_nearest_neighbor(problem: OrienteeringProblem) -> Tuple[List[int], float]:
    """
    Greedy baseline: always go to nearest high-value node that maintains path to END.
    Returns (path, total_reward)
    """
    path = [START_NODE]
    visited = {START_NODE}
    current = START_NODE
    total_distance = 0.0
    
    max_iterations = problem.num_nodes * 2  # Prevent infinite loops
    iteration = 0
    
    while current != END_NODE and iteration < max_iterations:
        iteration += 1
        best_node = None
        best_score_per_dist = -float('inf')
        
        neighbors = problem.get_neighbors(current)
        
        # Try to find the best scoring neighbor that still allows reaching END
        for node_id in neighbors:
            if node_id in visited or node_id == START_NODE:
                continue
            
            dist_to_node = problem.get_distance(current, node_id)
            new_cost = total_distance + dist_to_node
            
            if new_cost > problem.budget:
                continue
            
            # Check if we can reach END from this node
            new_visited = visited | {node_id}
            can_reach, path_to_end, cost_to_end = _can_reach_end_with_bfs(
                problem, node_id, new_cost, new_visited
            )
            
            if not can_reach:
                continue  # Dead end
            
            if node_id == END_NODE:
                # Can go directly to end
                best_node = END_NODE
                break
            
            # Score this option
            score_per_dist = problem.nodes[node_id].score / dist_to_node if dist_to_node > 0 else float('inf')
            
            if score_per_dist > best_score_per_dist:
                best_node = node_id
                best_score_per_dist = score_per_dist
        
        # If no good neighbor found, just navigate to END
        if best_node is None:
            can_reach, path_to_end, cost_to_end = _can_reach_end_with_bfs(
                problem, current, total_distance, visited
            )
            if can_reach and len(path_to_end) > 0:
                # Follow the path to end
                for node in path_to_end:
                    if node not in visited:
                        path.append(node)
                        total_distance += problem.get_distance(current, node)
                        visited.add(node)
                        current = node
                break
            else:
                # Can't reach end - failed
                break
        
        # Move to best_node
        path.append(best_node)
        visited.add(best_node)
        total_distance += problem.get_distance(current, best_node)
        current = best_node
    
    # Calculate reward
    total_reward = sum(problem.nodes[node].score for node in path)
    return path, total_reward


def compare_solutions(problem: OrienteeringProblem, solutions: Dict[str, List[int]]) -> None:
    """
    Compare multiple solutions and print a summary table.
    solutions: dict of {name: path}
    """
    print("\n" + "="*80)
    print("SOLUTION COMPARISON")
    print("="*80)
    
    results = []
    for name, path in solutions.items():
        validation = validate_solution(problem, path)
        results.append((name, validation))
    
    # Sort by reward descending
    results.sort(key=lambda x: x[1]['total_reward'], reverse=True)
    
    # Print table
    print(f"\n{'Algorithm':<25} {'Valid':<8} {'Reward':<10} {'Distance':<12} {'Budget %':<10} {'Nodes':<8}")
    print("-"*80)
    
    for name, val in results:
        valid_str = "✓" if val['is_valid'] else "✗"
        print(f"{name:<25} {valid_str:<8} {val['total_reward']:<10} "
              f"{val['total_distance']:<12.2f} {val['budget_used_pct']:<10.1f} "
              f"{val['nodes_visited']:<8}")
    
    print("\n" + "="*80)


def print_validation_report(problem: OrienteeringProblem, path: List[int], algorithm_name: str = "Solution") -> None:
    """
    Print a detailed validation report for a single solution.
    """
    print("\n" + "="*80)
    print(f"VALIDATION REPORT: {algorithm_name}")
    print("="*80)
    
    validation = validate_solution(problem, path)
    
    # Basic info
    print(f"\nProblem: {problem.num_nodes} nodes, Budget: {problem.budget:.2f}")
    if problem.max_edge_distance:
        print(f"Max Edge Distance: {problem.max_edge_distance:.2f}")
    
    # Validation status
    print(f"\n{'Status:':<20} {'VALID ✓' if validation['is_valid'] else 'INVALID ✗'}")
    
    # Metrics
    print(f"\n{'Metric':<25} {'Value'}")
    print("-"*50)
    print(f"{'Total Reward':<25} {validation['total_reward']}")
    print(f"{'Total Distance':<25} {validation['total_distance']:.4f}")
    print(f"{'Budget':<25} {validation['budget']:.4f}")
    print(f"{'Budget Used':<25} {validation['budget_used_pct']:.2f}%")
    print(f"{'Slack (remaining)':<25} {validation['slack']:.4f}")
    print(f"{'Path Length':<25} {validation['path_length']}")
    print(f"{'Unique Nodes Visited':<25} {validation['nodes_visited']}")
    
    # Path
    print(f"\nPath: {path}")
    
    # Errors
    if validation['errors']:
        print(f"\n{'ERRORS:':^50}")
        print("-"*50)
        for error in validation['errors']:
            print(f"  ✗ {error}")
    
    # Warnings
    if validation['warnings']:
        print(f"\n{'WARNINGS:':^50}")
        print("-"*50)
        for warning in validation['warnings']:
            print(f"  ⚠ {warning}")
    
    # Comparison to baselines
    print(f"\n{'QUALITY METRICS':^50}")
    print("-"*50)
    
    # Upper bound
    upper_bound, ub_explanation = calculate_upper_bound(problem)
    optimality_gap = ((upper_bound - validation['total_reward']) / upper_bound * 100) if upper_bound > 0 else 0
    print(f"Upper Bound: {upper_bound:.0f}")
    print(f"Optimality Gap: {optimality_gap:.1f}% (lower is better)")
    print(f"  ({ub_explanation})")
    
    # Greedy baseline
    greedy_path, greedy_reward = greedy_nearest_neighbor(problem)
    greedy_validation = validate_solution(problem, greedy_path)
    if greedy_validation['is_valid']:
        improvement = ((validation['total_reward'] - greedy_reward) / greedy_reward * 100) if greedy_reward > 0 else 0
        print(f"\nGreedy Baseline: {greedy_reward:.0f}")
        print(f"Improvement over Greedy: {improvement:+.1f}%")
    else:
        print(f"\nGreedy Baseline: Failed to find valid solution")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python validate_solution.py <problem_file> [solution_path]")
        print("\nExample:")
        print("  python validate_solution.py OP_Benchmark_Set/set_64_1/set_64_1_80.txt")
        print("  python validate_solution.py OP_Benchmark_Set/set_64_1/set_64_1_80.txt \"0,5,12,7,1\"")
        sys.exit(1)
    
    # Load problem
    problem_file = sys.argv[1]
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)
    
    print(f"Loaded problem from: {problem_file}")
    print(f"  Nodes: {problem.num_nodes}")
    print(f"  Budget: {budget}")
    
    if len(sys.argv) >= 3:
        # Validate provided solution
        path_str = sys.argv[2]
        path = [int(x.strip()) for x in path_str.split(',')]
        print_validation_report(problem, path, "Provided Solution")
    else:
        # Run greedy baseline for demonstration
        print("\nNo solution provided. Running greedy baseline for demonstration...")
        greedy_path, greedy_reward = greedy_nearest_neighbor(problem)
        print_validation_report(problem, greedy_path, "Greedy Nearest Neighbor")
