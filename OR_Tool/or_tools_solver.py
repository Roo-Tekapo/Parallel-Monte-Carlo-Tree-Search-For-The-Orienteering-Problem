"""
OR-Tools solver for the Orienteering Problem (Prize-Collecting TSP variant)

This module uses Google OR-Tools to find optimal or near-optimal solutions
for orienteering problem instances from the benchmark set.
"""

import sys
import os
import time
from typing import List, Tuple, Optional
import math

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from orienteering.orienteering import OrienteeringProblem, Node


class ORToolsOrienteeringSolver:
    """
    Solves the Orienteering Problem using Google OR-Tools routing solver.
    
    The orienteering problem is formulated as a vehicle routing problem with:
    - Single vehicle (one tour)
    - Distance constraint (budget)
    - Maximize collected rewards (node scores)
    """
    
    def __init__(self, problem: OrienteeringProblem, time_limit_seconds: int = 30):
        """
        Initialize the OR-Tools solver.
        
        Args:
            problem: OrienteeringProblem instance
            time_limit_seconds: Time limit for the solver
        """
        self.problem = problem
        self.time_limit_seconds = time_limit_seconds
        self.num_nodes = problem.num_nodes
        
        # Create distance matrix (scaled to integers for OR-Tools)
        self.distance_scale = 10000  # Scale factor for distance precision
        self.distance_matrix = self._create_distance_matrix()
        
        # Node rewards (scores)
        self.rewards = [node.score for node in problem.nodes]
        
    def _create_distance_matrix(self) -> List[List[int]]:
        """Create integer distance matrix scaled for OR-Tools."""
        matrix = []
        for i in range(self.num_nodes):
            row = []
            for j in range(self.num_nodes):
                dist = self.problem.get_distance(i, j)
                scaled_dist = int(dist * self.distance_scale)
                row.append(scaled_dist)
            matrix.append(row)
        return matrix
    
    def _distance_callback(self, from_index: int, to_index: int) -> int:
        """Returns the distance between two nodes."""
        from_node = self.manager.IndexToNode(from_index)
        to_node = self.manager.IndexToNode(to_index)
        return self.distance_matrix[from_node][to_node]
    
    def _reward_callback(self, index: int) -> int:
        """Returns the reward (score) for visiting a node."""
        node = self.manager.IndexToNode(index)
        return self.rewards[node]
    
    def solve(self, verbose: bool = True) -> Tuple[List[int], float, float, dict]:
        """
        Solve the orienteering problem using OR-Tools.
        
        Args:
            verbose: Whether to print progress information
            
        Returns:
            Tuple of (path, total_reward, total_distance, stats)
        """
        if verbose:
            print("Setting up OR-Tools routing model...")
        
        # Create the routing index manager
        # Orienteering problem: Start at node 0
        # Traditional: end at node 1
        # No-end variant: can end at any node (use node 0 as end for routing purposes)
        # (as per problem specification: first point is start, second is end)
        # Use the multi-depot API with lists of start/end nodes
        
        # Check if problem supports is_no_end_variant (for no-end problems)
        is_no_end = hasattr(self.problem, 'is_no_end_variant') and self.problem.is_no_end_variant
        
        if is_no_end:
            # No-end variant: can end anywhere, use node 0 as dummy end
            self.manager = pywrapcp.RoutingIndexManager(
                self.num_nodes,  # number of nodes
                1,               # number of vehicles (tours)
                [0],             # start depots (list with node 0)
                [0]              # end depots (same as start for open tour)
            )
        else:
            # Traditional: must end at node 1
            self.manager = pywrapcp.RoutingIndexManager(
                self.num_nodes,  # number of nodes
                1,               # number of vehicles (tours)
                [0],             # start depots (list with node 0)
                [1]              # end depots (list with node 1)
            )
        
        # Create routing model
        routing = pywrapcp.RoutingModel(self.manager)
        
        # Register distance callback
        transit_callback_index = routing.RegisterTransitCallback(self._distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Add distance constraint (budget)
        scaled_budget = int(self.problem.budget * self.distance_scale)
        dimension_name = 'Distance'
        routing.AddDimension(
            transit_callback_index,
            0,              # no slack
            scaled_budget,  # maximum distance (budget)
            True,           # start cumul to zero
            dimension_name
        )
        
        # Make all intermediate nodes optional (can skip nodes)
        # Traditional: Nodes 0 and 1 are start/end and must be visited
        # No-end: Only node 0 is start and must be visited
        # CRITICAL: OR-Tools MINIMIZES cost. To maximize rewards:
        # - Give HIGH penalties for skipping HIGH-reward nodes
        # - Give LOW penalties for skipping LOW-reward nodes
        max_reward = max(self.rewards) if self.rewards else 0
        penalty_multiplier = 1000000  # Large multiplier to prioritize rewards over distance
        
        # Determine which nodes to skip based on variant
        if is_no_end:
            skip_start = 2  # Skip start (0) and dummy node (1) if exists
        else:
            skip_start = 2  # Skip start (0) and end (1) depots
        
        for node in range(skip_start, self.num_nodes):
            # Penalty for NOT visiting this node = reward * multiplier
            # High-reward nodes have high penalty for skipping (expensive to skip)
            # Low-reward nodes have low penalty for skipping (cheap to skip)
            penalty = int(self.rewards[node] * penalty_multiplier)
            routing.AddDisjunction([self.manager.NodeToIndex(node)], penalty)
        
        # Set objective: minimize negative rewards (= maximize rewards)
        # We need to maximize rewards while respecting distance constraint
        # Use disjunctions with large penalties to encourage visiting high-reward nodes
        
        # Alternative: Use SetPrimary/SecondaryObjective if available
        # routing.SetPrimaryObjective(pywrapcp.RoutingModel.ROUTING_OBJECTIVE_MAXIMIZE)
        
        # Set search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        
        # Choose search strategy - try PATH_MOST_CONSTRAINED_ARC for better initial solutions
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
        )
        
        # Set metaheuristic for improvement - use SIMULATED_ANNEALING for better exploration
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING
        )
        
        # Set time limit
        search_parameters.time_limit.seconds = self.time_limit_seconds
        search_parameters.log_search = False  # Reduce log verbosity
        
        if verbose:
            print(f"Solving with time limit of {self.time_limit_seconds} seconds...")
            print(f"Budget: {self.problem.budget}")
            print(f"Nodes: {self.num_nodes}")
        
        # Solve the problem
        start_time = time.time()
        solution = routing.SolveWithParameters(search_parameters)
        solve_time = time.time() - start_time
        
        if solution:
            if verbose:
                print(f"\nSolution found in {solve_time:.2f} seconds!")
            
            # Extract solution
            path, total_reward, total_distance = self._extract_solution(
                routing, self.manager, solution
            )
            
            stats = {
                'solve_time': solve_time,
                'objective_value': solution.ObjectiveValue(),
                'status': 'SOLVED'
            }
            
            return path, total_reward, total_distance, stats
        else:
            if verbose:
                print(f"\nNo solution found in {solve_time:.2f} seconds!")
            
            stats = {
                'solve_time': solve_time,
                'objective_value': None,
                'status': 'NO_SOLUTION'
            }
            
            return [], 0.0, 0.0, stats
    
    def _extract_solution(self, routing, manager, solution) -> Tuple[List[int], float, float]:
        """Extract the path and metrics from the solution."""
        path = []
        total_reward = 0.0
        total_distance = 0.0
        
        index = routing.Start(0)  # Start at depot
        
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            path.append(node)
            total_reward += self.rewards[node]
            
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            
            if not routing.IsEnd(index):
                from_node = manager.IndexToNode(previous_index)
                to_node = manager.IndexToNode(index)
                total_distance += self.problem.get_distance(from_node, to_node)
        
        # Add final node (back to depot)
        final_node = manager.IndexToNode(index)
        path.append(final_node)
        
        # Add distance from last visited node to depot
        if len(path) > 1:
            total_distance += self.problem.get_distance(path[-2], path[-1])
        
        return path, total_reward, total_distance
    
    def print_solution(self, path: List[int], reward: float, distance: float, stats: dict):
        """Print detailed solution information."""
        print("\n" + "="*80)
        print("OR-TOOLS SOLUTION")
        print("="*80)
        print(f"\nPath: {' -> '.join(map(str, path))}")
        print(f"Total Reward: {reward:.2f}")
        print(f"Total Distance: {distance:.4f} / {self.problem.budget:.4f}")
        print(f"Distance Used: {(distance/self.problem.budget*100):.1f}%")
        print(f"Nodes Visited: {len(path)}")
        print(f"\nSolve Time: {stats['solve_time']:.2f} seconds")
        print(f"Status: {stats['status']}")
        
        # Validate solution
        print("\n" + "-"*80)
        print("VALIDATION")
        print("-"*80)
        
        is_valid = True
        
        # Check budget constraint
        if distance > self.problem.budget + 1e-6:
            print(f"❌ Budget violated: {distance:.4f} > {self.problem.budget:.4f}")
            is_valid = False
        else:
            print(f"✓ Budget satisfied: {distance:.4f} <= {self.problem.budget:.4f}")
        
        # Check start/end at correct nodes
        is_no_end = hasattr(self.problem, 'is_no_end_variant') and self.problem.is_no_end_variant
        
        if path[0] != 0:
            print(f"❌ Path doesn't start at node 0 (start depot)")
            is_valid = False
        else:
            print(f"✓ Path starts at node 0 (start depot)")
        
        if is_no_end:
            # No-end variant: path can end anywhere
            print(f"✓ Path ends at node {path[-1]} (no-end variant allows any ending)")
        else:
            # Traditional variant: must end at node 1
            if path[-1] != 1:
                print(f"❌ Path doesn't end at node 1 (end depot)")
                is_valid = False
            else:
                print(f"✓ Path ends at node 1 (end depot)")
        
        # Check no duplicate nodes (start and end are different, so all should be unique)
        if len(path) != len(set(path)):
            print(f"❌ Path contains duplicate nodes")
            is_valid = False
        else:
            print(f"✓ No duplicate nodes in path")
        
        if is_valid:
            print("\n✅ Solution is VALID")
        else:
            print("\n❌ Solution is INVALID")
        
        print("="*80)


