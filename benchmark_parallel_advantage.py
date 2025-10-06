"""
Benchmark script to compare WU-UCT vs Single-threaded UCT performance.

This script systematically evaluates both algorithms on parallel-friendly
datasets to identify where WU-UCT excels.

Metrics tracked:
- Solution quality (total reward)
- Wall-clock time
- Speedup factor (single-thread time / parallel time)
- Iterations per second
- Efficiency (speedup / num_workers)
"""

import os
import time
import json
import math
from typing import Dict, List, Tuple
import argparse
from pathlib import Path

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from UCT.uct_single_thread import UCTSingleThread
from UCT.wu_uct import run_wu_uct


class ParallelBenchmark:
    """Benchmark parallel vs single-threaded UCT."""
    
    def __init__(self, output_dir: str = "benchmark_results"):
        """Initialize benchmark."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = []
    
    def run_single_thread(self, problem: OrienteeringProblem, 
                         max_iterations: int,
                         exploration_constant: float = math.sqrt(2)) -> Tuple[OrienteeringState, float, Dict]:
        """Run single-threaded UCT."""
        uct = UCTSingleThread(problem, iterations=max_iterations, 
                            exploration_constant=exploration_constant)
        
        start_time = time.time()
        best_state = uct.run()
        elapsed = time.time() - start_time
        
        stats = {
            'iterations': max_iterations,
            'time': elapsed,
            'iterations_per_sec': max_iterations / elapsed if elapsed > 0 else 0,
            'reward': best_state.get_reward(),
            'path_length': len(best_state.get_path()),
            'cost': best_state.get_cost()
        }
        
        return best_state, elapsed, stats
    
    def run_wu_uct(self, problem: OrienteeringProblem,
                   max_iterations: int,
                   num_workers: int = 4,
                   exploration_constant: float = math.sqrt(2)) -> Tuple[OrienteeringState, float, Dict]:
        """Run parallel WU-UCT."""
        start_time = time.time()
        best_state = run_wu_uct(
            problem,
            max_iterations=max_iterations,
            simulation_workers=num_workers,
            exploration_constant=exploration_constant,
            verbose=False
        )
        elapsed = time.time() - start_time
        
        stats = {
            'iterations': max_iterations,
            'workers': num_workers,
            'time': elapsed,
            'iterations_per_sec': max_iterations / elapsed if elapsed > 0 else 0,
            'reward': best_state.get_reward(),
            'path_length': len(best_state.get_path()),
            'cost': best_state.get_cost()
        }
        
        return best_state, elapsed, stats
    
    def benchmark_problem(self, problem_file: str, 
                         max_iterations: int = 10000,
                         num_workers: int = 4,
                         num_runs: int = 3,
                         max_edge_distance: float = 1.42) -> Dict:
        """Benchmark both algorithms on a single problem."""
        print(f"\n{'='*70}")
        print(f"Benchmarking: {problem_file}")
        print(f"{'='*70}")
        
        # Load problem with specified edge distance constraint
        nodes, budget = OrienteeringProblem.load_problem(problem_file)
        problem = OrienteeringProblem(nodes, budget, max_edge_distance=max_edge_distance)
        
        print(f"Problem: {len(nodes)} nodes, budget={budget:.2f}")
        
        # Run single-threaded multiple times
        print(f"\nRunning Single-threaded UCT ({num_runs} runs)...")
        single_results = []
        for run in range(num_runs):
            state, elapsed, stats = self.run_single_thread(problem, max_iterations)
            single_results.append(stats)
            print(f"  Run {run+1}: Reward={stats['reward']:.2f}, Time={elapsed:.2f}s")
        
        # Run WU-UCT multiple times
        print(f"\nRunning WU-UCT with {num_workers} workers ({num_runs} runs)...")
        parallel_results = []
        for run in range(num_runs):
            state, elapsed, stats = self.run_wu_uct(problem, max_iterations, num_workers)
            parallel_results.append(stats)
            print(f"  Run {run+1}: Reward={stats['reward']:.2f}, Time={elapsed:.2f}s")
        
        # Calculate averages
        avg_single = {
            'reward': sum(r['reward'] for r in single_results) / num_runs,
            'time': sum(r['time'] for r in single_results) / num_runs,
            'iter_per_sec': sum(r['iterations_per_sec'] for r in single_results) / num_runs
        }
        
        avg_parallel = {
            'reward': sum(r['reward'] for r in parallel_results) / num_runs,
            'time': sum(r['time'] for r in parallel_results) / num_runs,
            'iter_per_sec': sum(r['iterations_per_sec'] for r in parallel_results) / num_runs
        }
        
        # Calculate speedup metrics
        speedup = avg_single['time'] / avg_parallel['time'] if avg_parallel['time'] > 0 else 0
        efficiency = (speedup / num_workers) * 100  # Percentage
        reward_improvement = ((avg_parallel['reward'] - avg_single['reward']) / 
                             avg_single['reward'] * 100) if avg_single['reward'] > 0 else 0
        
        result = {
            'problem_file': problem_file,
            'num_nodes': len(nodes),
            'budget': budget,
            'max_iterations': max_iterations,
            'num_workers': num_workers,
            'num_runs': num_runs,
            'single_thread': avg_single,
            'wu_uct': avg_parallel,
            'speedup': speedup,
            'efficiency_percent': efficiency,
            'reward_improvement_percent': reward_improvement
        }
        
        # Print summary
        print(f"\n{'='*70}")
        print("RESULTS SUMMARY")
        print(f"{'='*70}")
        print(f"Single-thread: {avg_single['reward']:.2f} reward in {avg_single['time']:.2f}s")
        print(f"WU-UCT:        {avg_parallel['reward']:.2f} reward in {avg_parallel['time']:.2f}s")
        print(f"Speedup:       {speedup:.2f}x")
        print(f"Efficiency:    {efficiency:.1f}%")
        print(f"Reward Δ:      {reward_improvement:+.1f}%")
        
        if speedup > 1.5:
            print(f"✓ WU-UCT shows STRONG parallel advantage!")
        elif speedup > 1.1:
            print(f"✓ WU-UCT shows moderate parallel advantage")
        else:
            print(f"⚠ WU-UCT shows limited parallel advantage")
        
        self.results.append(result)
        return result
    
    def benchmark_suite(self, problem_dir: str, pattern: str = "*.txt",
                       max_iterations: int = 10000,
                       num_workers: int = 4,
                       num_runs: int = 3,
                       max_problems: int = None):
        """Benchmark all problems in a directory."""
        problem_files = sorted(Path(problem_dir).glob(pattern))
        
        if max_problems:
            problem_files = problem_files[:max_problems]
        
        print(f"\n{'#'*70}")
        print(f"BENCHMARK SUITE: {problem_dir}")
        print(f"{'#'*70}")
        print(f"Found {len(problem_files)} problems")
        print(f"Iterations per run: {max_iterations}")
        print(f"Workers: {num_workers}")
        print(f"Runs per problem: {num_runs}")
        
        for problem_file in problem_files:
            try:
                self.benchmark_problem(
                    str(problem_file),
                    max_iterations=max_iterations,
                    num_workers=num_workers,
                    num_runs=num_runs
                )
            except Exception as e:
                print(f"Error on {problem_file}: {e}")
                continue
        
        # Save results
        self.save_results()
        self.print_summary()
    
    def save_results(self):
        """Save benchmark results to JSON."""
        output_file = os.path.join(self.output_dir, "benchmark_results.json")
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    
    def print_summary(self):
        """Print overall benchmark summary."""
        if not self.results:
            return
        
        print(f"\n{'#'*70}")
        print("OVERALL BENCHMARK SUMMARY")
        print(f"{'#'*70}")
        
        avg_speedup = sum(r['speedup'] for r in self.results) / len(self.results)
        avg_efficiency = sum(r['efficiency_percent'] for r in self.results) / len(self.results)
        avg_reward_improvement = sum(r['reward_improvement_percent'] for r in self.results) / len(self.results)
        
        strong_advantage = sum(1 for r in self.results if r['speedup'] > 1.5)
        moderate_advantage = sum(1 for r in self.results if 1.1 < r['speedup'] <= 1.5)
        weak_advantage = sum(1 for r in self.results if r['speedup'] <= 1.1)
        
        print(f"\nTotal problems tested: {len(self.results)}")
        print(f"\nAverage speedup:       {avg_speedup:.2f}x")
        print(f"Average efficiency:    {avg_efficiency:.1f}%")
        print(f"Average reward Δ:      {avg_reward_improvement:+.1f}%")
        
        print(f"\nParallel Advantage Distribution:")
        print(f"  Strong (>1.5x):    {strong_advantage} problems ({strong_advantage/len(self.results)*100:.1f}%)")
        print(f"  Moderate (1.1-1.5x): {moderate_advantage} problems ({moderate_advantage/len(self.results)*100:.1f}%)")
        print(f"  Weak (<1.1x):      {weak_advantage} problems ({weak_advantage/len(self.results)*100:.1f}%)")
        
        # Find best cases
        best_speedup = max(self.results, key=lambda r: r['speedup'])
        best_reward = max(self.results, key=lambda r: r['reward_improvement_percent'])
        
        print(f"\nBest Speedup: {best_speedup['speedup']:.2f}x")
        print(f"  Problem: {os.path.basename(best_speedup['problem_file'])}")
        print(f"  Nodes: {best_speedup['num_nodes']}")
        
        print(f"\nBest Reward Improvement: {best_reward['reward_improvement_percent']:+.1f}%")
        print(f"  Problem: {os.path.basename(best_reward['problem_file'])}")
        print(f"  Nodes: {best_reward['num_nodes']}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark WU-UCT parallel advantage")
    parser.add_argument("--problem-dir", type=str, 
                       default="OP_Benchmark_Set/parallel_friendly/dense",
                       help="Directory containing problem files")
    parser.add_argument("--pattern", type=str, default="*.txt",
                       help="File pattern to match")
    parser.add_argument("--iterations", type=int, default=10000,
                       help="Iterations per run")
    parser.add_argument("--workers", type=int, default=4,
                       help="Number of simulation workers for WU-UCT")
    parser.add_argument("--runs", type=int, default=3,
                       help="Number of runs per problem")
    parser.add_argument("--max-problems", type=int, default=None,
                       help="Maximum number of problems to test")
    parser.add_argument("--output-dir", type=str, default="benchmark_results",
                       help="Output directory for results")
    
    args = parser.parse_args()
    
    benchmark = ParallelBenchmark(output_dir=args.output_dir)
    
    if os.path.isfile(args.problem_dir):
        # Single problem
        benchmark.benchmark_problem(
            args.problem_dir,
            max_iterations=args.iterations,
            num_workers=args.workers,
            num_runs=args.runs
        )
        benchmark.save_results()
    else:
        # Suite of problems
        benchmark.benchmark_suite(
            args.problem_dir,
            pattern=args.pattern,
            max_iterations=args.iterations,
            num_workers=args.workers,
            num_runs=args.runs,
            max_problems=args.max_problems
        )


if __name__ == "__main__":
    main()
