"""
Test script to verify the backtracking fix for MCTS methods.

This script tests that MCTS algorithms can continue productively exploring
even when they've exhausted the budget but still have iterations remaining.

The backtracking mechanism should prevent getting stuck at terminal/dead-end nodes.
"""

import math
import time
from orienteering.orienteering_traditional import OrienteeringProblem

# Import all MCTS implementations
from MCTS.mcts_base import MCTSSingleThread
from UCT.uct_single_thread import UCTSingleThread
from UCT.wu_uct import run_wu_uct
from VL.vl_coordinator import VirtualLossMCTS


def test_mcts_with_many_iterations(problem_file, iterations=50000):
    """
    Test MCTS implementations with a high number of iterations to ensure
    they don't get stuck when budget is exhausted.
    
    Args:
        problem_file: Path to the problem file
        iterations: Number of iterations to run (high value to test the fix)
    """
    print("="*80)
    print(f"Testing Backtracking Fix with {iterations} iterations")
    print("="*80)
    
    # Load problem
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    
    print(f"\nProblem: {problem_file}")
    print(f"Nodes: {len(nodes)}, Budget: {budget}")
    print(f"\nRunning {iterations} iterations to test backtracking...\n")
    
    results = []
    
    # Test 1: Traditional MCTS with soft end bias
    print("-" * 80)
    print("1. Traditional MCTS with Soft End Bias")
    print("-" * 80)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
    mcts = MCTSSingleThread(
        problem, 
        iterations=iterations,
        exploration_constant=math.sqrt(2),
        soft_end_bias=True,
        bias_decay_factor=5
    )
    
    start = time.time()
    best_state = mcts.run()
    elapsed = time.time() - start
    
    raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
    
    print(f"Time: {elapsed:.2f}s")
    print(f"Path: {best_state.get_path()}")
    print(f"Path length: {len(best_state.get_path())} nodes")
    print(f"Normalized reward: {best_state.get_reward():.6f}")
    print(f"Raw reward: {raw_reward}")
    print(f"Cost: {best_state.get_cost():.2f} / {budget:.2f}")
    print(f"Valid solution: {best_state.is_terminal()}")
    print(f"Iterations/sec: {iterations/elapsed:.2f}")
    
    results.append({
        'name': 'MCTS',
        'reward': best_state.get_reward(),
        'raw_reward': raw_reward,
        'path_length': len(best_state.get_path()),
        'cost': best_state.get_cost(),
        'time': elapsed,
        'valid': best_state.is_terminal()
    })
    
    # Test 2: Single-threaded UCT
    print("\n" + "-" * 80)
    print("2. Single-Threaded UCT")
    print("-" * 80)
    problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
    uct = UCTSingleThread(
        problem,
        iterations=iterations,
        exploration_constant=math.sqrt(2)
    )
    
    start = time.time()
    best_state = uct.run(verbose=False)
    elapsed = time.time() - start
    
    raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
    
    print(f"Time: {elapsed:.2f}s")
    print(f"Path: {best_state.get_path()}")
    print(f"Path length: {len(best_state.get_path())} nodes")
    print(f"Normalized reward: {best_state.get_reward():.6f}")
    print(f"Raw reward: {raw_reward}")
    print(f"Cost: {best_state.get_cost():.2f} / {budget:.2f}")
    print(f"Valid solution: {best_state.is_terminal()}")
    print(f"Iterations/sec: {iterations/elapsed:.2f}")
    
    results.append({
        'name': 'UCT',
        'reward': best_state.get_reward(),
        'raw_reward': raw_reward,
        'path_length': len(best_state.get_path()),
        'cost': best_state.get_cost(),
        'time': elapsed,
        'valid': best_state.is_terminal()
    })
    
    # Test 3: WU-UCT (parallel)
    print("\n" + "-" * 80)
    print("3. WU-UCT (Parallel)")
    print("-" * 80)
    problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
    
    start = time.time()
    best_state = run_wu_uct(
        problem,
        max_iterations=iterations,
        simulation_workers=4,
        exploration_constant=math.sqrt(2),
        verbose=False
    )
    elapsed = time.time() - start
    
    raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
    
    print(f"Time: {elapsed:.2f}s")
    print(f"Path: {best_state.get_path()}")
    print(f"Path length: {len(best_state.get_path())} nodes")
    print(f"Normalized reward: {best_state.get_reward():.6f}")
    print(f"Raw reward: {raw_reward}")
    print(f"Cost: {best_state.get_cost():.2f} / {budget:.2f}")
    print(f"Valid solution: {best_state.is_terminal()}")
    print(f"Iterations/sec: {iterations/elapsed:.2f}")
    
    results.append({
        'name': 'WU-UCT',
        'reward': best_state.get_reward(),
        'raw_reward': raw_reward,
        'path_length': len(best_state.get_path()),
        'cost': best_state.get_cost(),
        'time': elapsed,
        'valid': best_state.is_terminal()
    })
    
    # Test 4: Virtual Loss MCTS (parallel)
    print("\n" + "-" * 80)
    print("4. Virtual Loss MCTS (Parallel)")
    print("-" * 80)
    problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
    vl = VirtualLossMCTS(
        problem,
        num_workers=4,
        exploration_constant=math.sqrt(2),
        virtual_loss_value=1.0
    )
    
    start = time.time()
    best_state = vl.run(max_iterations=iterations, verbose=False)
    elapsed = time.time() - start
    
    raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
    
    print(f"Time: {elapsed:.2f}s")
    print(f"Path: {best_state.get_path()}")
    print(f"Path length: {len(best_state.get_path())} nodes")
    print(f"Normalized reward: {best_state.get_reward():.6f}")
    print(f"Raw reward: {raw_reward}")
    print(f"Cost: {best_state.get_cost():.2f} / {budget:.2f}")
    print(f"Valid solution: {best_state.is_terminal()}")
    print(f"Iterations/sec: {iterations/elapsed:.2f}")
    
    results.append({
        'name': 'VL-MCTS',
        'reward': best_state.get_reward(),
        'raw_reward': raw_reward,
        'path_length': len(best_state.get_path()),
        'cost': best_state.get_cost(),
        'time': elapsed,
        'valid': best_state.is_terminal()
    })
    
    # Print summary comparison
    print("\n" + "="*80)
    print("SUMMARY COMPARISON")
    print("="*80)
    print(f"{'Method':<15} {'Norm Reward':<12} {'Raw Reward':<12} {'Path Len':<10} {'Time(s)':<10} {'Valid':<8} {'Iter/s':<10}")
    print("-"*80)
    
    for result in results:
        print(f"{result['name']:<15} "
              f"{result['reward']:<12.6f} "
              f"{result['raw_reward']:<12.2f} "
              f"{result['path_length']:<10} "
              f"{result['time']:<10.2f} "
              f"{str(result['valid']):<8} "
              f"{iterations/result['time']:<10.2f}")
    
    print("\n" + "="*80)
    print("Test Complete!")
    print("="*80)
    print("\nIf all methods show similar iteration rates and find valid solutions,")
    print("the backtracking fix is working correctly. They should continue exploring")
    print("productively even with high iteration counts.")
    

if __name__ == "__main__":
    # Test with a medium-sized grid problem
    test_problem = "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    
    # Run test with 50,000 iterations to ensure backtracking kicks in
    test_mcts_with_many_iterations(test_problem, iterations=50000)
    
    print("\n" + "="*80)
    print("Testing with a smaller problem and even more iterations...")
    print("="*80)
    
    # Test with smaller problem but more iterations
    test_problem_small = "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    test_mcts_with_many_iterations(test_problem_small, iterations=100000)
