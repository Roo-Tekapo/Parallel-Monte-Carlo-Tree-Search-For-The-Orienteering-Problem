"""
Optimal (or near-optimal) solver for Orienteering Problem instances.

Uses dynamic programming with state-space pruning to find the best possible path.
For larger instances, uses beam search or time-limited branch-and-bound.
"""

import time
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional
from collections import defaultdict
import heapq

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from orienteering.orienteering import OrienteeringProblem, START_NODE, END_NODE
from testing_solution.validate_solution import validate_solution, print_validation_report


def solve_dp_optimal(problem: OrienteeringProblem, max_time_seconds: float = 60.0) -> Tuple[List[int], float, str]:
    """
    Dynamic Programming approach to find optimal solution.
    
    State: (current_node, visited_set, cost_so_far) -> max_reward
    This can be exponential but works well for small/medium instances (< 20-25 nodes).
    
    Returns: (best_path, best_reward, method_description)
    """
    start_time = time.time()
    
    # State: (node, frozenset of visited, cost) -> (reward, path)
    # We'll use memoization with pruning
    best_solution = ([START_NODE], 0.0)
    
    # Priority queue: (-reward, cost, current_node, visited_set, path)
    # Use negative reward for max-heap behavior
    initial_state = (0, 0.0, START_NODE, frozenset([START_NODE]), [START_NODE])
    queue = [initial_state]
    
    visited_states = {}  # (node, visited_set) -> (best_reward, cost)
    nodes_explored = 0
    
    while queue and (time.time() - start_time) < max_time_seconds:
        neg_reward, cost, current, visited_set, path = heapq.heappop(queue)
        reward = -neg_reward
        nodes_explored += 1
        
        # Skip if we've seen this state with better reward
        state_key = (current, visited_set)
        if state_key in visited_states:
            prev_reward, prev_cost = visited_states[state_key]
            if prev_reward >= reward:
                continue
        visited_states[state_key] = (reward, cost)
        
        # If at END_NODE, check if this is best solution
        if current == END_NODE:
            if reward > best_solution[1]:
                best_solution = (path, reward)
            continue
        
        # Try all neighbors
        neighbors = problem.get_neighbors(current)
        
        for next_node in neighbors:
            if next_node in visited_set and next_node != END_NODE:
                continue
            
            edge_cost = problem.get_distance(current, next_node)
            new_cost = cost + edge_cost
            
            if new_cost > problem.budget:
                continue
            
            # For non-END nodes, check if we can still reach END
            if next_node != END_NODE:
                min_cost_to_end = problem.get_distance(next_node, END_NODE)
                if new_cost + min_cost_to_end > problem.budget:
                    continue
            
            new_visited = visited_set | {next_node}
            new_reward = reward + problem.nodes[next_node].score
            new_path = path + [next_node]
            
            # Add to queue
            heapq.heappush(queue, (-new_reward, new_cost, next_node, new_visited, new_path))
    
    elapsed = time.time() - start_time
    method = f"DP-based search (explored {nodes_explored} states in {elapsed:.2f}s)"
    
    return best_solution[0], best_solution[1], method


def solve_beam_search(problem: OrienteeringProblem, beam_width: int = 1000, 
                      max_time_seconds: float = 60.0) -> Tuple[List[int], float, str]:
    """
    Beam search: keeps only the top beam_width states at each depth level.
    Faster than full DP but may not find optimal solution for complex instances.
    
    Returns: (best_path, best_reward, method_description)
    """
    start_time = time.time()
    
    # State: (reward, cost, current_node, visited_set, path)
    current_beam = [(0, 0.0, START_NODE, frozenset([START_NODE]), [START_NODE])]
    best_solution = ([START_NODE], 0.0)
    
    max_depth = problem.num_nodes
    nodes_explored = 0
    
    for depth in range(max_depth):
        if (time.time() - start_time) > max_time_seconds or not current_beam:
            break
        
        next_beam = []
        seen_states = {}  # (node, visited) -> best_reward
        
        for reward, cost, current, visited_set, path in current_beam:
            nodes_explored += 1
            
            # If at END, record solution
            if current == END_NODE:
                if reward > best_solution[1]:
                    best_solution = (path, reward)
                continue
            
            # Expand neighbors
            neighbors = problem.get_neighbors(current)
            
            for next_node in neighbors:
                if next_node in visited_set and next_node != END_NODE:
                    continue
                
                edge_cost = problem.get_distance(current, next_node)
                new_cost = cost + edge_cost
                
                if new_cost > problem.budget:
                    continue
                
                # Check if we can reach END
                if next_node != END_NODE:
                    min_cost_to_end = problem.get_distance(next_node, END_NODE)
                    if new_cost + min_cost_to_end > problem.budget:
                        continue
                
                new_visited = visited_set | {next_node}
                new_reward = reward + problem.nodes[next_node].score
                new_path = path + [next_node]
                
                # Prune dominated states
                state_key = (next_node, new_visited)
                if state_key in seen_states:
                    if seen_states[state_key] >= new_reward:
                        continue
                seen_states[state_key] = new_reward
                
                next_beam.append((new_reward, new_cost, next_node, new_visited, new_path))
        
        # Keep only top beam_width states by reward
        next_beam.sort(reverse=True, key=lambda x: x[0])
        current_beam = next_beam[:beam_width]
    
    elapsed = time.time() - start_time
    method = f"Beam search (width={beam_width}, explored {nodes_explored} states in {elapsed:.2f}s)"
    
    return best_solution[0], best_solution[1], method


