"""
WU-UCT Solver for Orienteering Problem
"""
import argparse
import time
import os
import sys
from typing import List, Tuple, Optional

# Import orienteering module from current directory
from orienteering.orienteering import OrienteeringProblem, OrienteeringState

# Import WU-UCT components
from WU_UCT.wu_orienteering_tree import WUOrienteeringTree
from WU_UCT.wu_orienteering_worker import WUOrienteeringWorker
from WU_UCT.wu_specialized_workers import WUCoordinatedSolver


class WUOrienteeringSolver:
    """WU-UCT solver for the Orienteering Problem"""
    
    def __init__(self, problem: OrienteeringProblem, 
                 num_workers: int = 4,
                 expansion_workers: int = None,
                 simulation_workers: int = None,
                 max_steps: int = 1000,
                 max_depth: int = 20,
                 max_width: int = 10,
                 gamma: float = 1.0):
        self.problem = problem
        self.num_workers = num_workers
        self.expansion_workers = expansion_workers or num_workers
        self.simulation_workers = simulation_workers or num_workers
        self.max_steps = max_steps
        self.max_depth = max_depth
        self.max_width = max_width
        self.gamma = gamma
        
        # Initialize tree
        self.tree = WUOrienteeringTree(
            problem=problem,
            max_steps=max_steps,
            max_depth=max_depth,
            max_width=max_width,
            gamma=gamma,
            expansion_worker_num=self.expansion_workers,
            simulation_worker_num=self.simulation_workers
        )
        
        # Workers
        self.workers: List[WUOrienteeringWorker] = []
        self.workers_running = False
    
    def solve(self, max_iterations: Optional[int] = None,
              max_time: Optional[float] = None,
              iterations_per_worker: Optional[int] = None,
              verbose: bool = False) -> Tuple[List[int], float, dict]:
        """
        Solve the orienteering problem using WU-UCT
        
        Returns: (best_path, best_reward, statistics)
        """
        if verbose:
            print(f"Starting WU-UCT solver (single-threaded)")
            print(f"Problem: {len(self.problem.nodes)} nodes, budget: {self.problem.budget}")
        
        # Use the tree's solve method which is simpler and more reliable
        return self.tree.solve_complete_problem(
            max_iterations=max_iterations or 10000,
            verbose=verbose
        )
    
    def solve_parallel(self, max_iterations: Optional[int] = None,
                      max_time: Optional[float] = None,
                      iterations_per_worker: Optional[int] = None,
                      verbose: bool = False) -> Tuple[List[int], float, dict]:
        """
        Solve the orienteering problem using parallel WU-UCT (original implementation)
        
        Returns: (best_path, best_reward, statistics)
        """
        start_time = time.time()
        
        if verbose:
            print(f"Starting WU-UCT solver (parallel) with {self.num_workers} workers")
            print(f"Problem: {len(self.problem.nodes)} nodes, budget: {self.problem.budget}")
        
        # Calculate iterations per worker
        if iterations_per_worker is None and max_iterations:
            iterations_per_worker = max_iterations // self.num_workers
        
        # Start workers
        self._start_workers(iterations_per_worker, max_time)
        
        if verbose:
            print(f"Started {self.num_workers} workers")
            if max_time:
                self._monitor_progress(max_time)
        
        # Wait for completion
        self._wait_for_completion()
        
        # Get results from the current tree state (don't reset/re-solve)
        best_path, best_reward = self.tree._extract_best_complete_path()
        tree_stats = self.tree.get_statistics()
        
        # Collect statistics
        elapsed_time = time.time() - start_time
        stats = self._collect_statistics(elapsed_time, tree_stats)
        
        if verbose:
            print(f"\nParallel solution found:")
            print(f"Best path: {best_path}")
            print(f"Best reward: {best_reward}")
            print(f"Total time: {elapsed_time:.2f}s")
            print(f"Total simulations: {stats['total_simulations']}")
            
            # Display detailed worker statistics
            print(f"\nWorker Performance Details:")
            print(f"{'Worker':<8} {'Iterations':<12} {'Rate (it/s)':<12} {'Time (s)':<10} {'Status':<10}")
            print("-" * 60)
            for worker_stat in stats['worker_stats']:
                print(f"{worker_stat['worker_id']:<8} "
                      f"{worker_stat['iterations_completed']:<12} "
                      f"{worker_stat['iterations_per_second']:<12.1f} "
                      f"{worker_stat['elapsed_time']:<10.2f} "
                      f"{'Running' if worker_stat['running'] else 'Stopped':<10}")
            
            print(f"\nSummary:")
            print(f"- Total workers: {len(stats['worker_stats'])}")
            print(f"- Average iterations per worker: {stats['total_worker_iterations'] / len(stats['worker_stats']):.0f}")
            print(f"- Combined iteration rate: {stats['total_worker_iterations'] / elapsed_time:.1f} iterations/s")
        
        return best_path, best_reward, stats
    
    def solve_wu_uct(self, max_iterations: Optional[int] = None,
                     max_time: Optional[float] = None,
                     verbose: bool = False) -> Tuple[List[int], float, dict]:
        """
        Solve the orienteering problem using True WU-UCT with specialized workers
        
        Returns: (best_path, best_reward, statistics)
        """
        if verbose:
            print(f"Starting WU-UCT solver with {self.expansion_workers} expansion workers "
                  f"and {self.simulation_workers} simulation workers")
        
        # Create coordinated solver
        coordinated_solver = WUCoordinatedSolver(
            tree=self.tree,
            num_expansion_workers=self.expansion_workers,
            num_simulation_workers=self.simulation_workers
        )
        
        try:
            return coordinated_solver.solve(
                max_iterations=max_iterations,
                max_time=max_time,
                verbose=verbose
            )
        finally:
            coordinated_solver.stop()
    
    def _start_workers(self, iterations_per_worker: Optional[int], max_time: Optional[float]):
        """Start worker threads"""
        self.workers = []
        for i in range(self.num_workers):
            worker = WUOrienteeringWorker(
                worker_id=i,
                tree=self.tree,
                max_iterations=iterations_per_worker,
                max_time=max_time
            )
            self.workers.append(worker)
            worker.start()
        
        self.workers_running = True
    
    def _wait_for_completion(self):
        """Wait for all workers to complete"""
        for worker in self.workers:
            worker.join()
        self.workers_running = False
    
    def _monitor_progress(self, max_time: float):
        """Monitor and print progress"""
        import threading
        
        def monitor():
            start = time.time()
            progress_count = 0
            while self.workers_running and (time.time() - start) < max_time:
                time.sleep(5)  # Update every 5 seconds
                if self.workers_running:
                    stats = self.tree.get_statistics()
                    elapsed = time.time() - start
                    print(f"Progress: {elapsed:.1f}s, Simulations: {stats['simulation_count']}, "
                          f"Best reward: {stats['best_reward']:.2f}")
                    
                    # Show detailed worker stats every 15 seconds
                    progress_count += 1
                    if progress_count % 3 == 0:  # Every 15 seconds (3 * 5s intervals)
                        active_workers = sum(1 for w in self.workers if w.is_alive())
                        total_iterations = sum(w.iterations_completed for w in self.workers)
                        print(f"  Active workers: {active_workers}/{len(self.workers)}, "
                              f"Total iterations: {total_iterations}")
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def _collect_statistics(self, elapsed_time: float, tree_stats: dict) -> dict:
        """Collect comprehensive statistics"""
        worker_stats = []
        total_worker_iterations = 0
        for worker in self.workers:
            stats = worker.get_statistics()
            worker_stats.append(stats)
            total_worker_iterations += stats['iterations_completed']
        
        combined_stats = {
            'elapsed_time': elapsed_time,
            'total_simulations': tree_stats.get('simulation_count', 0),
            'total_worker_iterations': total_worker_iterations,
            'simulations_per_second': tree_stats.get('simulation_count', 0) / max(elapsed_time, 0.001),
            'num_workers': self.num_workers,
            'worker_stats': worker_stats
        }
        
        # Merge tree stats
        combined_stats.update(tree_stats)
        return combined_stats
    
    def stop(self):
        """Stop all workers"""
        for worker in self.workers:
            worker.stop()
        self.workers_running = False


