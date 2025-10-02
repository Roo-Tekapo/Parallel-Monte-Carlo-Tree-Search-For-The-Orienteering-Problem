#!/usr/bin/env python3
"""
Batch runner for UCT single-threaded algorithm on set_1000_1 datasets.
Runs UCT on all budget variants of the 1000-node problem set.
"""

import subprocess
import os
import time
from pathlib import Path


def run_uct_batch():
    """Run UCT on all set_1000_1 datasets."""
    
    # Base paths
    base_dir = Path("/Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem")
    uct_dir = base_dir / "UCT"
    dataset_dir = base_dir / "OP_Benchmark_Set" / "set_1000_1"
    
    # Get all dataset files and sort by budget
    dataset_files = list(dataset_dir.glob("set_1000_1_*.txt"))
    dataset_files.sort(key=lambda x: int(x.stem.split('_')[-1]))
    
    print(f"Found {len(dataset_files)} dataset files:")
    for f in dataset_files:
        budget = f.stem.split('_')[-1]
        print(f"  - Budget {budget}: {f.name}")
    
    print("\nStarting UCT batch run...")
    print("=" * 60)
    
    results = []
    
    for dataset_file in dataset_files:
        budget = dataset_file.stem.split('_')[-1]
        output_filename = f"single_thread_set1000_{budget}_100k.txt"
        
        print(f"\n🔄 Running UCT on budget {budget}...")
        print(f"   Dataset: {dataset_file.name}")
        print(f"   Output: {output_filename}")
        
        start_time = time.time()
        
        # Build command
        cmd = [
            "python3", "main.py",
            "--problem-file", str(dataset_file),
            "--algorithm", "uct",
            "--max-iterations", "100000",
            "--verbose",
            "--output-file", output_filename
        ]
        
        try:
            # Run the command
            process = subprocess.run(
                cmd,
                cwd=uct_dir,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout per run
            )
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            if process.returncode == 0:
                # Parse the output to get results
                output_lines = process.stdout.strip().split('\n')
                
                # Extract key results
                reward = None
                cost = None
                path_length = None
                
                for line in output_lines:
                    if line.startswith("Total reward:"):
                        reward = int(line.split()[-1])
                    elif line.startswith("Total cost:"):
                        cost = float(line.split()[-1])
                    elif line.startswith("Best path:"):
                        path_str = line.split(":", 1)[1].strip()
                        path_str = path_str.strip("[]")
                        path_length = len([x.strip() for x in path_str.split(",") if x.strip()])
                
                print(f"   ✅ Success! Time: {elapsed:.1f}s")
                print(f"      Reward: {reward}, Cost: {cost:.2f}, Path length: {path_length}")
                
                results.append({
                    'budget': int(budget),
                    'success': True,
                    'time': elapsed,
                    'reward': reward,
                    'cost': cost,
                    'path_length': path_length,
                    'output_file': output_filename
                })
            else:
                print(f"   ❌ Failed! Return code: {process.returncode}")
                print(f"      Error: {process.stderr}")
                
                results.append({
                    'budget': int(budget),
                    'success': False,
                    'time': elapsed,
                    'error': process.stderr,
                    'output_file': output_filename
                })
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ Timeout after 1 hour")
            results.append({
                'budget': int(budget),
                'success': False,
                'time': 3600,
                'error': 'Timeout',
                'output_file': output_filename
            })
        except Exception as e:
            print(f"   💥 Exception: {e}")
            results.append({
                'budget': int(budget),
                'success': False,
                'time': 0,
                'error': str(e),
                'output_file': output_filename
            })
    
    # Print summary
    print("\n" + "=" * 60)
    print("BATCH RUN SUMMARY")
    print("=" * 60)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"Total runs: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        print(f"\n✅ SUCCESSFUL RUNS:")
        print(f"{'Budget':<8} {'Reward':<8} {'Cost':<10} {'Path':<6} {'Time':<8} {'Output File'}")
        print("-" * 60)
        for r in successful:
            print(f"{r['budget']:<8} {r['reward']:<8} {r['cost']:<10.2f} {r['path_length']:<6} {r['time']:<8.1f}s {r['output_file']}")
    
    if failed:
        print(f"\n❌ FAILED RUNS:")
        for r in failed:
            print(f"Budget {r['budget']}: {r['error']}")
    
    total_time = sum(r['time'] for r in results)
    print(f"\nTotal execution time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    
    # Save summary to file
    summary_file = uct_dir / "uct-output" / "batch_summary_set1000_uct.txt"
    with open(summary_file, 'w') as f:
        f.write("UCT Batch Run Summary - set_1000_1 datasets\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total runs: {len(results)}\n")
        f.write(f"Successful: {len(successful)}\n")
        f.write(f"Failed: {len(failed)}\n\n")
        
        if successful:
            f.write("SUCCESSFUL RUNS:\n")
            f.write(f"{'Budget':<8} {'Reward':<8} {'Cost':<10} {'Path':<6} {'Time':<8} {'Output File'}\n")
            f.write("-" * 60 + "\n")
            for r in successful:
                f.write(f"{r['budget']:<8} {r['reward']:<8} {r['cost']:<10.2f} {r['path_length']:<6} {r['time']:<8.1f}s {r['output_file']}\n")
        
        if failed:
            f.write("\nFAILED RUNS:\n")
            for r in failed:
                f.write(f"Budget {r['budget']}: {r['error']}\n")
        
        f.write(f"\nTotal execution time: {total_time:.1f}s ({total_time/60:.1f} minutes)\n")
    
    print(f"\nSummary saved to: {summary_file}")


if __name__ == "__main__":
    run_uct_batch()