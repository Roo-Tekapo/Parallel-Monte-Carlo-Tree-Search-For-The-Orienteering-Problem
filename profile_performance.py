"""
Performance profiling script to identify bottlenecks in MCTS implementations.

This script profiles both MCTS Base and UCT Single Thread to show exactly
where time is being spent in each implementation.
"""

import cProfile
import pstats
import io
from pstats import SortKey
import time

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from MCTS.mcts_base import MCTSSingleThread
from UCT.uct_single_thread import UCTSingleThread


def profile_mcts_base(problem, iterations=1000):
    """Profile MCTS Base implementation."""
    print(f"\n{'='*60}")
    print("PROFILING: MCTS Base")
    print(f"{'='*60}")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    start_time = time.time()
    solver = MCTSSingleThread(problem, iterations=iterations)
    best_state = solver.run()
    elapsed_time = time.time() - start_time
    
    profiler.disable()
    
    # Print results
    print(f"\nResults:")
    print(f"  Best reward: {best_state.get_reward()}")
    print(f"  Path length: {len(best_state.get_path())}")
    print(f"  Total time: {elapsed_time:.2f}s")
    print(f"  Time per iteration: {(elapsed_time/iterations)*1000:.2f}ms")
    
    # Print top 20 most time-consuming functions
    print(f"\nTop 20 time consumers:")
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(SortKey.CUMULATIVE)
    ps.print_stats(20)
    print(s.getvalue())
    
    return profiler, best_state, elapsed_time


def profile_uct_single(problem, iterations=1000):
    """Profile UCT Single Thread implementation."""
    print(f"\n{'='*60}")
    print("PROFILING: UCT Single Thread")
    print(f"{'='*60}")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    start_time = time.time()
    solver = UCTSingleThread(problem, iterations=iterations)
    best_state = solver.run()
    elapsed_time = time.time() - start_time
    
    profiler.disable()
    
    # Print results
    print(f"\nResults:")
    print(f"  Best reward: {best_state.get_reward()}")
    print(f"  Path length: {len(best_state.get_path())}")
    print(f"  Total time: {elapsed_time:.2f}s")
    print(f"  Time per iteration: {(elapsed_time/iterations)*1000:.2f}ms")
    
    # Print top 20 most time-consuming functions
    print(f"\nTop 20 time consumers:")
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(SortKey.CUMULATIVE)
    ps.print_stats(20)
    print(s.getvalue())
    
    return profiler, best_state, elapsed_time


def detailed_function_analysis(profiler, name):
    """Print detailed analysis of specific bottleneck functions."""
    print(f"\n{'='*60}")
    print(f"DETAILED ANALYSIS: {name}")
    print(f"{'='*60}")
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(SortKey.CUMULATIVE)
    
    # Focus on specific bottleneck functions
    print("\nget_available_actions:")
    ps.print_stats('get_available_actions')
    
    print("\n_can_reach_end_from:")
    ps.print_stats('_can_reach_end_from')
    
    print("\napply_action:")
    ps.print_stats('apply_action')
    
    print("\nsimulate:")
    ps.print_stats('simulate')
    
    print(s.getvalue())


