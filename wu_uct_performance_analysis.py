#!/usr/bin/env python3
"""
Performance analysis and optimization suggestions for WU-UCT.
"""

import sys
import os
import time
import cProfile
import pstats
import io
import multiprocessing
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orienteering.orienteering import OrienteeringProblem
from UCT.wu_uct_coordinator import WUUCT
from UCT.uct_single_thread import UCTSingleThread


def profile_wu_uct(problem_file: str, iterations: int = 10000, workers: int = 4) -> Dict:
    """Profile WU-UCT execution and identify bottlenecks."""
    
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget)
    
    # Profile WU-UCT
    print(f"Profiling WU-UCT with {workers} workers, {iterations} iterations...")
    
    pr = cProfile.Profile()
    pr.enable()
    
    start_time = time.time()
    wu_uct = WUUCT(problem, simulation_workers=workers)
    result = wu_uct.run(max_iterations=iterations, verbose=False)
    end_time = time.time()
    
    pr.disable()
    
    # Capture profile stats
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s)
    ps.sort_stats('cumulative')
    ps.print_stats(30)  # Top 30 functions
    
    return {
        'total_time': end_time - start_time,
        'result_reward': result.get_reward(),
        'result_cost': result.get_cost(),
        'profile_output': s.getvalue(),
        'workers': workers,
        'iterations': iterations
    }


def benchmark_scalability():
    """Test how WU-UCT scales with different numbers of workers."""
    
    problem_file = "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    iterations = 20000
    
    if not os.path.exists(problem_file):
        print(f"❌ Problem file not found: {problem_file}")
        return
    
    print("🔍 WU-UCT PERFORMANCE ANALYSIS")
    print("=" * 50)
    
    # Test different worker counts
    worker_counts = [1, 2, 4, 6, 8]
    if multiprocessing.cpu_count() >= 12:
        worker_counts.extend([10, 12])
    
    results = []
    
    for workers in worker_counts:
        try:
            print(f"\n📊 Testing with {workers} workers...")
            result = profile_wu_uct(problem_file, iterations, workers)
            results.append(result)
            
            print(f"   Time: {result['total_time']:.2f}s")
            print(f"   Reward: {result['result_reward']:.0f}")
            print(f"   Efficiency: {iterations/result['total_time']:.0f} iter/sec")
            
        except Exception as e:
            print(f"   ❌ Error with {workers} workers: {e}")
    
    # Analyze results
    print(f"\n📈 SCALABILITY ANALYSIS")
    print("=" * 50)
    
    if len(results) >= 2:
        baseline = results[0]  # Single worker baseline
        
        print(f"{'Workers':<8} {'Time(s)':<8} {'Speedup':<8} {'Efficiency':<12} {'Reward':<8}")
        print("-" * 50)
        
        for result in results:
            speedup = baseline['total_time'] / result['total_time']
            efficiency = speedup / result['workers']
            
            print(f"{result['workers']:<8} {result['total_time']:<8.2f} {speedup:<8.2f} "
                  f"{efficiency:<12.2f} {result['result_reward']:<8.0f}")
    
    # Show detailed profile for medium worker count
    if len(results) >= 3:
        print(f"\n🔍 DETAILED PROFILE ({results[2]['workers']} workers)")
        print("=" * 50)
        print(results[2]['profile_output'])
    
    return results