def main():
    parser = argparse.ArgumentParser(description="WU-UCT for Orienteering Problem")
    
    # Problem parameters
    parser.add_argument("--problem-file", type=str, required=True,
                        help="Path to orienteering problem file")
    parser.add_argument("--max-edge-distance", type=float, default=None,
                        help="Maximum edge distance constraint (default: no constraint)")
    
    # Algorithm parameters  
    parser.add_argument("--max-iterations", type=int, default=10000,
                        help="Maximum number of MCTS iterations (default: 10000)")
    parser.add_argument("--max-time", type=float, default=30.0,
                        help="Maximum time in seconds (default: 30)")
    parser.add_argument("--max-steps", type=int, default=1000,
                        help="Max simulation steps per move (default: 1000)")
    parser.add_argument("--max-depth", type=int, default=50,
                        help="Max depth of MCTS simulation (default: 50)")
    parser.add_argument("--max-width", type=int, default=10,
                        help="Max width of MCTS simulation (default: 10)")
    parser.add_argument("--gamma", type=float, default=1.0,
                        help="Discount factor (default: 1.0)")
    
    # Parallel parameters
    parser.add_argument("--num-workers", type=int, default=4,
                        help="Number of worker threads (default: 4)")
    parser.add_argument("--expansion-workers", type=int, default=None,
                        help="Number of expansion workers (default: 1 for 8+ cores, else num-workers)")
    parser.add_argument("--simulation-workers", type=int, default=None,
                        help="Number of simulation workers (default: remaining cores after expansion)")
    parser.add_argument("--parallel", action="store_true",
                        help="Use parallel WU-UCT (original implementation, default: False)")
    parser.add_argument("--wu-uct", action="store_true",
                        help="Use True WU-UCT with specialized workers (default: False)")
    
    # Output parameters
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose output (default: False)")
    parser.add_argument("--output-file", type=str, default=None,
                        help="Output file for results")
    
    args = parser.parse_args()
    
    # Load problem
    try:
        nodes, budget = OrienteeringProblem.load_problem(args.problem_file)
        problem = OrienteeringProblem(nodes, budget, args.max_edge_distance)
        
        if args.verbose:
            print(f"Loaded problem: {len(nodes)} nodes, budget: {budget}")
            if args.max_edge_distance:
                print(f"Max edge distance: {args.max_edge_distance}")
                
    except Exception as e:
        print(f"Error loading problem file: {e}")
        return
    
    # Determine optimal worker configuration
    if args.expansion_workers is None or args.simulation_workers is None:
        # Auto-configure based on WU-UCT paper recommendations
        total_cores = args.num_workers
        if total_cores >= 8:
            # For 8+ cores: 1 expansion worker, rest simulation workers (WU-UCT paper style)
            expansion_workers = args.expansion_workers or 1
            simulation_workers = args.simulation_workers or (total_cores - expansion_workers)
        else:
            # For fewer cores: use traditional approach (all workers do full iterations)
            expansion_workers = args.expansion_workers or total_cores
            simulation_workers = args.simulation_workers or total_cores
    else:
        expansion_workers = args.expansion_workers
        simulation_workers = args.simulation_workers
    
    # Only print worker configuration for modes that use workers
    if args.verbose and (args.parallel or args.wu_uct):
        if args.wu_uct:
            print(f"Worker configuration: {expansion_workers} expansion, {simulation_workers} simulation")
        elif args.parallel:
            print(f"Worker configuration: {args.num_workers} parallel workers")
    
    # Create solver
    solver = WUOrienteeringSolver(
        problem=problem,
        num_workers=args.num_workers,
        expansion_workers=expansion_workers,
        simulation_workers=simulation_workers,
        max_steps=args.max_steps,
        max_depth=args.max_depth,
        max_width=args.max_width,
        gamma=args.gamma
    )
    
    # Solve
    try:
        if args.wu_uct:
            best_path, best_reward, stats = solver.solve_wu_uct(
                max_iterations=args.max_iterations,
                max_time=args.max_time,
                verbose=args.verbose
            )
        elif args.parallel:
            best_path, best_reward, stats = solver.solve_parallel(
                max_iterations=args.max_iterations,
                max_time=args.max_time,
                verbose=args.verbose
            )
        else:
            best_path, best_reward, stats = solver.solve(
                max_iterations=args.max_iterations,
                verbose=args.verbose
            )
        
        # Output results
        print(f"\nFinal Results:")
        print(f"Best path: {best_path}")
        print(f"Best reward: {best_reward}")
        print(f"Time taken: {stats.get('elapsed_time', 0):.2f}s")
        print(f"Iterations: {stats.get('total_simulations', 0)}")
        
        # Save results if requested
        if args.output_file:
            with open(args.output_file, 'w') as f:
                f.write(f"Problem: {args.problem_file}\n")
                f.write(f"Best path: {best_path}\n")
                f.write(f"Best reward: {best_reward}\n")
                f.write(f"Statistics: {stats}\n")
            print(f"Results saved to {args.output_file}")
            
    except KeyboardInterrupt:
        print("\nSolver interrupted by user")
        solver.stop()
    except Exception as e:
        print(f"Error during solving: {e}")
        solver.stop()


if __name__ == "__main__":
    main()