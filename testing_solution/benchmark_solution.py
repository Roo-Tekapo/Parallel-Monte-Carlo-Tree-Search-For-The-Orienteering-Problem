"""
Benchmarking and Statistical Analysis Tool for OP Solutions
Runs multiple trials and provides statistical quality metrics
"""

import time
import sys
from pathlib import Path
import numpy as np
from typing import List, Dict, Callable, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from testing_solution.validate_solution import validate_solution, greedy_nearest_neighbor, calculate_upper_bound


def run_multiple_trials(
    problem: OrienteeringProblem,
    solver_func: Callable[[OrienteeringProblem], Tuple[List[int], float]],
    num_trials: int = 10,
    algorithm_name: str = "Algorithm"
) -> Dict:
    """
    Run solver multiple times and collect statistics.
    
    Args:
        problem: The OP instance
        solver_func: Function that takes problem and returns (path, reward)
        num_trials: Number of trials to run
        algorithm_name: Name for reporting
    
    Returns:
        Dictionary with statistics
    """
    print(f"\nRunning {num_trials} trials of {algorithm_name}...")
    print("-" * 60)
    
    valid_rewards = []
    all_rewards = []
    valid_paths = []
    times = []
    valid_count = 0
    
    for trial in range(num_trials):
        start_time = time.time()
        
        try:
            path, reward = solver_func(problem)
            elapsed = time.time() - start_time
            
            validation = validate_solution(problem, path)
            all_rewards.append(reward)
            times.append(elapsed)
            
            if validation['is_valid']:
                valid_rewards.append(reward)
                valid_paths.append(path)
                valid_count += 1
                status = "✓"
            else:
                status = "✗"
            
            print(f"  Trial {trial+1:2d}: Reward={reward:6.0f} Time={elapsed:6.2f}s {status}")
            
        except Exception as e:
            print(f"  Trial {trial+1:2d}: FAILED - {str(e)}")
            elapsed = time.time() - start_time
            times.append(elapsed)
    
    # Calculate statistics
    if not valid_rewards:
        print(f"\n⚠ Warning: No valid solutions found in {num_trials} trials!")
        return {
            'algorithm': algorithm_name,
            'num_trials': num_trials,
            'valid_count': 0,
            'valid_rate': 0.0,
            'mean_reward': 0,
            'std_reward': 0,
            'min_reward': 0,
            'max_reward': 0,
            'best_path': None,
            'worst_path': None,
            'avg_time': np.mean(times) if times else 0,
            'std_time': np.std(times) if times else 0
        }
    
    best_idx = np.argmax(valid_rewards)
    worst_idx = np.argmin(valid_rewards)
    
    stats = {
        'algorithm': algorithm_name,
        'num_trials': num_trials,
        'valid_count': valid_count,
        'valid_rate': (valid_count / num_trials) * 100,
        'mean_reward': np.mean(valid_rewards),
        'std_reward': np.std(valid_rewards),
        'min_reward': np.min(valid_rewards),
        'max_reward': np.max(valid_rewards),
        'median_reward': np.median(valid_rewards),
        'best_path': valid_paths[best_idx],
        'worst_path': valid_paths[worst_idx],
        'avg_time': np.mean(times),
        'std_time': np.std(times),
        'all_rewards': valid_rewards
    }
    
    return stats