def analyze_bottlenecks():
    """Identify specific performance bottlenecks in WU-UCT."""
    
    problem_file = "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    
    print("\n🐌 BOTTLENECK ANALYSIS")
    print("=" * 50)
    
    # Compare with single-threaded UCT
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget)
    
    iterations = 10000
    
    # Single-threaded UCT baseline
    print("Testing single-threaded UCT...")
    start_time = time.time()
    uct = UCTSingleThread(problem, iterations)
    uct_result = uct.run()
    uct_time = time.time() - start_time
    
    print(f"UCT: {uct_time:.2f}s, Reward: {uct_result.get_reward():.0f}")
    
    # WU-UCT with different configurations
    configs = [
        {"sim_workers": 1, "exp_workers": 1},
        {"sim_workers": 2, "exp_workers": 1}, 
        {"sim_workers": 4, "exp_workers": 1},
        {"sim_workers": 4, "exp_workers": 2}
    ]
    
    print("\nTesting WU-UCT configurations...")
    for config in configs:
        start_time = time.time()
        wu_uct = WUUCT(problem, 
                      expansion_workers=config["exp_workers"],
                      simulation_workers=config["sim_workers"])
        wu_result = wu_uct.run(max_iterations=iterations, verbose=False)
        wu_time = time.time() - start_time
        
        overhead = (wu_time / uct_time - 1) * 100
        
        print(f"WU-UCT {config['sim_workers']}s/{config['exp_workers']}e: "
              f"{wu_time:.2f}s ({overhead:+.1f}%), Reward: {wu_result.get_reward():.0f}")


def suggest_optimizations():
    """Provide specific optimization recommendations."""
    
    print("\n💡 OPTIMIZATION RECOMMENDATIONS")
    print("=" * 50)
    
    recommendations = [
        {
            "category": "🏗️ Thread Pool Management",
            "suggestions": [
                "Pre-allocate worker threads instead of creating/destroying them",
                "Use thread-local storage for simulation state to reduce copying",
                "Implement work-stealing between simulation workers",
                "Consider using ProcessPoolExecutor for CPU-bound simulations"
            ]
        },
        {
            "category": "🔄 Queue Optimization", 
            "suggestions": [
                "Use lockless queues (like multiprocessing.Queue) for better throughput",
                "Batch work units to reduce queue overhead",
                "Implement priority queues for more promising work units",
                "Pre-allocate work unit objects to avoid garbage collection"
            ]
        },
        {
            "category": "🧮 Simulation Speedup",
            "suggestions": [
                "Cache distance calculations between frequently accessed nodes",
                "Use more efficient random number generation (e.g., numpy.random)",
                "Implement early termination for obviously poor simulations", 
                "Vectorize simulation operations where possible"
            ]
        },
        {
            "category": "🌲 Tree Management",
            "suggestions": [
                "Use more efficient node storage (arrays instead of objects)",
                "Implement node pooling to reduce memory allocation",
                "Cache UCT calculations for frequently accessed nodes",
                "Use bit operations for action availability checks"
            ]
        },
        {
            "category": "🔧 System-Level Optimizations",
            "suggestions": [
                "Pin worker threads to specific CPU cores",
                "Increase process priority for compute-intensive operations",
                "Use memory mapping for large problem instances",
                "Enable compiler optimizations (e.g., Cython, Numba)"
            ]
        }
    ]
    
    for rec in recommendations:
        print(f"\n{rec['category']}")
        print("-" * len(rec['category']))
        for i, suggestion in enumerate(rec['suggestions'], 1):
            print(f"{i}. {suggestion}")
    
    print(f"\n🎯 IMMEDIATE ACTION ITEMS")
    print("-" * 30)
    print("1. Profile with larger iteration counts to identify real bottlenecks")
    print("2. Implement simulation worker pooling with thread reuse") 
    print("3. Add distance caching for the orienteering problem")
    print("4. Consider using Numba JIT compilation for simulation loops")
    print("5. Benchmark against optimized single-threaded implementation")


if __name__ == "__main__":
    print("WU-UCT Performance Analysis")
    print("=" * 60)
    
    # Check if problem files exist
    test_files = [
        "OP_Benchmark_Set/set_64_1/set_64_1_80.txt",
        "OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt"
    ]
    
    available_files = [f for f in test_files if os.path.exists(f)]
    
    if not available_files:
        print("❌ No test files found. Please ensure problem files exist.")
        sys.exit(1)
    
    try:
        # Run scalability benchmark
        results = benchmark_scalability()
        
        # Analyze bottlenecks
        analyze_bottlenecks()
        
        # Provide optimization suggestions
        suggest_optimizations()
        
    except KeyboardInterrupt:
        print("\n⏸️  Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()