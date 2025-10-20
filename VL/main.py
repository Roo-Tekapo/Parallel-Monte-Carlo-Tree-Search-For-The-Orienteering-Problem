"""
Virtual Loss MCTS - Main Entry Point

This script demonstrates the Virtual Loss parallel MCTS algorithm
for solving the Orienteering Problem.

Usage:
    python main.py --problem-file <path> [options]

Example:
    python main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt --workers 4 --iterations 10000
"""

import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Virtual Loss MCTS for Orienteering Problem',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Virtual Loss (VL) vs WU-UCT:
  VL uses a FIXED penalty value that's temporarily applied to nodes.
  WU-UCT uses an INCREMENTAL counter that modifies the UCT formula.
  
  VL Advantages:
    - Simpler implementation (uses standard UCT)
    - More intuitive parameter tuning
    - Direct penalty on node values
    
Virtual Loss Value Guidelines:
  0.5-1.0:  Light coordination (more exploitation)
  1.0-2.0:  Standard coordination (balanced)
  2.0-3.0:  Strong coordination (more exploration separation)
        """
    )
    
    # Required arguments
    parser.add_argument('--problem-file', '-p', required=True,
                       help='Path to orienteering problem file')
    
    # Algorithm parameters
    parser.add_argument('--workers', '-w', type=int, default=4,
                       help='Number of parallel workers (default: 4)')
    parser.add_argument('--iterations', '-i', type=int, default=10000,
                       help='Total number of iterations (default: 10000)')
    parser.add_argument('--time-limit', '-t', type=float, default=None,
                       help='Time limit in seconds (overrides iterations)')
    
    # VL-specific parameters
    parser.add_argument('--vl-value', '-v', type=float, default=1.0,
                       help='Virtual loss penalty value (default: 1.0)')
    parser.add_argument('--exploration', '-e', type=float, default=1.414,
                       help='UCT exploration constant (default: √2 ≈ 1.414)')
    
    # Problem settings
    parser.add_argument('--normalize', action='store_true',
                       help='Enable reward normalization')
    parser.add_argument('--no-normalize', dest='normalize', action='store_false',
                       help='Disable reward normalization')
    parser.set_defaults(normalize=True)
    
    # Output options
    parser.add_argument('--verbose', action='store_true',
                       help='Print detailed progress information')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress most output')
    parser.add_argument('--use-no-end', '-no-end', action='store_true',
                       help='Use no-end orienteering variant (maximize reward without end node requirement)')
    
    return parser.parse_args()


def load_problem(filepath: str, normalize: bool = True, use_no_end: bool = False):
    """
    Load orienteering problem from file.
    
    Args:
        filepath: Path to problem file
        normalize: Whether to enable reward normalization
        use_no_end: Use no-end orienteering variant
        
    Returns:
        OrienteeringProblem instance
    """
    # Set the variant BEFORE importing
    os.environ['VL_USE_NO_END'] = 'true' if use_no_end else 'false'
    
    # Import from adapter (which reads the env var)
    from VL.orienteering_adapter import OrienteeringProblem
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Problem file not found: {filepath}")
    
    nodes, budget = OrienteeringProblem.load_problem(filepath)
    problem = OrienteeringProblem(nodes, budget, normalize_rewards=normalize)
    return problem


def main():
    """Main execution function."""
    args = parse_args()
    
    # Set the variant BEFORE importing VL modules
    os.environ['VL_USE_NO_END'] = 'true' if args.use_no_end else 'false'
    
    # Import VL modules (they will use the adapter which reads the env var)
    from VL.vl_coordinator import VirtualLossMCTS
    from VL.orienteering_adapter import get_variant
    
    variant_name = get_variant()
    
    if not args.quiet:
        print("="*70)
        print("Virtual Loss Parallel MCTS for Orienteering Problem")
        print("="*70)
    
    # Load problem
    try:
        problem = load_problem(args.problem_file, args.normalize, args.use_no_end)
        if not args.quiet:
            print(f"\nProblem: {args.problem_file}")
            print(f"  Nodes: {problem.num_nodes}")
            print(f"  Budget: {problem.budget}")
            print(f"  Variant: {variant_name} Orienteering")
            print(f"  Normalize Rewards: {args.normalize}")
    except Exception as e:
        print(f"Error loading problem: {e}", file=sys.stderr)
        return 1
    
    # Initialize Virtual Loss MCTS
    vl_mcts = VirtualLossMCTS(
        problem=problem,
        num_workers=args.workers,
        exploration_constant=args.exploration,
        virtual_loss_value=args.vl_value
    )
    
    if not args.quiet:
        print(f"\nVirtual Loss MCTS Configuration:")
        print(f"  Workers: {args.workers}")
        print(f"  Iterations: {args.iterations}")
        if args.time_limit:
            print(f"  Time Limit: {args.time_limit}s")
        print(f"  VL Value: {args.vl_value}")
        print(f"  Exploration Constant: {args.exploration}")
        print()
    
    # Run algorithm
    try:
        solution = vl_mcts.run(
            max_iterations=args.iterations,
            max_time=args.time_limit,
            verbose=args.verbose or not args.quiet
        )
        
        if not args.quiet and not args.verbose:
            # Calculate actual reward
            actual_reward = sum(problem.nodes[node_id].score for node_id in solution.path)
            
            print(f"\nFinal Solution:")
            print(f"  Path: {solution.path}")
            
            if problem.normalize_rewards:
                print(f"  Normalized reward: {solution.reward_so_far:.6f}")
                print(f"  Actual reward: {actual_reward}")
            else:
                print(f"  Reward: {solution.reward_so_far:.2f}")
                
            print(f"  Cost: {solution.cost_so_far:.2f} / {problem.budget:.2f}")
            print(f"  Nodes Visited: {len(solution.path)}")
            print(f"  Terminal: {solution.is_terminal()}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\nError during execution: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
