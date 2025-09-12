"""
Demo script for WU-UCT implementation.
Shows how to use the WU-UCT worker manager to solve orienteering problems.
"""
import math
from orienteering.orienteering import OrienteeringProblem
from MCTS.wu_worker_manager import WUUCTWorkerManager


def main():
    """Main demo function."""
    print("WU-UCT Orienteering Problem Solver Demo")
    print("=" * 50)
    
    # Load a test problem
    try:
        nodes, budget = OrienteeringProblem.load_problem(
            "OP_Benchmark_Set/sample/sample_6_small.txt"
        )
        print(f"Loaded problem with {len(nodes)} nodes and budget {budget}")
    except Exception as e:
        print(f"Failed to load problem: {e}")
        return
    
    # Create problem instance
    problem = OrienteeringProblem(nodes, budget)
    
    # Configure WU-UCT parameters
    config = {
        'max_steps': 1000,          # Number of MCTS simulations
        'expansion_workers': 2,      # Number of expansion worker threads
        'simulation_workers': 4,     # Number of simulation worker threads
        'exploration_constant': math.sqrt(2),  # UCT exploration parameter
        'simulation_strategy': 'random'  # Simulation strategy
    }
    
    print(f"WU-UCT Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    print()
    
    # Create and run WU-UCT solver
    try:
        manager = WUUCTWorkerManager(problem, **config)
        
        print("Starting WU-UCT solve...")
        best_solution = manager.solve()
        
        # Display results
        print("\nResults:")
        print("=" * 30)
        print(f"Best path: {best_solution.get_path()}")
        print(f"Total reward: {best_solution.get_reward()}")
        print(f"Total cost: {best_solution.get_cost()}")
        print(f"Budget used: {best_solution.get_cost()}/{budget}")
        
        # Display statistics
        stats = manager.get_statistics()
        print(f"\nStatistics:")
        print(f"Total expansions: {stats['wu_uct_stats']['total_expansions']}")
        print(f"Total simulations: {stats['wu_uct_stats']['total_simulations']}")
        print(f"Total time: {stats['wu_uct_stats']['total_time']:.2f} seconds")
        
        print(f"\nWorker Pool Statistics:")
        expansion_stats = stats['coordinator_stats']['expansion_pool']
        simulation_stats = stats['coordinator_stats']['simulation_pool']
        
        print(f"Expansion workers: {expansion_stats['total_tasks_completed']} tasks, "
              f"{expansion_stats['average_task_time']:.4f}s avg")
        print(f"Simulation workers: {simulation_stats['total_tasks_completed']} tasks, "
              f"{simulation_stats['average_task_time']:.4f}s avg")
        
    except Exception as e:
        print(f"Error during WU-UCT solve: {e}")
        import traceback
        traceback.print_exc()


def compare_with_single_threaded():
    """Compare WU-UCT with single-threaded MCTS."""
    print("\nComparison with Single-Threaded MCTS")
    print("=" * 50)
    
    try:
        from MCTS.mcts_single_thread import MCTSSingleThread
        
        # Load problem
        nodes, budget = OrienteeringProblem.load_problem(
            "OP_Benchmark_Set/sample/sample_6_small.txt"
        )
        problem = OrienteeringProblem(nodes, budget)
        
        # Run single-threaded MCTS
        print("Running single-threaded MCTS...")
        import time
        
        start_time = time.time()
        single_solver = MCTSSingleThread(problem, iterations=1000)
        single_result = single_solver.run()
        single_time = time.time() - start_time
        
        print(f"Single-threaded result: {single_result.get_reward()} (time: {single_time:.2f}s)")
        
        # Run WU-UCT
        print("Running WU-UCT...")
        start_time = time.time()
        wu_manager = WUUCTWorkerManager(
            problem, 
            max_steps=1000, 
            expansion_workers=2, 
            simulation_workers=4
        )
        wu_result = wu_manager.solve()
        wu_time = time.time() - start_time
        
        print(f"WU-UCT result: {wu_result.get_reward()} (time: {wu_time:.2f}s)")
        print(f"Speedup: {single_time / wu_time:.2f}x")
        
    except ImportError as e:
        print(f"Cannot compare - missing single-threaded implementation: {e}")
    except Exception as e:
        print(f"Comparison failed: {e}")


if __name__ == "__main__":
    main()
    
    # Optionally run comparison
    try:
        compare_with_single_threaded()
    except Exception as e:
        print(f"Comparison skipped: {e}")
