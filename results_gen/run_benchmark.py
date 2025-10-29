#!/usr/bin/env python3
"""
Benchmark Runner for Orienteering Problem Solvers

This script runs multiple MCTS algorithms (UCT, Simple_WU, VL) and OR-Tools
on a set of orienteering problems and exports results to Excel.

Usage:
    python run_benchmark.py --dataset grid_sample --algorithms uct simple_wu vl ortools --iterations 10000
    python run_benchmark.py --dataset all --algorithms all --output results.xlsx
"""

import argparse
import sys
import os
import time
import glob
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import traceback

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Excel writing support
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not available. Install with: pip install pandas openpyxl")


class BenchmarkRunner:
    """Runs benchmarks on different orienteering problem solvers."""
    
    def __init__(self, output_dir: str = None):
        """
        Initialize benchmark runner.
        
        Args:
            output_dir: Directory to save results (default: results_gen/outputs)
        """
        self.project_root = project_root
        self.benchmark_dir = project_root / "OP_Benchmark_Set"
        
        if output_dir is None:
            self.output_dir = project_root / "results_gen" / "outputs"
        else:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.results = []
        
    def get_problem_files(self, dataset_name: str) -> List[Path]:
        """
        Get list of problem files from a dataset.
        
        Args:
            dataset_name: Name of dataset folder or 'all' for all datasets
            
        Returns:
            List of problem file paths
        """
        problem_files = []
        
        if dataset_name == 'all':
            # Get all .txt files from all subdirectories
            problem_files = list(self.benchmark_dir.glob("**/*.txt"))
        else:
            # Get files from specific dataset folder
            dataset_path = self.benchmark_dir / dataset_name
            if not dataset_path.exists():
                print(f"Warning: Dataset '{dataset_name}' not found at {dataset_path}")
                return []
            problem_files = list(dataset_path.glob("*.txt"))
        
        return sorted(problem_files)
    
    def run_uct_single(self, problem_file: Path, max_iterations: int = 10000, 
                       max_time: Optional[float] = None, **kwargs) -> Dict:
        """
        Run single-threaded UCT algorithm.
        
        Args:
            problem_file: Path to problem file
            max_iterations: Maximum iterations
            max_time: Maximum time in seconds
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with results
        """
        try:
            # Set environment variable
            os.environ['UCT_USE_NO_END'] = 'false'
            
            from UCT.uct_single_thread import UCTSingleThread
            from UCT.orienteering_adapter import OrienteeringProblem
            
            # Load problem
            nodes, budget = OrienteeringProblem.load_problem(str(problem_file))
            problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
            
            # Run UCT
            start_time = time.time()
            uct = UCTSingleThread(problem, iterations=max_iterations)
            best_state = uct.run(max_time=max_time)
            elapsed_time = time.time() - start_time
            
            # Get statistics
            stats = uct.get_statistics()
            
            # Calculate raw reward
            raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
            
            return {
                'algorithm': 'UCT',
                'problem': problem_file.name,
                'problem_file': problem_file.name,
                'dataset': problem_file.parent.name,
                'num_nodes': len(nodes),
                'budget': budget,
                'iterations': stats.get('iterations', max_iterations),
                'elapsed_time': elapsed_time,
                'best_path': str(best_state.get_path()),
                'path_length': len(best_state.get_path()),
                'normalized_reward': best_state.get_reward(),
                'raw_reward': raw_reward,
                'total_cost': best_state.get_cost(),
                'budget_used_pct': (best_state.get_cost() / budget * 100) if budget > 0 else 0,
                'success': True,
                'error': None
            }
        except Exception as e:
            return {
                'algorithm': 'UCT',
                'problem': problem_file.name,
                'problem_file': problem_file.name,
                'dataset': problem_file.parent.name,
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def run_simple_wu(self, problem_file: Path, max_iterations: int = 10000,
                      num_workers: int = 4, max_time: Optional[float] = None, **kwargs) -> Dict:
        """
        Run Simple WU-UCT algorithm.
        
        Args:
            problem_file: Path to problem file
            max_iterations: Maximum iterations
            num_workers: Number of workers
            max_time: Maximum time in seconds
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with results
        """
        try:
            # Set environment variable
            os.environ['SIMPLE_WU_USE_NO_END'] = 'false'
            
            from Simple_WU.simple_wu_coordinator import SimpleWUUCT
            from Simple_WU.orienteering_adapter import OrienteeringProblem
            
            # Load problem
            nodes, budget = OrienteeringProblem.load_problem(str(problem_file))
            problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
            
            # Run Simple WU-UCT
            start_time = time.time()
            simple_wu = SimpleWUUCT(problem, num_workers=num_workers)
            best_state = simple_wu.run(max_iterations=max_iterations, max_time=max_time, verbose=False)
            elapsed_time = time.time() - start_time
            
            # Get statistics
            stats = simple_wu.get_tree_statistics()
            
            # Calculate raw reward
            raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
            
            return {
                'algorithm': 'Simple_WU',
                'problem': problem_file.name,
                'problem_file': problem_file.name,
                'dataset': problem_file.parent.name,
                'num_nodes': len(nodes),
                'budget': budget,
                'num_workers': num_workers,
                'iterations': stats.get('iterations', max_iterations),
                'elapsed_time': elapsed_time,
                'best_path': str(best_state.get_path()),
                'path_length': len(best_state.get_path()),
                'normalized_reward': best_state.get_reward(),
                'raw_reward': raw_reward,
                'total_cost': best_state.get_cost(),
                'budget_used_pct': (best_state.get_cost() / budget * 100) if budget > 0 else 0,
                'success': True,
                'error': None
            }
        except Exception as e:
            return {
                'algorithm': 'Simple_WU',
                'problem': problem_file.name,
                'problem_file': problem_file.name,
                'dataset': problem_file.parent.name,
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def run_vl(self, problem_file: Path, max_iterations: int = 10000,
               num_workers: int = 4, vl_value: float = 1.0,
               max_time: Optional[float] = None, **kwargs) -> Dict:
        """
        Run Virtual Loss MCTS algorithm.
        
        Args:
            problem_file: Path to problem file
            max_iterations: Maximum iterations
            num_workers: Number of workers
            vl_value: Virtual loss penalty value
            max_time: Maximum time in seconds
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with results
        """
        try:
            # Set environment variable
            os.environ['VL_USE_NO_END'] = 'false'
            
            from VL.vl_coordinator import VirtualLossMCTS
            from VL.orienteering_adapter import OrienteeringProblem
            
            # Load problem
            nodes, budget = OrienteeringProblem.load_problem(str(problem_file))
            problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
            
            # Run VL-MCTS
            start_time = time.time()
            vl_mcts = VirtualLossMCTS(problem, num_workers=num_workers, 
                                     virtual_loss_value=vl_value)
            best_state = vl_mcts.run(max_iterations=max_iterations, max_time=max_time, verbose=False)
            elapsed_time = time.time() - start_time
            
            # Get statistics
            stats = vl_mcts.get_tree_statistics()
            
            # Calculate raw reward
            raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
            
            return {
                'algorithm': 'VL',
                'problem': problem_file.name,
                'problem_file': problem_file.name,
                'dataset': problem_file.parent.name,
                'num_nodes': len(nodes),
                'budget': budget,
                'num_workers': num_workers,
                'vl_value': vl_value,
                'iterations': stats.get('iterations', max_iterations),
                'elapsed_time': elapsed_time,
                'best_path': str(best_state.get_path()),
                'path_length': len(best_state.get_path()),
                'normalized_reward': best_state.get_reward(),
                'raw_reward': raw_reward,
                'total_cost': best_state.get_cost(),
                'budget_used_pct': (best_state.get_cost() / budget * 100) if budget > 0 else 0,
                'success': True,
                'error': None
            }
        except Exception as e:
            return {
                'algorithm': 'VL',
                'problem': problem_file.name,
                'problem_file': problem_file.name,
                'dataset': problem_file.parent.name,
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def run_ortools(self, problem_file: Path, time_limit: int = 30, **kwargs) -> Dict:
        """
        Run OR-Tools solver.
        
        Args:
            problem_file: Path to problem file
            time_limit: Time limit in seconds
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with results
        """
        try:
            from OR_Tool.or_tools_solver import ORToolsOrienteeringSolver
            from orienteering.orienteering import OrienteeringProblem
            
            # Load problem
            nodes, budget = OrienteeringProblem.load_problem(str(problem_file))
            problem = OrienteeringProblem(nodes, budget)
            
            # Run OR-Tools
            start_time = time.time()
            solver = ORToolsOrienteeringSolver(problem, time_limit_seconds=time_limit)
            path, reward, distance, stats = solver.solve(verbose=False)
            elapsed_time = time.time() - start_time
            
            return {
                'algorithm': 'OR-Tools',
                'problem': problem_file.name,
                'problem_file': problem_file.name,
                'dataset': problem_file.parent.name,
                'num_nodes': len(nodes),
                'budget': budget,
                'time_limit': time_limit,
                'elapsed_time': elapsed_time,
                'best_path': str(path),
                'path_length': len(path),
                'raw_reward': reward,
                'total_cost': distance,
                'budget_used_pct': (distance / budget * 100) if budget > 0 else 0,
                'solver_status': stats.get('status', 'Unknown'),
                'success': True,
                'error': None
            }
        except Exception as e:
            return {
                'algorithm': 'OR-Tools',
                'problem': problem_file.name,
                'problem_file': problem_file.name,
                'dataset': problem_file.parent.name,
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def run_benchmark(self, problem_files: List[Path], algorithms: List[str],
                     max_iterations: int = 10000, num_workers: int = 4,
                     max_time: Optional[float] = None, vl_value: float = 1.0,
                     ortools_time_limit: int = 60, num_runs: int = 1, verbose: bool = True):
        """
        Run benchmark on multiple problems and algorithms.
        
        Args:
            problem_files: List of problem files to test
            algorithms: List of algorithms to run ('uct', 'simple_wu', 'vl', 'ortools')
            max_iterations: Maximum iterations for MCTS algorithms
            num_workers: Number of workers for parallel algorithms
            max_time: Maximum time in seconds (optional)
            vl_value: Virtual loss value for VL algorithm
            ortools_time_limit: Time limit for OR-Tools (default: 60 seconds)
            num_runs: Number of times to run each algorithm on each problem (Note: OR-Tools runs only once per problem)
            verbose: Print progress information
        """
        # Calculate total runs accounting for OR-Tools running only once
        ortools_in_algos = 'ortools' in algorithms
        ortools_runs = len(problem_files) if ortools_in_algos else 0
        other_algo_runs = len(problem_files) * len([a for a in algorithms if a != 'ortools']) * num_runs
        total_runs = ortools_runs + other_algo_runs
        current_run = 0
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"Starting Benchmark Run")
            print(f"{'='*80}")
            print(f"Problems: {len(problem_files)}")
            print(f"Algorithms: {', '.join(algorithms)}")
            if num_runs > 1:
                print(f"Runs per algorithm: {num_runs}")
                if ortools_in_algos:
                    print(f"Note: OR-Tools runs only once per problem (deterministic)")
            print(f"Total runs: {total_runs}")
            print(f"{'='*80}\n")
        
        # Cache to store OR-Tools results for each problem
        ortools_cache = {}
        
        for problem_file in problem_files:
            if verbose:
                print(f"\n--- Problem: {problem_file.name} ---")
            
            for algo in algorithms:
                # OR-Tools only runs once per problem (deterministic)
                algo_runs = 1 if algo == 'ortools' else num_runs
                
                for run_num in range(algo_runs):
                    current_run += 1
                    
                    if verbose:
                        run_label = f" (run {run_num + 1}/{algo_runs})" if algo_runs > 1 else ""
                        print(f"  [{current_run}/{total_runs}] Running {algo.upper()}{run_label}...", end=' ', flush=True)
                    
                    # Run the appropriate algorithm
                    if algo == 'uct':
                        result = self.run_uct_single(problem_file, max_iterations=max_iterations,
                                                    max_time=max_time)
                    elif algo == 'simple_wu':
                        result = self.run_simple_wu(problem_file, max_iterations=max_iterations,
                                                  num_workers=num_workers, max_time=max_time)
                    elif algo == 'vl':
                        result = self.run_vl(problem_file, max_iterations=max_iterations,
                                           num_workers=num_workers, vl_value=vl_value,
                                           max_time=max_time)
                    elif algo == 'ortools':
                        # Check cache first
                        cache_key = str(problem_file)
                        if cache_key in ortools_cache:
                            result = ortools_cache[cache_key].copy()
                            if verbose:
                                print(f"✓ (Cached - Reward: {result.get('raw_reward', 'N/A'):.2f}, Time: {result.get('elapsed_time', 0):.2f}s)")
                        else:
                            result = self.run_ortools(problem_file, time_limit=ortools_time_limit)
                            ortools_cache[cache_key] = result.copy()
                            if verbose:
                                if result['success']:
                                    reward = result.get('raw_reward', result.get('normalized_reward', 'N/A'))
                                    time_taken = result.get('elapsed_time', 0)
                                    print(f"✓ (Reward: {reward:.2f}, Time: {time_taken:.2f}s)")
                                else:
                                    print(f"✗ Error: {result.get('error', 'Unknown error')}")
                    else:
                        if verbose:
                            print(f"Unknown algorithm: {algo}")
                        continue
                    
                    # Add run number to result
                    if num_runs > 1 and algo != 'ortools':
                        result['run_number'] = run_num + 1
                    
                    # Store result
                    self.results.append(result)
                    
                    # Print result if not already printed (for non-cached results)
                    if verbose and algo != 'ortools':
                        if result['success']:
                            reward = result.get('raw_reward', result.get('normalized_reward', 'N/A'))
                            time_taken = result.get('elapsed_time', 0)
                            print(f"✓ (Reward: {reward:.2f}, Time: {time_taken:.2f}s)")
                        else:
                            print(f"✗ Error: {result.get('error', 'Unknown error')}")
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"Benchmark Complete!")
            print(f"Successful runs: {sum(1 for r in self.results if r['success'])}/{total_runs}")
            print(f"{'='*80}\n")
    
    def save_results_to_excel(self, filename: str = None):
        """
        Save results to Excel file.
        
        Args:
            filename: Output filename (default: benchmark_results_TIMESTAMP.xlsx)
        """
        if not PANDAS_AVAILABLE:
            print("Error: pandas not available. Cannot save to Excel.")
            print("Install with: pip install pandas openpyxl")
            return None
        
        if not self.results:
            print("No results to save!")
            return None
        
        # Create filename with timestamp if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.xlsx"
        
        # Ensure .xlsx extension
        if not filename.endswith('.xlsx'):
            filename += '.xlsx'
        
        output_path = self.output_dir / filename
        
        try:
            # Convert results to DataFrame
            df = pd.DataFrame(self.results)
            
            # Create Excel writer with multiple sheets
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Main results sheet
                df.to_excel(writer, sheet_name='All Results', index=False)
                
                # Successful results only
                df_success = df[df['success'] == True]
                if not df_success.empty:
                    df_success.to_excel(writer, sheet_name='Successful Runs', index=False)
                
                # Algorithm Summary - Overall statistics
                if not df_success.empty and 'algorithm' in df_success.columns:
                    numeric_cols = ['raw_reward', 'elapsed_time', 'budget_used_pct']
                    available_numeric_cols = [col for col in numeric_cols if col in df_success.columns]
                    
                    if available_numeric_cols:
                        # Overall statistics by algorithm (main summary)
                        overall = df_success.groupby('algorithm')[available_numeric_cols].agg(['mean', 'std', 'min', 'max'])
                        overall.to_excel(writer, sheet_name='Algorithm Summary')
                
                # Stats by Problem - Per-problem breakdown
                if not df_success.empty and 'algorithm' in df_success.columns and 'problem' in df_success.columns:
                    numeric_cols = ['raw_reward', 'elapsed_time', 'budget_used_pct']
                    available_numeric_cols = [col for col in numeric_cols if col in df_success.columns]
                    
                    if available_numeric_cols:
                        # Per-problem statistics by algorithm
                        per_problem = df_success.groupby(['problem', 'algorithm'])[available_numeric_cols].agg(['mean', 'std', 'min', 'max'])
                        per_problem.to_excel(writer, sheet_name='Stats by Problem')
                
                # Failed runs
                df_failed = df[df['success'] == False]
                if not df_failed.empty:
                    df_failed.to_excel(writer, sheet_name='Failed Runs', index=False)
            
            print(f"\n✓ Results saved to: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error saving to Excel: {e}")
            traceback.print_exc()
            return None
    
    def save_results_to_json(self, filename: str = None):
        """
        Save results to JSON file (alternative to Excel).
        
        Args:
            filename: Output filename (default: benchmark_results_TIMESTAMP.json)
        """
        if not self.results:
            print("No results to save!")
            return None
        
        # Create filename with timestamp if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        output_path = self.output_dir / filename
        
        try:
            with open(output_path, 'w') as f:
                json.dump(self.results, f, indent=2)
            
            print(f"\n✓ Results saved to: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error saving to JSON: {e}")
            traceback.print_exc()
            return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Benchmark runner for orienteering problem solvers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all algorithms on grid_sample dataset
  python run_benchmark.py --dataset grid_sample --algorithms all
  
  # Run UCT and VL on specific dataset with custom iterations
  python run_benchmark.py --dataset set_64_1 --algorithms uct vl --iterations 20000
  
  # Run OR-Tools only on all datasets
  python run_benchmark.py --dataset all --algorithms ortools
  
  # Use time limit instead of iterations
  python run_benchmark.py --dataset sample --algorithms all --max-time 60
  
Available datasets:
  grid_sample, grid_patterns, parallel_friendly_v2, sample,
  set_64_1, set_100_1, set_1000_1, Tsiligirides_1, or 'all'
        """
    )

    parser.add_argument('--dataset', '-d', type=str, default='grid_sample',
                       help='Dataset name or "all" for all datasets (default: grid_sample)')
    parser.add_argument('--algorithms', '-a', nargs='+',
                       default=['uct', 'simple_wu', 'vl', 'ortools'],
                       help='Algorithms to run: uct, simple_wu, vl, ortools, or "all" (default: all)')
    parser.add_argument('--iterations', '-i', type=int, default=10000,
                       help='Maximum iterations for MCTS algorithms (default: 10000)')
    parser.add_argument('--max-time', '-t', type=float, default=None,
                       help='Maximum time in seconds (overrides iterations)')
    parser.add_argument('--runs', '-r', type=int, default=1,
                       help='Number of times to run each algorithm on each problem (default: 1)')
    parser.add_argument('--workers', '-w', type=int, default=4,
                       help='Number of workers for parallel algorithms (default: 4)')
    parser.add_argument('--vl-value', type=float, default=1.0,
                       help='Virtual loss value for VL algorithm (default: 1.0)')
    parser.add_argument('--ortools-time', type=int, default=60,
                       help='Time limit for OR-Tools in seconds (default: 60)')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='Output filename (default: benchmark_results_TIMESTAMP.xlsx)')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Output directory (default: results_gen/outputs)')
    parser.add_argument('--format', type=str, choices=['excel', 'json', 'both'], default='excel',
                       help='Output format (default: excel)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress progress output')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of problem files to test (for quick testing)')
    
    args = parser.parse_args()
    
    # Handle "all" shortcut for algorithms
    if 'all' in args.algorithms:
        args.algorithms = ['uct', 'simple_wu', 'vl', 'ortools']
    
    # Initialize benchmark runner
    runner = BenchmarkRunner(output_dir=args.output_dir)
    
    # Get problem files
    problem_files = runner.get_problem_files(args.dataset)
    
    if not problem_files:
        print(f"Error: No problem files found for dataset '{args.dataset}'")
        print(f"Available datasets in {runner.benchmark_dir}:")
        for subdir in sorted(runner.benchmark_dir.iterdir()):
            if subdir.is_dir():
                print(f"  - {subdir.name}")
        sys.exit(1)
    
    # Apply limit if specified
    if args.limit:
        problem_files = problem_files[:args.limit]
        if not args.quiet:
            print(f"Limiting to first {args.limit} problem files")
    
    # Run benchmark
    runner.run_benchmark(
        problem_files=problem_files,
        algorithms=args.algorithms,
        max_iterations=args.iterations,
        num_workers=args.workers,
        max_time=args.max_time,
        vl_value=args.vl_value,
        ortools_time_limit=args.ortools_time,
        num_runs=args.runs,
        verbose=not args.quiet
    )
    
    # Save results
    if args.format in ['excel', 'both']:
        runner.save_results_to_excel(args.output)
    
    if args.format in ['json', 'both']:
        json_filename = args.output.replace('.xlsx', '.json') if args.output else None
        runner.save_results_to_json(json_filename)


if __name__ == '__main__':
    main()