def count_get_available_actions_calls(problem, iterations=100):
    """Count how many times get_available_actions is called."""
    print(f"\n{'='*60}")
    print("COUNTING get_available_actions CALLS")
    print(f"{'='*60}")
    
    # Monkey patch to count calls
    original_method = OrienteeringState.get_available_actions
    call_count = [0]
    bfs_call_count = [0]
    
    def counting_wrapper(self):
        call_count[0] += 1
        return original_method(self)
    
    def counting_bfs_wrapper(self, node_id, current_cost):
        bfs_call_count[0] += 1
        return original_can_reach(self, node_id, current_cost)
    
    # Apply patches
    original_can_reach = OrienteeringState._can_reach_end_from
    OrienteeringState.get_available_actions = counting_wrapper
    OrienteeringState._can_reach_end_from = counting_bfs_wrapper
    
    # Run MCTS
    solver = MCTSSingleThread(problem, iterations=iterations)
    best_state = solver.run()
    
    # Restore original methods
    OrienteeringState.get_available_actions = original_method
    OrienteeringState._can_reach_end_from = original_can_reach
    
    print(f"\nResults for {iterations} iterations:")
    print(f"  get_available_actions called: {call_count[0]:,} times")
    print(f"  _can_reach_end_from called: {bfs_call_count[0]:,} times")
    print(f"  Calls per iteration: {call_count[0]/iterations:.1f}")
    print(f"  BFS per iteration: {bfs_call_count[0]/iterations:.1f}")
    print(f"  BFS per get_available_actions: {bfs_call_count[0]/max(call_count[0],1):.1f}")
    
    return call_count[0], bfs_call_count[0]


def compare_implementations(problem, iterations=1000):
    """Compare MCTS Base vs UCT Single Thread."""
    print(f"\n{'#'*60}")
    print(f"# PERFORMANCE COMPARISON")
    print(f"# Problem: {problem.num_nodes} nodes, budget: {problem.budget}")
    print(f"# Iterations: {iterations}")
    print(f"{'#'*60}")
    
    # Profile MCTS Base
    mcts_profiler, mcts_state, mcts_time = profile_mcts_base(problem, iterations)
    
    # Profile UCT Single
    uct_profiler, uct_state, uct_time = profile_uct_single(problem, iterations)
    
    # Comparison summary
    print(f"\n{'='*60}")
    print("COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"\n{'Implementation':<20} {'Time (s)':<12} {'Reward':<10} {'Path Length':<12} {'ms/iter':<10}")
    print(f"{'-'*70}")
    print(f"{'MCTS Base':<20} {mcts_time:<12.2f} {mcts_state.get_reward():<10} {len(mcts_state.get_path()):<12} {(mcts_time/iterations)*1000:<10.2f}")
    print(f"{'UCT Single':<20} {uct_time:<12.2f} {uct_state.get_reward():<10} {len(uct_state.get_path()):<12} {(uct_time/iterations)*1000:<10.2f}")
    print(f"{'-'*70}")
    
    slowdown = (uct_time / mcts_time - 1) * 100
    print(f"\nUCT Single Thread is {abs(slowdown):.1f}% {'slower' if slowdown > 0 else 'faster'} than MCTS Base")
    
    # Detailed analysis
    detailed_function_analysis(mcts_profiler, "MCTS Base")
    detailed_function_analysis(uct_profiler, "UCT Single")


if __name__ == "__main__":
    import sys
    
    # Default to a medium-sized problem
    problem_file = "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    iterations = 1000
    
    # Check for command-line arguments
    if len(sys.argv) > 1:
        problem_file = sys.argv[1]
    if len(sys.argv) > 2:
        iterations = int(sys.argv[2])
    
    print(f"Loading problem: {problem_file}")
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)
    
    print(f"Problem size: {problem.num_nodes} nodes")
    print(f"Budget: {budget}")
    print(f"Iterations: {iterations}")
    
    # Count function calls first (with fewer iterations to save time)
    count_get_available_actions_calls(problem, iterations=min(100, iterations))
    
    # Full comparison
    compare_implementations(problem, iterations)
    
    print("\n" + "="*60)
    print("PROFILING COMPLETE")
    print("="*60)
    print("\nKey findings:")
    print("1. Check how much time is spent in _can_reach_end_from")
    print("2. Compare get_available_actions vs actual MCTS logic")
    print("3. Note the small difference between MCTS Base and UCT Single")
    print("\nTo test different problems:")
    print(f"  python profile_performance.py <problem_file> <iterations>")
    print("\nExample:")
    print(f"  python profile_performance.py OP_Benchmark_Set/parallel_friendly_v2/xlarge/xlarge_40x40_r0_42.txt 100")
