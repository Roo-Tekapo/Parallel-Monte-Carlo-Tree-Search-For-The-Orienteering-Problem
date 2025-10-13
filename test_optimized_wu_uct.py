"""
Test script to benchmark OPTIMIZED WU-UCT vs ORIGINAL WU-UCT

This script tests the optimized expansion worker on multiple benchmark problems:
1. set_64_1_80.txt - Small problem
2. grid_10x10_long_50.txt - Grid problem
3. Grid patterns - Various grid problems

Measures:
- Throughput (simulations/second)
- Solution quality
- Scalability across worker counts
"""

import time
import math
from typing import Dict, List
from orienteering.orienteering import OrienteeringProblem, OrienteeringState

# Import original WU-UCT
from UCT.wu_uct_coordinator import WUUCT

# Import optimized components
from UCT.expansion_worker_optimized import OptimizedWUUCTExpansionWorker
from UCT.simulation_worker import SimulationWorkerPool
from UCT.work_units import WorkUnit, SimulationResult
import queue


class OptimizedWUUCT:
    """
    Optimized WU-UCT coordinator using the optimized expansion worker.
    
    This is a modified version of WUUCT that uses OptimizedWUUCTExpansionWorker
    instead of the original WUUCTExpansionWorker.
    """
    
    def __init__(self, problem: OrienteeringProblem, 
                 expansion_workers: int = 1,
                 simulation_workers: int = 4,
                 exploration_constant: float = math.sqrt(2),
                 max_distance: float = None):
        self.problem = problem
        self.expansion_workers_count = expansion_workers
        self.simulation_workers_count = simulation_workers
        self.exploration_constant = exploration_constant
        self.max_distance = max_distance
        
        self.expansion_workers = []
        self.simulation_worker_pool = SimulationWorkerPool(simulation_workers)
        self.running = False
    
    def run(self, max_iterations: int, max_time: float = None, verbose: bool = False) -> OrienteeringState:
        """Run the optimized WU-UCT algorithm."""
        self.running = True
        start_time = time.time()
        
        # Create shared queues
        shared_work_queue = queue.Queue()
        shared_result_queue = queue.Queue()
        
        iterations_per_worker = None if max_time else max_iterations // self.expansion_workers_count
        
        # Create optimized expansion workers
        for i in range(self.expansion_workers_count):
            worker = OptimizedWUUCTExpansionWorker(
                self.problem,
                worker_id=i,
                exploration_constant=self.exploration_constant,
                max_distance=self.max_distance,
                work_queue=shared_work_queue,
                result_queue=shared_result_queue,
                max_iterations=iterations_per_worker,
                max_time=max_time,
                batch_size=10  # Optimized batching
            )
            self.expansion_workers.append(worker)
            worker.start()
        
        # Start simulation workers
        self.simulation_worker_pool.start_workers(shared_work_queue, shared_result_queue)
        
        try:
            if verbose:
                print(f"Starting OPTIMIZED WU-UCT with {self.expansion_workers_count} expansion workers "
                      f"and {self.simulation_workers_count} simulation workers")
            
            # Monitor progress
            last_iteration = 0
            while self.running and any(worker.is_alive() for worker in self.expansion_workers):
                if max_time and (time.time() - start_time) >= max_time:
                    if verbose:
                        print(f"Time limit of {max_time}s reached")
                    break
                
                time.sleep(1)
                
                current_iteration = self._count_completed_iterations()
                if verbose and current_iteration > last_iteration and current_iteration % 10000 == 0:
                    elapsed = time.time() - start_time
                    print(f"Iteration {current_iteration}, Time: {elapsed:.1f}s, "
                          f"Throughput: {current_iteration/elapsed:.0f} sims/sec")
                    last_iteration = current_iteration
            
            # Wait for workers to complete
            for worker in self.expansion_workers:
                worker.join(timeout=1.0)
            
            final_iteration = self._count_completed_iterations()
            
            if verbose:
                elapsed = time.time() - start_time
                print(f"\nOptimized WU-UCT completed: {final_iteration} iterations in {elapsed:.1f}s")
                print(f"Throughput: {final_iteration/elapsed:.0f} sims/sec")
        
        finally:
            self._cleanup_workers()
        
        # Get best solution
        best_state = None
        if self.expansion_workers:
            best_state = self.expansion_workers[0].get_best_path()
        
        if best_state is None:
            return OrienteeringState(self.problem)
        
        return best_state
    
    def _count_completed_iterations(self) -> int:
        """Count total completed iterations."""
        if not self.expansion_workers:
            return 0
        stats = self.expansion_workers[0].get_statistics()
        return stats.get('root_visits', 0)
    
    def _cleanup_workers(self):
        """Clean up all workers."""
        self.running = False
        
        for worker in self.expansion_workers:
            worker.stop()
        
        for worker in self.expansion_workers:
            if worker.is_alive():
                worker.join(timeout=2.0)
        
        self.simulation_worker_pool.stop_workers(timeout=2.0)
    
    def get_statistics(self) -> Dict:
        """Get statistics from the search."""
        if not self.expansion_workers:
            return {'nodes': 0, 'root_visits': 0}
        return self.expansion_workers[0].get_statistics()


