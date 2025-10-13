#!/usr/bin/env python3
"""
Quick diagnostic test to compare UCT vs WU-UCT performance.
"""

import sys
import os
import time
import subprocess

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_uct_test(problem_file, iterations=1000):
    """Run single-threaded UCT test."""
    print(f"Testing Single-Threaded UCT ({iterations} iterations)...")
    
    cmd = [
        'python3', 'UCT/main.py',
        '--algorithm', 'uct',
        '--problem-file', problem_file,
        '--max-iterations', str(iterations),
        '--max-distance', '1.42',
        '--verbose'
    ]
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    end_time = time.time()
    
    if result.returncode != 0:
        print(f"UCT test failed: {result.stderr}")
        return None
        
    return {
        'time': end_time - start_time,
        'output': result.stdout,
        'reward': extract_reward(result.stdout)
    }

def run_wu_uct_test(problem_file, iterations=1000):
    """Run WU-UCT test."""
    print(f"Testing WU-UCT ({iterations} iterations)...")
    
    cmd = [
        'python3', 'UCT/main.py', 
        '--algorithm', 'wu-uct',
        '--problem-file', problem_file,
        '--max-iterations', str(iterations),
        '--max-distance', '1.42',
        '--simulation-workers', '2',
        '--expansion-workers', '1',
        '--verbose'
    ]
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    end_time = time.time()
    
    if result.returncode != 0:
        print(f"WU-UCT test failed: {result.stderr}")
        return None
        
    return {
        'time': end_time - start_time,
        'output': result.stdout,
        'reward': extract_reward(result.stdout)
    }

def extract_reward(output):
    """Extract reward from output."""
    for line in output.split('\n'):
        if line.startswith('Total reward:'):
            try:
                return float(line.split(':')[1].strip())
            except:
                pass
    return 0.0

def main():
    """Run diagnostic comparison."""
    
    print("WU-UCT PERFORMANCE DIAGNOSTIC")
    print("=" * 50)
    
    # Test problem
    problem_file = "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    
    if not os.path.exists(problem_file):
        print(f"Test problem not found: {problem_file}")
        # Try alternative
        problem_file = "OP_Benchmark_Set/grid_sample/grid_10x10_easy_20.txt"
        if not os.path.exists(problem_file):
            print(f"Alternative problem not found: {problem_file}")
            return
    
    print(f"Using problem: {problem_file}")
    print()
    
    # Run tests
    iterations = 1000
    
    uct_result = run_uct_test(problem_file, iterations)
    print()
    wu_uct_result = run_wu_uct_test(problem_file, iterations)
    
    print("\n" + "=" * 50)
    print("COMPARISON RESULTS")
    print("=" * 50)
    
    if uct_result and wu_uct_result:
        print(f"Single-threaded UCT:")
        print(f"  Time: {uct_result['time']:.2f}s")
        print(f"  Reward: {uct_result['reward']}")
        print(f"  Iterations/sec: {iterations/uct_result['time']:.1f}")
        
        print(f"\nWU-UCT:")
        print(f"  Time: {wu_uct_result['time']:.2f}s") 
        print(f"  Reward: {wu_uct_result['reward']}")
        print(f"  Iterations/sec: {iterations/wu_uct_result['time']:.1f}")
        
        print(f"\nPerformance Ratio:")
        speedup = uct_result['time'] / wu_uct_result['time']
        print(f"  WU-UCT vs UCT time ratio: {wu_uct_result['time']/uct_result['time']:.2f}x")
        
        if speedup > 1.0:
            print(f"  ✓ WU-UCT is {speedup:.2f}x FASTER")
        else:
            print(f"  ✗ WU-UCT is {1/speedup:.2f}x SLOWER")
            
        reward_ratio = wu_uct_result['reward'] / max(uct_result['reward'], 1)
        print(f"  Reward ratio: {reward_ratio:.2f}")
        
        if reward_ratio >= 0.9:
            print(f"  ✓ WU-UCT reward quality is good")
        else:
            print(f"  ⚠ WU-UCT reward quality may be poor")
            
    else:
        print("One or both tests failed - check error messages above")
        if uct_result is None:
            print("UCT test failed")
        if wu_uct_result is None:
            print("WU-UCT test failed")

if __name__ == "__main__":
    main()