def print_statistics_report(stats: Dict, problem: OrienteeringProblem) -> None:
    """
    Print a detailed statistical report.
    """
    print("\n" + "="*80)
    print(f"STATISTICAL ANALYSIS: {stats['algorithm']}")
    print("="*80)
    
    # Calculate upper bound for context
    upper_bound, _ = calculate_upper_bound(problem)
    
    print(f"\nTrials: {stats['num_trials']}")
    print(f"Valid Solutions: {stats['valid_count']} ({stats['valid_rate']:.1f}%)")
    
    if stats['valid_count'] == 0:
        print("\n⚠ No valid solutions found!")
        return
    
    print(f"\n{'Metric':<25} {'Value':<20} {'% of Upper Bound'}")
    print("-" * 70)
    
    mean_pct = (stats['mean_reward'] / upper_bound * 100) if upper_bound > 0 else 0
    max_pct = (stats['max_reward'] / upper_bound * 100) if upper_bound > 0 else 0
    min_pct = (stats['min_reward'] / upper_bound * 100) if upper_bound > 0 else 0
    
    print(f"{'Mean Reward':<25} {stats['mean_reward']:<20.2f} {mean_pct:.1f}%")
    print(f"{'Std Dev':<25} {stats['std_reward']:<20.2f}")
    print(f"{'Median Reward':<25} {stats['median_reward']:<20.2f}")
    print(f"{'Min Reward':<25} {stats['min_reward']:<20.2f} {min_pct:.1f}%")
    print(f"{'Max Reward':<25} {stats['max_reward']:<20.2f} {max_pct:.1f}%")
    print(f"{'Range':<25} {stats['max_reward'] - stats['min_reward']:<20.2f}")
    print(f"\n{'Upper Bound':<25} {upper_bound:<20.2f} 100.0%")
    print(f"{'Avg Optimality Gap':<25} {100 - mean_pct:<20.1f}%")
    
    # Coefficient of variation (relative std dev)
    cv = (stats['std_reward'] / stats['mean_reward'] * 100) if stats['mean_reward'] > 0 else 0
    print(f"\n{'Coefficient of Variation':<25} {cv:.2f}%")
    print(f"  (Lower is better - indicates consistency)")
    
    print(f"\n{'Avg Time per Trial':<25} {stats['avg_time']:.3f}s")
    print(f"{'Std Dev Time':<25} {stats['std_time']:.3f}s")
    
    # Best and worst paths
    print(f"\nBest Path (Reward={stats['max_reward']:.0f}):")
    print(f"  {stats['best_path']}")
    print(f"\nWorst Path (Reward={stats['min_reward']:.0f}):")
    print(f"  {stats['worst_path']}")
    
    print("\n" + "="*80)


def compare_algorithms(
    problem: OrienteeringProblem,
    algorithms: Dict[str, Callable],
    num_trials: int = 10
) -> None:
    """
    Compare multiple algorithms statistically.
    
    Args:
        problem: The OP instance
        algorithms: Dict of {name: solver_function}
        num_trials: Number of trials per algorithm
    """
    all_stats = []
    
    for name, solver_func in algorithms.items():
        stats = run_multiple_trials(problem, solver_func, num_trials, name)
        all_stats.append(stats)
        print_statistics_report(stats, problem)
    
    # Comparison table
    print("\n" + "="*80)
    print("ALGORITHM COMPARISON")
    print("="*80)
    
    print(f"\n{'Algorithm':<25} {'Mean±Std':<20} {'Max':<10} {'Time(s)':<12} {'Valid%'}")
    print("-" * 80)
    
    # Sort by mean reward
    all_stats.sort(key=lambda x: x['mean_reward'], reverse=True)
    
    for stats in all_stats:
        if stats['valid_count'] > 0:
            mean_std = f"{stats['mean_reward']:.1f}±{stats['std_reward']:.1f}"
            print(f"{stats['algorithm']:<25} {mean_std:<20} {stats['max_reward']:<10.0f} "
                  f"{stats['avg_time']:<12.3f} {stats['valid_rate']:.0f}%")
        else:
            print(f"{stats['algorithm']:<25} {'N/A':<20} {'N/A':<10} "
                  f"{stats['avg_time']:<12.3f} 0%")
    
    print("\n" + "="*80)
    
    # Statistical significance tests (if multiple valid algorithms and scipy available)
    valid_stats = [s for s in all_stats if s['valid_count'] > 0]
    if len(valid_stats) >= 2:
        try:
            from scipy import stats as scipy_stats
            
            print("\nSTATISTICAL SIGNIFICANCE (t-test, p < 0.05)")
            print("-" * 80)
            
            for i in range(len(valid_stats)):
                for j in range(i + 1, len(valid_stats)):
                    alg1 = valid_stats[i]
                    alg2 = valid_stats[j]
                    
                    t_stat, p_value = scipy_stats.ttest_ind(alg1['all_rewards'], alg2['all_rewards'])
                    
                    if p_value < 0.05:
                        better = alg1['algorithm'] if alg1['mean_reward'] > alg2['mean_reward'] else alg2['algorithm']
                        print(f"  {alg1['algorithm']} vs {alg2['algorithm']}: "
                              f"p={p_value:.4f} → {better} is significantly better")
                    else:
                        print(f"  {alg1['algorithm']} vs {alg2['algorithm']}: "
                              f"p={p_value:.4f} → No significant difference")
            
            print("\n" + "="*80)
        except ImportError:
            print("\n(scipy not installed - skipping statistical significance tests)")
            print("Install with: pip install scipy")
            print("="*80)