def solve_benchmark_problem(problem_file: str, 
                           time_limit: int = 30,
                           verbose: bool = True) -> dict:
    """
    Solve a single benchmark problem.
    
    Args:
        problem_file: Path to the problem file
        time_limit: Time limit in seconds
        verbose: Whether to print detailed output
        
    Returns:
        Dictionary with results
    """
    if verbose:
        print("\n" + "="*80)
        print(f"SOLVING: {problem_file}")
        print("="*80)
    
    # Load problem
    try:
        nodes, budget = OrienteeringProblem.load_problem(problem_file)
        problem = OrienteeringProblem(nodes, budget)
        
        if verbose:
            print(f"Loaded: {len(nodes)} nodes, budget: {budget}")
    except Exception as e:
        print(f"ERROR loading problem: {e}")
        return None
    
    # Solve with OR-Tools
    solver = ORToolsOrienteeringSolver(problem, time_limit_seconds=time_limit)
    path, reward, distance, stats = solver.solve(verbose=verbose)
    
    if verbose:
        solver.print_solution(path, reward, distance, stats)
    
    return {
        'problem_file': problem_file,
        'num_nodes': len(nodes),
        'budget': budget,
        'path': path,
        'reward': reward,
        'distance': distance,
        'solve_time': stats['solve_time'],
        'status': stats['status']
    }


