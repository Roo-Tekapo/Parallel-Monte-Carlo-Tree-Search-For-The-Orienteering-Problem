#!/usr/bin/env python3
"""
Simple comparison of UCT vs WU-UCT performance on the same problem.
"""

import time
import subprocess
import sys

def run_algorithm(algorithm, problem_file, max_time=2.0):
    """Run algorithm and parse results."""
    print(f"\n=== Running {algorithm.upper()} ===")
    
    if algorithm == "uct":
        cmd = [
            "python3", "UCT/main.py", 
            "--algorithm", "uct",
            "--problem-file", problem_file,
            "--max-time", str(max_time),
            "--max-distance", "1.42"
        ]
    else:  # wu-uct
        cmd = [
            "python3", "UCT/main.py", 
            "--algorithm", "wu-uct",
            "--problem-file", problem_file,
            "--max-time", str(max_time),
            "--max-distance", "1.42",
            "--expansion-workers", "1",
            "--simulation-workers", "2"
        ]
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
    end_time = time.time()
    
    if result.returncode != 0:
        print(f"Error running {algorithm}: {result.stderr}")
        return None
    
    # Parse output
    lines = result.stdout.strip().split('\n')
    reward = None
    cost = None
    path_length = None
    execution_time = None
    
    for line in lines:
        if line.startswith("Total reward:"):
            reward = int(line.split(":")[1].strip())
        elif line.startswith("Total cost:"):
            cost = float(line.split(":")[1].strip())
        elif line.startswith("Execution time:"):
            execution_time = float(line.split(":")[1].strip().replace(" seconds", ""))
        elif line.startswith("Best path:"):
            path_str = line.split(":", 1)[1].strip()
            # Count nodes in path (simple comma count + 1)
            path_length = path_str.count(',') + 1
    
    return {
        'reward': reward,
        'cost': cost,
        'path_length': path_length,
        'execution_time': execution_time,
        'actual_time': end_time - start_time
    }

def main():
    problem_file = "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    max_time = 2.0
    
    print("Performance Comparison: UCT vs WU-UCT")
    print("=" * 50)
    print(f"Problem: {problem_file}")
    print(f"Max time: {max_time}s")
    
    # Run UCT
    uct_result = run_algorithm("uct", problem_file, max_time)
    if uct_result:
        print(f"UCT Result:")
        print(f"  Reward: {uct_result['reward']}")
        print(f"  Path length: {uct_result['path_length']} nodes")
        print(f"  Cost: {uct_result['cost']:.2f}")
        print(f"  Execution time: {uct_result['execution_time']:.2f}s")
    
    # Run WU-UCT
    wu_result = run_algorithm("wu-uct", problem_file, max_time)
    if wu_result:
        print(f"WU-UCT Result:")
        print(f"  Reward: {wu_result['reward']}")
        print(f"  Path length: {wu_result['path_length']} nodes")
        print(f"  Cost: {wu_result['cost']:.2f}")
        print(f"  Execution time: {wu_result['execution_time']:.2f}s")
    
    # Comparison
    if uct_result and wu_result:
        print(f"\n=== COMPARISON ===")
        reward_ratio = wu_result['reward'] / uct_result['reward'] if uct_result['reward'] > 0 else 0
        time_ratio = wu_result['execution_time'] / uct_result['execution_time'] if uct_result['execution_time'] > 0 else 0
        print(f"WU-UCT Reward Ratio: {reward_ratio:.3f}x ({wu_result['reward']} vs {uct_result['reward']})")
        print(f"WU-UCT Time Ratio: {time_ratio:.3f}x ({wu_result['execution_time']:.2f}s vs {uct_result['execution_time']:.2f}s)")
        
        if reward_ratio > 0.8:
            print("✅ WU-UCT quality is competitive")
        else:
            print("❌ WU-UCT quality needs improvement")
            
        if time_ratio < 1.5:
            print("✅ WU-UCT performance is reasonable")
        else:
            print("❌ WU-UCT performance needs improvement")

if __name__ == "__main__":
    main()