def plot_convergence(rewards_over_time: List[float], algorithm_name: str = "Algorithm") -> None:
    """
    Plot reward convergence over iterations/time.
    
    Args:
        rewards_over_time: List of best rewards found at each iteration
        algorithm_name: Name for the plot
    """
    try:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 6))
        plt.plot(rewards_over_time, linewidth=2)
        plt.xlabel('Iteration', fontsize=12)
        plt.ylabel('Best Reward Found', fontsize=12)
        plt.title(f'Solution Quality Convergence: {algorithm_name}', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'convergence_{algorithm_name.replace(" ", "_")}.png', dpi=150)
        plt.close()
        print(f"Convergence plot saved to: convergence_{algorithm_name.replace(' ', '_')}.png")
    except ImportError:
        print("matplotlib not installed - skipping plot generation")


def plot_reward_distribution(all_stats: List[Dict], problem: OrienteeringProblem) -> None:
    """
    Plot box plot comparing reward distributions of different algorithms.
    """
    try:
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Prepare data
        data = []
        labels = []
        for stats in all_stats:
            if stats['valid_count'] > 0:
                data.append(stats['all_rewards'])
                labels.append(stats['algorithm'])
        
        if not data:
            print("No valid data to plot!")
            return
        
        # Create box plot
        bp = ax.boxplot(data, labels=labels, patch_artist=True)
        
        # Add upper bound line
        upper_bound, _ = calculate_upper_bound(problem)
        ax.axhline(y=upper_bound, color='r', linestyle='--', label=f'Upper Bound ({upper_bound:.0f})', linewidth=2)
        
        ax.set_ylabel('Reward', fontsize=12)
        ax.set_title('Reward Distribution Comparison', fontsize=14)
        ax.grid(True, alpha=0.3, axis='y')
        ax.legend(fontsize=10)
        
        # Color boxes
        colors = ['lightblue', 'lightgreen', 'lightyellow', 'lightcoral', 'plum']
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
        
        plt.xticks(rotation=15, ha='right')
        plt.tight_layout()
        plt.savefig('reward_distribution_comparison.png', dpi=150)
        plt.close()
        print("Distribution plot saved to: reward_distribution_comparison.png")
    except ImportError:
        print("matplotlib not installed - skipping plot generation")


if __name__ == "__main__":
    import sys
    
    # Example usage
    print("="*80)
    print("ORIENTEERING PROBLEM SOLUTION BENCHMARKING TOOL")
    print("="*80)
    
    if len(sys.argv) < 2:
        print("\nUsage: python benchmark_solution.py <problem_file> [num_trials]")
        print("\nExample:")
        print("  python benchmark_solution.py OP_Benchmark_Set/set_64_1/set_64_1_80.txt 20")
        sys.exit(1)
    
    problem_file = sys.argv[1]
    num_trials = int(sys.argv[2]) if len(sys.argv) >= 3 else 10
    
    # Load problem
    from orienteering.orienteering import OrienteeringProblem
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)
    
    print(f"\nProblem: {problem_file}")
    print(f"  Nodes: {problem.num_nodes}, Budget: {budget}")
    
    # Define baseline algorithm
    def greedy_solver(prob):
        path, reward = greedy_nearest_neighbor(prob)
        return path, reward
    
    # Run benchmark on greedy baseline
    stats = run_multiple_trials(problem, greedy_solver, num_trials, "Greedy Nearest Neighbor")
    print_statistics_report(stats, problem)
    
    print("\n" + "="*80)
    print("RECOMMENDATION:")
    print("="*80)
    print("\nTo benchmark your MCTS solution:")
    print("1. Import your MCTS solver function")
    print("2. Create a wrapper that takes OrienteeringProblem and returns (path, reward)")
    print("3. Call run_multiple_trials() with your solver")
    print("\nExample code:")
    print("""
    from MCTS.wu_uct_demo import run_wu_uct  # Your solver
    
    def my_mcts_solver(problem):
        result = run_wu_uct(problem, iterations=10000)
        path = result['path']
        reward = result['reward']
        return path, reward
    
    stats = run_multiple_trials(problem, my_mcts_solver, num_trials=10, 
                                 algorithm_name="WU-UCT MCTS")
    print_statistics_report(stats, problem)
    """)
