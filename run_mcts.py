#!/usr/bin/env python3
"""
Simple script to run MCTS with different approaches
Usage:
  python3 run_mcts.py [traditional|conservative|soft_bias] [problem_file] [iterations] [decay_factor]
  
  decay_factor (for soft_bias only): Lower values = stronger bias toward end node
    - 1.0-3.0: Very strong bias (conservative)
    - 4.0-6.0: Medium bias (balanced) 
    - 8.0-15.0: Weak bias (more exploration)
"""

import sys
from orienteering.orienteering import OrienteeringProblem
from MCTS.mcts_base import MCTSSingleThread

def run_mcts(approach="traditional", problem_file="OP_Benchmark_Set/sample/sample_30.txt", iterations=1000):
    """Run MCTS with specified approach"""
    
    print(f"Running {approach.upper()} MCTS approach")
    print(f"Problem: {problem_file}")
    print(f"Iterations: {iterations}")
    print("=" * 50)
    
    # Load problem
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    # Remove max_edge_distance constraint for testing
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=None)
    
    print(f"Problem size: {problem.num_nodes} nodes, budget: {budget}")
    
    # Create solver with specified approach
    if approach.lower() == "traditional":
        solver = MCTSSingleThread(problem=problem, iterations=iterations, traditional_mcts=True)
    elif approach.lower() == "conservative":
        solver = MCTSSingleThread(problem=problem, iterations=iterations, traditional_mcts=False)
    elif approach.lower() == "soft_bias":
        # Default decay factor, can be overridden via command line
        decay_factor = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0  # Reduced from 10.0 to 5.0 for stronger bias
        solver = MCTSSingleThread(problem=problem, iterations=iterations, traditional_mcts=True, soft_end_bias=True, bias_decay_factor=decay_factor)
        print(f"Using soft end-node bias with decay factor {decay_factor}")
    else:
        raise ValueError(f"Unknown approach: {approach}. Use 'traditional', 'conservative', or 'soft_bias'")
    
    # Run solver
    import time
    start_time = time.time()
    best_state = solver.run()
    end_time = time.time()
    
    # Print results
    print(f"\n{approach.upper()} MCTS Results:")
    print(f"Path: {best_state.get_path()}")
    print(f"Reward: {best_state.get_reward()}")
    print(f"Cost: {best_state.get_cost():.2f}")
    print(f"Budget: {budget}")
    print(f"Valid solution: {best_state.is_terminal()}")
    print(f"Path length: {len(best_state.get_path())} nodes")
    print(f"Time: {end_time - start_time:.3f}s")
    
    return best_state

if __name__ == "__main__":
    # Parse command line arguments
    approach = sys.argv[1] if len(sys.argv) > 1 else "traditional"
    problem_file = sys.argv[2] if len(sys.argv) > 2 else "OP_Benchmark_Set/sample/sample_30.txt"
    iterations = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    
    if approach not in ["traditional", "conservative", "soft_bias"]:
        print("Error: approach must be 'traditional', 'conservative', or 'soft_bias'")
        print("Usage: python3 run_mcts.py [traditional|conservative|soft_bias] [problem_file] [iterations] [decay_factor]")
        sys.exit(1)
    
    try:
        run_mcts(approach, problem_file, iterations)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)