def batch_solve_directory(directory: str, 
                          time_limit: int = 30,
                          pattern: str = "*.txt") -> List[dict]:
    """
    Solve all problems in a directory.
    
    Args:
        directory: Directory containing problem files
        time_limit: Time limit per problem in seconds
        pattern: File pattern to match
        
    Returns:
        List of result dictionaries
    """
    import glob
    
    problem_files = glob.glob(os.path.join(directory, pattern))
    
    if not problem_files:
        print(f"No problem files found in {directory} matching {pattern}")
        return []
    
    print(f"\nFound {len(problem_files)} problem files")
    print("="*80)
    
    results = []
    
    for i, problem_file in enumerate(problem_files, 1):
        print(f"\n[{i}/{len(problem_files)}] Processing {problem_file}...")
        
        result = solve_benchmark_problem(problem_file, time_limit=time_limit, verbose=True)
        
        if result:
            results.append(result)
    
    return results


def print_summary(results: List[dict]):
    """Print summary of all results."""
    if not results:
        print("\nNo results to summarize.")
        return
    
    print("\n" + "="*80)
    print("SUMMARY OF ALL RESULTS")
    print("="*80)
    
    total_solved = sum(1 for r in results if r['status'] == 'SOLVED')
    total_reward = sum(r['reward'] for r in results)
    avg_solve_time = sum(r['solve_time'] for r in results) / len(results)
    
    print(f"\nProblems Solved: {total_solved}/{len(results)}")
    print(f"Total Reward Collected: {total_reward:.2f}")
    print(f"Average Solve Time: {avg_solve_time:.2f} seconds")
    
    print("\n" + "-"*80)
    print(f"{'Problem':<50} {'Reward':<10} {'Time (s)':<10}")
    print("-"*80)
    
    for result in results:
        problem_name = os.path.basename(result['problem_file'])
        print(f"{problem_name:<50} {result['reward']:<10.2f} {result['solve_time']:<10.2f}")
    
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Solve Orienteering Problem using OR-Tools"
    )
    parser.add_argument(
        'problem_file',
        nargs='?',
        help='Problem file or directory to solve'
    )
    parser.add_argument(
        '--time-limit',
        type=int,
        default=30,
        help='Time limit in seconds per problem (default: 30)'
    )
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Solve all problems in directory'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimal output'
    )
    
    args = parser.parse_args()
    
    if not args.problem_file:
        # Default: run on sample problems
        print("No problem file specified. Using default samples...")
        args.problem_file = "OP_Benchmark_Set/sample"
        args.batch = True
    
    if args.batch:
        # Batch mode: solve all problems in directory
        results = batch_solve_directory(
            args.problem_file,
            time_limit=args.time_limit
        )
        print_summary(results)
    else:
        # Single problem mode
        result = solve_benchmark_problem(
            args.problem_file,
            time_limit=args.time_limit,
            verbose=not args.quiet
        )
