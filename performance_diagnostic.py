"""
Performance Diagnostic Script for WU-UCT vs Single-Thread MCTS
Identifies bottlenecks and performance issues in parallel implementation.
"""

import time
import cProfile
import pstats
import io
from contextlib import contextmanager
import threading
import sys

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from MCTS.wu_uct import WUUCTSolver
from MCTS.mcts_single_thread import single_thread_mcts


@contextmanager
def timer(name):
    """Context manager for timing code blocks."""
    start = time.time()
    yield
    end = time.time()
    print(f"{name}: {end - start:.3f} seconds")


class PerformanceDiagnostic:
    """Diagnose performance issues in WU-UCT implementation."""
    
    def __init__(self, problem_file, iterations=1000):
        self.problem_file = problem_file
        self.iterations = iterations
        self.results = {}
        
        # Load problem
        nodes, budget = OrienteeringProblem.load_problem(problem_file)
        self.problem = OrienteeringProblem(nodes, budget)
        print(f"Loaded problem: {len(nodes)} nodes, budget: {budget}")
    
    def test_single_thread_baseline(self):
        """Test single-threaded MCTS as baseline."""
        print("\n" + "="*60)
        print("BASELINE: Single-Thread MCTS")
        print("="*60)
        
        solver = single_thread_mcts(self.problem)
        
        start_time = time.time()
        solver.run(self.iterations)
        end_time = time.time()
        
        elapsed = end_time - start_time
        sims_per_sec = self.iterations / elapsed
        
        print(f"Time: {elapsed:.3f} seconds")
        print(f"Iterations: {self.iterations}")
        print(f"Simulations/sec: {sims_per_sec:.1f}")
        
        self.results['single_thread'] = {
            'time': elapsed,
            'iterations': self.iterations,
            'sims_per_sec': sims_per_sec
        }
        
        return elapsed
    
    def test_wu_uct_parallel(self, num_workers=4):
        """Test WU-UCT parallel implementation."""
        print("\n" + "="*60)
        print(f"WU-UCT Parallel ({num_workers} workers)")
        print("="*60)
        
        solver = WUUCTSolver(
            problem=self.problem,
            iterations=self.iterations,
            num_workers=num_workers,
            exploration_constant=1.414
        )
        
        start_time = time.time()
        best_solution = solver.run()
        end_time = time.time()
        
        elapsed = end_time - start_time
        sims_per_sec = self.iterations / elapsed
        
        print(f"Time: {elapsed:.3f} seconds")
        print(f"Iterations: {self.iterations}")
        print(f"Simulations/sec: {sims_per_sec:.1f}")
        print(f"Best reward: {best_solution.get_reward()}")
        
        self.results[f'wu_uct_{num_workers}'] = {
            'time': elapsed,
            'iterations': self.iterations,
            'sims_per_sec': sims_per_sec,
            'reward': best_solution.get_reward()
        }
        
        return elapsed
    
    def profile_wu_uct(self, num_workers=4):
        """Profile WU-UCT to find hotspots."""
        print("\n" + "="*60)
        print(f"PROFILING: WU-UCT ({num_workers} workers)")
        print("="*60)
        
        solver = WUUCTSolver(
            problem=self.problem,
            iterations=min(self.iterations, 500),  # Use fewer iterations for profiling
            num_workers=num_workers,
            exploration_constant=1.414
        )
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        solver.run()
        
        profiler.disable()
        
        # Print profiling results
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(30)  # Top 30 functions
        
        print("\nTop 30 functions by cumulative time:")
        print(s.getvalue())
        
        return profiler
    
    def test_lock_contention(self, num_workers=4):
        """Test for lock contention issues."""
        print("\n" + "="*60)
        print("LOCK CONTENTION ANALYSIS")
        print("="*60)
        
        solver = WUUCTSolver(
            problem=self.problem,
            iterations=min(self.iterations, 500),
            num_workers=num_workers,
            exploration_constant=1.414
        )
        
        # Instrument the lock to measure contention
        original_lock = solver.global_tree_lock
        lock_waits = [0]
        lock_acquisitions = [0]
        total_wait_time = [0.0]
        
        class InstrumentedLock:
            def __enter__(self):
                lock_acquisitions[0] += 1
                start = time.time()
                result = original_lock.__enter__()
                wait_time = time.time() - start
                if wait_time > 0.0001:  # More than 0.1ms
                    lock_waits[0] += 1
                    total_wait_time[0] += wait_time
                return result
            
            def __exit__(self, *args):
                return original_lock.__exit__(*args)
        
        solver.global_tree_lock = InstrumentedLock()
        
        start_time = time.time()
        solver.run()
        end_time = time.time()
        
        elapsed = end_time - start_time
        
        print(f"Total lock acquisitions: {lock_acquisitions[0]}")
        print(f"Lock contentions (wait > 0.1ms): {lock_waits[0]}")
        print(f"Contention rate: {100 * lock_waits[0] / max(lock_acquisitions[0], 1):.2f}%")
        print(f"Total wait time: {total_wait_time[0]:.3f}s")
        print(f"Wait time overhead: {100 * total_wait_time[0] / elapsed:.2f}%")
        
        self.results['lock_contention'] = {
            'acquisitions': lock_acquisitions[0],
            'contentions': lock_waits[0],
            'contention_rate': 100 * lock_waits[0] / max(lock_acquisitions[0], 1),
            'total_wait_time': total_wait_time[0],
            'wait_overhead_pct': 100 * total_wait_time[0] / elapsed
        }
    
    def test_overhead_breakdown(self, num_workers=4):
        """Break down where time is spent in WU-UCT."""
        print("\n" + "="*60)
        print("OVERHEAD BREAKDOWN")
        print("="*60)
        
        solver = WUUCTSolver(
            problem=self.problem,
            iterations=min(self.iterations, 500),
            num_workers=num_workers,
            exploration_constant=1.414
        )
        
        # Track time in different phases
        selection_time = [0.0]
        expansion_time = [0.0]
        simulation_time = [0.0]
        backprop_time = [0.0]
        lock_time = [0.0]
        
        # Instrument methods
        original_selection = solver.wu_uct_selection
        original_expand = solver.safe_expand
        original_simulate = solver.simulate
        original_backprop = solver.wu_uct_backpropagate
        
        def timed_selection(node, worker_id):
            start = time.time()
            result = original_selection(node, worker_id)
            selection_time[0] += time.time() - start
            return result
        
        def timed_expand(node, task_id):
            start = time.time()
            result = original_expand(node, task_id)
            expansion_time[0] += time.time() - start
            return result
        
        def timed_simulate(state):
            start = time.time()
            result = original_simulate(state)
            simulation_time[0] += time.time() - start
            return result
        
        def timed_backprop(path, reward):
            start = time.time()
            result = original_backprop(path, reward)
            backprop_time[0] += time.time() - start
            return result
        
        solver.wu_uct_selection = timed_selection
        solver.safe_expand = timed_expand
        solver.simulate = timed_simulate
        solver.wu_uct_backpropagate = timed_backprop
        
        start_time = time.time()
        solver.run()
        total_time = time.time() - start_time
        
        print(f"\nTime breakdown:")
        print(f"  Selection:   {selection_time[0]:.3f}s ({100*selection_time[0]/total_time:.1f}%)")
        print(f"  Expansion:   {expansion_time[0]:.3f}s ({100*expansion_time[0]/total_time:.1f}%)")
        print(f"  Simulation:  {simulation_time[0]:.3f}s ({100*simulation_time[0]/total_time:.1f}%)")
        print(f"  Backprop:    {backprop_time[0]:.3f}s ({100*backprop_time[0]/total_time:.1f}%)")
        other_time = total_time - (selection_time[0] + expansion_time[0] + 
                                   simulation_time[0] + backprop_time[0])
        print(f"  Other/Sync:  {other_time:.3f}s ({100*other_time/total_time:.1f}%)")
        print(f"  Total:       {total_time:.3f}s")
        
        self.results['overhead_breakdown'] = {
            'selection': selection_time[0],
            'expansion': expansion_time[0],
            'simulation': simulation_time[0],
            'backprop': backprop_time[0],
            'other': other_time,
            'total': total_time
        }
    
    def compare_speedup(self):
        """Compare speedup across different worker counts."""
        print("\n" + "="*60)
        print("SPEEDUP COMPARISON")
        print("="*60)
        
        baseline = self.test_single_thread_baseline()
        
        for num_workers in [2, 4, 8]:
            wu_time = self.test_wu_uct_parallel(num_workers)
            speedup = baseline / wu_time
            efficiency = 100 * speedup / num_workers
            
            print(f"\n{num_workers} workers:")
            print(f"  Speedup: {speedup:.2f}x")
            print(f"  Parallel efficiency: {efficiency:.1f}%")
            
            if speedup < 1.0:
                print(f"  ⚠️  SLOWER than single-threaded by {1/speedup:.2f}x!")
    
    def run_full_diagnostic(self):
        """Run complete diagnostic suite."""
        print("\n" + "="*60)
        print("WU-UCT PERFORMANCE DIAGNOSTIC")
        print("="*60)
        print(f"Problem: {self.problem_file}")
        print(f"Iterations: {self.iterations}")
        
        # Test baseline
        baseline_time = self.test_single_thread_baseline()
        
        # Test WU-UCT with different worker counts
        wu_time_4 = self.test_wu_uct_parallel(num_workers=4)
        
        # Analyze if there's a problem
        if wu_time_4 > baseline_time:
            print("\n⚠️  WU-UCT is SLOWER than single-threaded!")
            print("Running detailed diagnostics...\n")
            
            # Detailed diagnostics
            self.test_lock_contention(num_workers=4)
            self.test_overhead_breakdown(num_workers=4)
            self.profile_wu_uct(num_workers=4)
        else:
            print("\n✓ WU-UCT is faster than single-threaded")
            speedup = baseline_time / wu_time_4
            print(f"Speedup: {speedup:.2f}x with 4 workers")
        
        # Summary
        print("\n" + "="*60)
        print("DIAGNOSTIC SUMMARY")
        print("="*60)
        for key, value in self.results.items():
            print(f"\n{key}:")
            for k, v in value.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    # Use a small problem for quick diagnostics
    problem_file = "OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt"
    
    # Check if file exists
    import os
    if not os.path.exists(problem_file):
        print(f"Error: Problem file not found: {problem_file}")
        print("Please specify a valid problem file.")
        sys.exit(1)
    
    # Run diagnostics with fewer iterations for quick feedback
    diagnostic = PerformanceDiagnostic(problem_file, iterations=500)
    diagnostic.run_full_diagnostic()