def solve_best_path(problem: OrienteeringProblem, method: str = "auto", 
                    max_time_seconds: float = 60.0) -> Tuple[List[int], float, str]:
    """
    Find the best path using the specified method.
    
    Args:
        problem: OrienteeringProblem instance
        method: "dp" (exact DP), "beam" (beam search), or "auto" (choose based on size)
        max_time_seconds: Time limit for search
    
    Returns: (best_path, best_reward, method_description)
    """
    
    if method == "auto":
        # Choose method based on problem size
        if problem.num_nodes <= 20:
            method = "dp"
        else:
            method = "beam"
    
    if method == "dp":
        return solve_dp_optimal(problem, max_time_seconds)
    elif method == "beam":
        beam_width = min(5000, max(1000, problem.num_nodes * 50))
        return solve_beam_search(problem, beam_width, max_time_seconds)
    else:
        raise ValueError(f"Unknown method: {method}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python solve_optimal.py <problem_file> [method] [time_limit]")
        print("\nMethods:")
        print("  dp    - Dynamic programming (exact, for small instances)")
        print("  beam  - Beam search (fast, near-optimal for larger instances)")
        print("  auto  - Automatically choose based on problem size (default)")
        print("\nExamples:")
        print("  python solve_optimal.py OP_Benchmark_Set/set_64_1/set_64_1_80.txt")
        print("  python solve_optimal.py OP_Benchmark_Set/set_64_1/set_64_1_80.txt beam 120")
        sys.exit(1)
    
    problem_file = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) >= 3 else "auto"
    time_limit = float(sys.argv[3]) if len(sys.argv) >= 4 else 60.0
    
    # Load problem
    print("="*80)
    print("OPTIMAL PATH FINDER FOR ORIENTEERING PROBLEM")
    print("="*80)
    print(f"\nProblem file: {problem_file}")
    
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)
    
    print(f"Problem size: {problem.num_nodes} nodes")
    print(f"Budget: {budget}")
    print(f"Max edge distance: {problem.max_edge_distance}")
    print(f"\nSolver method: {method}")
    print(f"Time limit: {time_limit}s")
    print("\nSearching for optimal path...")
    print("-"*80)
    
    # Solve
    start = time.time()
    best_path, best_reward, method_desc = solve_best_path(problem, method, time_limit)
    elapsed = time.time() - start
    
    print(f"\n{method_desc}")
    print(f"Total time: {elapsed:.2f}s")
    
    # Validate and print report
    print_validation_report(problem, best_path, f"Optimal Solver ({method})")
    
    # Compare with greedy
    from validate_solution import greedy_nearest_neighbor
    greedy_path, greedy_reward = greedy_nearest_neighbor(problem)
    greedy_val = validate_solution(problem, greedy_path)
    
    if greedy_val['is_valid']:
        improvement = ((best_reward - greedy_reward) / greedy_reward * 100) if greedy_reward > 0 else 0
        print("\n" + "="*80)
        print("COMPARISON WITH GREEDY BASELINE")
        print("="*80)
        print(f"Optimal solution reward: {best_reward:.0f}")
        print(f"Greedy baseline reward:  {greedy_reward:.0f}")
        print(f"Improvement:             {improvement:+.1f}%")
        print(f"\nOptimal path: {best_path}")
        print(f"Greedy path:  {greedy_path}")
        print("="*80)
