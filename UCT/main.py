#!/usr/bin/env python3
"""
Main entry point for UCT algorithms.
Supports both single-threaded UCT and parallel WU-UCT.
"""

import argparse
import sys
import os
import time
import math

# Add parent directory to path to import orienteering
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orienteering.orienteering import OrienteeringProblem
from UCT.uct_single_thread import UCTSingleThread
from UCT.wu_uct_coordinator import WUUCT


def main():
    parser = argparse.ArgumentParser(description='UCT and WU-UCT algorithms for the Orienteering Problem')
    
    parser.add_argument('--problem-file', type=str, required=True,
                       help='Path to the orienteering problem file')
    parser.add_argument('--algorithm', type=str, choices=['uct', 'wu-uct'], default='wu-uct',
                       help='Algorithm to use (default: wu-uct)')
    parser.add_argument('--max-iterations', type=int, default=100000,
                       help='Maximum number of iterations (default: 100000)')
    parser.add_argument('--exploration-constant', type=float, default=math.sqrt(2),
                       help='UCT exploration constant (default: sqrt(2))')
    parser.add_argument('--simulation-workers', type=int, default=4,
                       help='Number of simulation workers for WU-UCT (default: 4)')
    parser.add_argument('--expansion-workers', type=int, default=1,
                       help='Number of expansion workers for WU-UCT (must be 1, default: 1)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--output-file', type=str,
                       help='Output file to save results')
    
    args = parser.parse_args()
    
    # Validate expansion workers for WU-UCT
    if args.algorithm == 'wu-uct' and args.expansion_workers != 1:
        print("ERROR: WU-UCT requires exactly 1 expansion worker")
        sys.exit(1)
    
    # Load problem
    try:
        nodes, budget = OrienteeringProblem.load_problem(args.problem_file)
        problem = OrienteeringProblem(nodes, budget)
        
        if args.verbose:
            print(f"Loaded problem: {len(nodes)} nodes, budget: {budget}")
            print(f"Problem file: {args.problem_file}")
    except Exception as e:
        print(f"ERROR: Failed to load problem file: {e}")
        sys.exit(1)
    
    # Run algorithm
    start_time = time.time()
    
    if args.algorithm == 'uct':
        if args.verbose:
            print(f"Running single-threaded UCT with {args.max_iterations} iterations")
        
        uct = UCTSingleThread(problem, 
                             iterations=args.max_iterations,
                             exploration_constant=args.exploration_constant)
        best_state = uct.run()
        
        if args.verbose:
            stats = uct.get_statistics()
            print(f"UCT Statistics: {stats}")
    
    elif args.algorithm == 'wu-uct':
        if args.verbose:
            print(f"Running WU-UCT with {args.max_iterations} iterations")
            print(f"Expansion workers: {args.expansion_workers}")
            print(f"Simulation workers: {args.simulation_workers}")
        
        wu_uct = WUUCT(problem,
                      expansion_workers=args.expansion_workers,
                      simulation_workers=args.simulation_workers,
                      exploration_constant=args.exploration_constant)
        
        best_state = wu_uct.run(max_iterations=args.max_iterations, verbose=args.verbose)
        
        if args.verbose:
            stats = wu_uct.get_statistics()
            print(f"WU-UCT Statistics: {stats}")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Print results
    print(f"\nResults:")
    print(f"Algorithm: {args.algorithm.upper()}")
    print(f"Best path: {best_state.get_path()}")
    print(f"Total reward: {best_state.get_reward()}")
    print(f"Total cost: {best_state.get_cost()}")
    print(f"Execution time: {elapsed_time:.2f} seconds")
    
    # Save results to file if specified or create default filename
    if args.output_file:
        output_file = args.output_file
        # If output file doesn't start with absolute path or UCT folder, put it in uct-output
        if not os.path.isabs(output_file) and not output_file.startswith('uct-output'):
            # Get the directory where this script is located (UCT folder)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            uct_output_dir = os.path.join(script_dir, 'uct-output')
            output_file = os.path.join(uct_output_dir, os.path.basename(output_file))
    else:
        # Create default filename in uct-output folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        uct_output_dir = os.path.join(script_dir, 'uct-output')
        problem_name = os.path.splitext(os.path.basename(args.problem_file))[0]
        output_file = os.path.join(uct_output_dir, f"{args.algorithm}_{problem_name}_{args.max_iterations}.txt")
    
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(f"# {args.algorithm.upper()} Results\n")
            f.write(f"# Problem: {args.problem_file}\n")
            f.write(f"# Iterations: {args.max_iterations}\n")
            f.write(f"# Exploration constant: {args.exploration_constant}\n")
            if args.algorithm == 'wu-uct':
                f.write(f"# Expansion workers: {args.expansion_workers}\n")
                f.write(f"# Simulation workers: {args.simulation_workers}\n")
            f.write(f"# Execution time: {elapsed_time:.2f}s\n")
            f.write(f"#\n")
            f.write(f"Path= {' '.join(map(str, best_state.get_path()))}\n")
            f.write(f"Reward= {best_state.get_reward()}\n")
            f.write(f"Cost= {best_state.get_cost()}\n")
        
        print(f"Results saved to: {output_file}")
    except Exception as e:
        print(f"ERROR: Failed to save results to file: {e}")


if __name__ == "__main__":
    main()