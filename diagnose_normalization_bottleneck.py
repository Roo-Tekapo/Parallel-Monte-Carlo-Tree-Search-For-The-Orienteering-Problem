"""
Diagnostic script to identify normalization performance bottlenecks.

Profiles individual operations to find where slowdown occurs:
- get_normalized_score() calls
- State creation overhead
- Reward calculation overhead
- UCT selection with normalized vs raw scores
"""

import time
import cProfile
import pstats
from io import StringIO
from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from MCTS.mcts_base import MCTSSingleThread


def profile_operation(func, *args, **kwargs):
    """Profile a single operation and return execution time."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


def test_state_creation_overhead(problem, num_operations=10000):
    """Test overhead of creating states with normalization."""
    print(f"\n{'='*60}")
    print("Testing State Creation Overhead")
    print(f"{'='*60}")
    
    # Test state creation
    start = time.perf_counter()
    for _ in range(num_operations):
        state = OrienteeringState(problem)
    elapsed = time.perf_counter() - start
    
    print(f"Created {num_operations} states in {elapsed:.4f}s")
    print(f"Time per state: {elapsed/num_operations*1e6:.2f} µs")
    print(f"Operations/sec: {num_operations/elapsed:.0f}")


def test_score_access_overhead(problem, num_operations=100000):
    """Test overhead of get_normalized_score() vs direct access."""
    print(f"\n{'='*60}")
    print("Testing Score Access Overhead")
    print(f"{'='*60}")
    
    node_ids = list(range(min(len(problem.nodes), 100)))
    
    # Test direct access (if normalization is off)
    if not problem.normalize_rewards:
        start = time.perf_counter()
        for _ in range(num_operations):
            for node_id in node_ids:
                score = problem.nodes[node_id].score
        elapsed_direct = time.perf_counter() - start
        print(f"Direct access: {elapsed_direct:.4f}s for {num_operations*len(node_ids)} accesses")
        print(f"  Time per access: {elapsed_direct/(num_operations*len(node_ids))*1e9:.2f} ns")
    
    # Test normalized access
    start = time.perf_counter()
    for _ in range(num_operations):
        for node_id in node_ids:
            score = problem.get_normalized_score(node_id)
    elapsed_norm = time.perf_counter() - start
    print(f"Normalized access: {elapsed_norm:.4f}s for {num_operations*len(node_ids)} accesses")
    print(f"  Time per access: {elapsed_norm/(num_operations*len(node_ids))*1e9:.2f} ns")
    
    if not problem.normalize_rewards:
        overhead = (elapsed_norm - elapsed_direct) / elapsed_direct * 100
        print(f"  Overhead: {overhead:.1f}%")


def test_apply_action_overhead(problem, num_operations=10000):
    """Test overhead in apply_action with normalization."""
    print(f"\n{'='*60}")
    print("Testing apply_action Overhead")
    print(f"{'='*60}")
    
    state = OrienteeringState(problem)
    actions = state.get_available_actions(traditional_mcts=False)
    
    if not actions:
        print("No actions available, skipping test")
        return
    
    action = actions[0]
    
    start = time.perf_counter()
    for _ in range(num_operations):
        try:
            new_state = state.apply_action(action, traditional_mcts=False)
        except:
            break
    elapsed = time.perf_counter() - start
    
    print(f"Applied action {num_operations} times in {elapsed:.4f}s")
    print(f"Time per action: {elapsed/num_operations*1e6:.2f} µs")


def test_simulation_overhead(problem, num_simulations=1000):
    """Test simulation performance with/without normalization."""
    print(f"\n{'='*60}")
    print("Testing Simulation Performance")
    print(f"{'='*60}")
    
    solver = MCTSSingleThread(problem, iterations=1)
    state = OrienteeringState(problem)
    
    start = time.perf_counter()
    for _ in range(num_simulations):
        reward = solver.simulate(state)
    elapsed = time.perf_counter() - start
    
    print(f"Ran {num_simulations} simulations in {elapsed:.4f}s")
    print(f"Time per simulation: {elapsed/num_simulations*1e3:.2f} ms")
    print(f"Simulations/sec: {num_simulations/elapsed:.0f}")


def profile_full_mcts_run(problem, iterations=1000):
    """Profile a full MCTS run to identify hotspots."""
    print(f"\n{'='*60}")
    print(f"Profiling Full MCTS Run ({iterations} iterations)")
    print(f"{'='*60}")
    
    solver = MCTSSingleThread(problem, iterations=iterations)
    
    # Profile the run
    profiler = cProfile.Profile()
    profiler.enable()
    
    start = time.perf_counter()
    best_state = solver.run()
    elapsed = time.perf_counter() - start
    
    profiler.disable()
    
    print(f"\nRun completed in {elapsed:.4f}s")
    print(f"Iterations/sec: {iterations/elapsed:.0f}")
    
    # Print top time-consuming functions
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # Top 20 functions
    
    print("\nTop 20 time-consuming functions:")
    print(s.getvalue())


def run_diagnostics(problem_file):
    """Run all diagnostic tests."""
    print(f"\n{'#'*60}")
    print(f"DIAGNOSTIC: {problem_file}")
    print(f"{'#'*60}")
    
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    
    print(f"\nProblem Stats:")
    print(f"  Nodes: {len(nodes)}")
    print(f"  Budget: {budget}")
    print(f"  Total score: {sum(n.score for n in nodes)}")
    print(f"  Max score: {max(n.score for n in nodes)}")
    
    # Test with normalization OFF
    print(f"\n\n{'*'*60}")
    print("TESTING WITHOUT NORMALIZATION")
    print(f"{'*'*60}")
    
    problem_no_norm = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, normalize_rewards=False)
    
    test_state_creation_overhead(problem_no_norm, num_operations=10000)
    test_score_access_overhead(problem_no_norm, num_operations=100000)
    test_apply_action_overhead(problem_no_norm, num_operations=10000)
    test_simulation_overhead(problem_no_norm, num_simulations=1000)
    profile_full_mcts_run(problem_no_norm, iterations=1000)
    
    # Test with normalization ON
    print(f"\n\n{'*'*60}")
    print("TESTING WITH NORMALIZATION")
    print(f"{'*'*60}")
    
    problem_norm = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
    
    print(f"\nNormalization parameters:")
    print(f"  Scale: {problem_norm.reward_scale}")
    print(f"  Offset: {problem_norm.reward_offset}")
    
    test_state_creation_overhead(problem_norm, num_operations=10000)
    test_score_access_overhead(problem_norm, num_operations=100000)
    test_apply_action_overhead(problem_norm, num_operations=10000)
    test_simulation_overhead(problem_norm, num_simulations=1000)
    profile_full_mcts_run(problem_norm, iterations=1000)
    
    # Compare
    print(f"\n\n{'='*60}")
    print("COMPARISON SUMMARY")
    print(f"{'='*60}")
    print("\nThe profiler output above shows where time is spent.")
    print("Look for functions called frequently with normalization enabled:")
    print("  - get_normalized_score()")
    print("  - OrienteeringState.__init__()")
    print("  - apply_action()")
    print("\nIf these show significant time, normalization may be the bottleneck.")


if __name__ == "__main__":
    problem_file = "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    run_diagnostics(problem_file)
    
    print("\n\n" + "="*60)
    print("Diagnostics complete!")
    print("="*60)