class BenchmarkRunner:
    """Run benchmarks comparing original vs optimized WU-UCT."""
    
    def __init__(self):
        self.results = {}
    
    def test_problem(self, problem_file: str, iterations: int = 10000, 
                    worker_counts: List[int] = [1, 2, 4, 8]):
        """Test a single problem with both implementations."""
        print(f"\n{'='*80}")
        print(f"Testing: {problem_file}")
        print(f"{'='*80}")
        
        # Load problem
        try:
            nodes, budget = OrienteeringProblem.load_problem(problem_file)
            problem = OrienteeringProblem(nodes, budget)
            print(f"Loaded: {len(nodes)} nodes, budget: {budget}")
        except Exception as e:
            print(f"Error loading problem: {e}")
            return
        
        problem_results = {}
        
        for num_workers in worker_counts:
            print(f"\n{'-'*60}")
            print(f"Testing with {num_workers} workers")
            print(f"{'-'*60}")
            
            # Test ORIGINAL WU-UCT
            print(f"\n[1/2] Testing ORIGINAL WU-UCT...")
            original_result = self._test_original(problem, iterations, num_workers)
            
            # Test OPTIMIZED WU-UCT
            print(f"\n[2/2] Testing OPTIMIZED WU-UCT...")
            optimized_result = self._test_optimized(problem, iterations, num_workers)
            
            # Compare
            self._print_comparison(original_result, optimized_result, num_workers)
            
            problem_results[num_workers] = {
                'original': original_result,
                'optimized': optimized_result
            }
        
        self.results[problem_file] = problem_results
        self._print_problem_summary(problem_file, problem_results)
    
    def _test_original(self, problem: OrienteeringProblem, iterations: int, 
                      num_workers: int) -> Dict:
        """Test original WU-UCT implementation."""
        start_time = time.time()
        
        try:
            solver = WUUCT(
                problem=problem,
                expansion_workers=1,
                simulation_workers=num_workers,
                exploration_constant=math.sqrt(2)
            )
            
            best_solution = solver.run(max_iterations=iterations, verbose=False)
            
            elapsed = time.time() - start_time
            stats = solver.get_statistics()
            actual_iterations = stats.get('root_visits', iterations)
            
            return {
                'name': 'Original WU-UCT',
                'time': elapsed,
                'iterations': actual_iterations,
                'throughput': actual_iterations / elapsed if elapsed > 0 else 0,
                'reward': best_solution.get_reward(),
                'cost': best_solution.get_cost(),
                'feasible': best_solution.get_cost() <= problem.budget,
                'nodes': stats.get('nodes', 0)
            }
        except Exception as e:
            print(f"Error in original WU-UCT: {e}")
            import traceback
            traceback.print_exc()
            return {
                'name': 'Original WU-UCT',
                'time': 0,
                'iterations': 0,
                'throughput': 0,
                'reward': 0,
                'cost': 0,
                'feasible': False,
                'nodes': 0,
                'error': str(e)
            }
    
    def _test_optimized(self, problem: OrienteeringProblem, iterations: int, 
                       num_workers: int) -> Dict:
        """Test optimized WU-UCT implementation."""
        start_time = time.time()
        
        try:
            solver = OptimizedWUUCT(
                problem=problem,
                expansion_workers=1,
                simulation_workers=num_workers,
                exploration_constant=math.sqrt(2)
            )
            
            best_solution = solver.run(max_iterations=iterations, verbose=False)
            
            elapsed = time.time() - start_time
            stats = solver.get_statistics()
            actual_iterations = stats.get('root_visits', iterations)
            
            return {
                'name': 'Optimized WU-UCT',
                'time': elapsed,
                'iterations': actual_iterations,
                'throughput': actual_iterations / elapsed if elapsed > 0 else 0,
                'reward': best_solution.get_reward(),
                'cost': best_solution.get_cost(),
                'feasible': best_solution.get_cost() <= problem.budget,
                'nodes': stats.get('nodes', 0)
            }
        except Exception as e:
            print(f"Error in optimized WU-UCT: {e}")
            import traceback
            traceback.print_exc()
            return {
                'name': 'Optimized WU-UCT',
                'time': 0,
                'iterations': 0,
                'throughput': 0,
                'reward': 0,
                'cost': 0,
                'feasible': False,
                'nodes': 0,
                'error': str(e)
            }
    
    def _print_comparison(self, original: Dict, optimized: Dict, workers: int):
        """Print comparison between original and optimized."""
        print(f"\n{'─'*60}")
        print(f"COMPARISON: {workers} workers")
        print(f"{'─'*60}")
        
        if 'error' in original or 'error' in optimized:
            print("⚠ Error during testing, skipping comparison")
            return
        
        # Time
        time_improvement = ((original['time'] - optimized['time']) / original['time'] * 100) if original['time'] > 0 else 0
        print(f"Time:")
        print(f"  Original:  {original['time']:.2f}s")
        print(f"  Optimized: {optimized['time']:.2f}s ({time_improvement:+.1f}% improvement)")
        
        # Throughput
        throughput_improvement = ((optimized['throughput'] - original['throughput']) / original['throughput'] * 100) if original['throughput'] > 0 else 0
        speedup = optimized['throughput'] / original['throughput'] if original['throughput'] > 0 else 0
        print(f"\nThroughput:")
        print(f"  Original:  {original['throughput']:,.0f} sims/sec")
        print(f"  Optimized: {optimized['throughput']:,.0f} sims/sec ({throughput_improvement:+.1f}% improvement)")
        print(f"  Speedup:   {speedup:.2f}x")
        
        # Solution quality
        quality_diff = optimized['reward'] - original['reward']
        print(f"\nSolution Quality:")
        print(f"  Original:  {original['reward']:.1f}")
        print(f"  Optimized: {optimized['reward']:.1f} ({quality_diff:+.1f})")
        
        # Winner
        if speedup >= 1.5:
            print(f"\n✓ OPTIMIZED is {speedup:.1f}x FASTER")
        elif speedup >= 1.1:
            print(f"\n✓ Optimized is moderately faster ({speedup:.2f}x)")
        elif speedup >= 0.9:
            print(f"\n≈ Performance is similar ({speedup:.2f}x)")
        else:
            print(f"\n✗ Original is faster (optimized {speedup:.2f}x)")
    
    def _print_problem_summary(self, problem_file: str, results: Dict):
        """Print summary for a problem across all worker counts."""
        print(f"\n{'='*80}")
        print(f"SUMMARY: {problem_file}")
        print(f"{'='*80}")
        
        print(f"\n{'Workers':<10} {'Original':<20} {'Optimized':<20} {'Speedup':<15}")
        print(f"{'-'*65}")
        
        for workers, result in sorted(results.items()):
            orig = result['original']
            opt = result['optimized']
            
            if 'error' not in orig and 'error' not in opt:
                speedup = opt['throughput'] / orig['throughput'] if orig['throughput'] > 0 else 0
                print(f"{workers:<10} {orig['throughput']:>8,.0f} sims/sec   "
                      f"{opt['throughput']:>8,.0f} sims/sec   {speedup:>6.2f}x")
    
    def print_final_summary(self):
        """Print final summary across all problems."""
        print(f"\n{'#'*80}")
        print(f"# FINAL SUMMARY - Original vs Optimized WU-UCT")
        print(f"{'#'*80}\n")
        
        for problem_file, problem_results in self.results.items():
            print(f"\n{problem_file}:")
            
            total_speedup = 0
            count = 0
            
            for workers, result in sorted(problem_results.items()):
                orig = result['original']
                opt = result['optimized']
                
                if 'error' not in orig and 'error' not in opt and orig['throughput'] > 0:
                    speedup = opt['throughput'] / orig['throughput']
                    total_speedup += speedup
                    count += 1
                    print(f"  {workers}w: {speedup:.2f}x speedup ({orig['throughput']:,.0f} → {opt['throughput']:,.0f} sims/sec)")
            
            if count > 0:
                avg_speedup = total_speedup / count
                print(f"  Average speedup: {avg_speedup:.2f}x")
        
        print(f"\n{'#'*80}\n")


def main():
    """Run the benchmark suite."""
    print("="*80)
    print("BENCHMARK: Original WU-UCT vs Optimized WU-UCT")
    print("="*80)
    
    runner = BenchmarkRunner()
    
    # Test problems
    problems = [
        ("OP_Benchmark_Set/set_64_1/set_64_1_80.txt", 10000),
        ("OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt", 10000),
        ("OP_Benchmark_Set/grid_patterns/grid_10x10_r0_01.txt", 10000),
    ]
    
    # Worker counts to test
    worker_counts = [1, 2, 4, 8]
    
    # Run tests
    for problem_file, iterations in problems:
        runner.test_problem(problem_file, iterations, worker_counts)
    
    # Print final summary
    runner.print_final_summary()
    
    print("\nBenchmark complete!")
    print("Results saved to: (results shown above)")


if __name__ == "__main__":
    main()
