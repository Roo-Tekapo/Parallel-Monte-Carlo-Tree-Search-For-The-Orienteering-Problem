# Results Generation Tools

This directory contains tools for running comprehensive benchmarks across multiple MCTS algorithms and OR-Tools on orienteering problem datasets.

## Quick Start

### Installation

First, ensure you have the required dependencies:

```bash
pip install pandas openpyxl
```

### Basic Usage

```bash
# Run all algorithms on the sample dataset
python run_benchmark.py --dataset sample --algorithms all

# Run specific algorithms on a specific dataset
python run_benchmark.py --dataset grid_sample --algorithms uct vl --iterations 10000

# Run with time limit instead of iterations
python run_benchmark.py --dataset set_64_1 --algorithms all --max-time 60

# Quick test on limited problems
python run_benchmark.py --dataset all --algorithms all --limit 5
```

## Algorithms

The benchmark runner supports the following algorithms:

1. **UCT** (`uct`) - Single-threaded Upper Confidence Tree
2. **Simple_WU** (`simple_wu`) - Simplified WU-UCT with unified workers
3. **VL** (`vl`) - Virtual Loss parallel MCTS
4. **OR-Tools** (`ortools`) - Google OR-Tools optimization solver

## Available Datasets

The benchmark runner can test on the following datasets from `OP_Benchmark_Set/`:

- `grid_sample` - Grid-based sample problems
- `grid_patterns` - Grid problems with patterns
- `parallel_friendly_v2` - Problems designed for parallel algorithms
- `sample` - General sample problems
- `set_64_1` - 64-node problems
- `set_100_1` - 100-node problems
- `set_1000_1` - 1000-node problems
- `Tsiligirides_1` - Classic Tsiligirides benchmark problems
- `all` - Run on all datasets

## Command Line Options

```
--dataset, -d           Dataset name or 'all' (default: sample)
--algorithms, -a        Algorithms to run (default: all)
--iterations, -i        Max iterations for MCTS (default: 10000)
--max-time, -t          Max time in seconds (overrides iterations)
--workers, -w           Number of parallel workers (default: 4)
--vl-value             Virtual loss penalty value (default: 1.0)
--ortools-time         Time limit for OR-Tools (default: 30s)
--output, -o           Output filename (default: auto-generated)
--output-dir           Output directory (default: results_gen/outputs)
--format               Output format: excel, json, or both (default: excel)
--quiet, -q            Suppress progress output
--limit                Limit number of problems to test
```

## Examples

### Example 1: Compare all algorithms on sample dataset

```bash
python run_benchmark.py --dataset sample --algorithms all --iterations 5000
```

This will run UCT, Simple_WU, VL, and OR-Tools on all problems in the sample dataset.

### Example 2: Test parallel algorithms with different worker counts

```bash
# Test with 4 workers
python run_benchmark.py --dataset grid_sample --algorithms simple_wu vl --workers 4 --output results_4w.xlsx

# Test with 8 workers
python run_benchmark.py --dataset grid_sample --algorithms simple_wu vl --workers 8 --output results_8w.xlsx
```

### Example 3: Quick comparison with time limit

```bash
python run_benchmark.py --dataset set_64_1 --algorithms all --max-time 30 --limit 10
```

This runs each algorithm for maximum 30 seconds on the first 10 problems from set_64_1.

### Example 4: OR-Tools only on all datasets

```bash
python run_benchmark.py --dataset all --algorithms ortools --ortools-time 60 --output ortools_full.xlsx
```

### Example 5: Export to both Excel and JSON

```bash
python run_benchmark.py --dataset parallel_friendly_v2 --algorithms all --format both
```

## Output Format

The script generates an Excel file (or JSON) with the following structure:

### Sheets in Excel Output

1. **All Results** - Complete results for all runs
2. **Successful Runs** - Only successful algorithm runs
3. **Algorithm Summary** - Statistical summary by algorithm (mean, std, min, max)
4. **Failed Runs** - Runs that encountered errors

### Result Columns

For MCTS algorithms (UCT, Simple_WU, VL):
- `algorithm` - Algorithm name
- `problem_file` - Problem filename
- `dataset` - Dataset name
- `num_nodes` - Number of nodes in problem
- `budget` - Distance budget
- `num_workers` - Number of parallel workers (if applicable)
- `iterations` - Actual iterations performed
- `elapsed_time` - Execution time in seconds
- `best_path` - Best path found
- `path_length` - Number of nodes in path
- `normalized_reward` - Normalized reward value
- `raw_reward` - Raw reward (sum of node scores)
- `total_cost` - Total distance of path
- `budget_used_pct` - Percentage of budget used
- `success` - Whether run succeeded
- `error` - Error message if failed

For OR-Tools:
- Similar columns plus `solver_status` (optimization status)

## Tips

1. **Start Small**: Use `--limit 5` to test on a small subset first
2. **Time vs Iterations**: Use `--max-time` for fair comparison across problems of different sizes
3. **Worker Count**: Test different `--workers` values to find optimal parallelization
4. **VL Tuning**: Experiment with `--vl-value` between 0.5 and 3.0
5. **Output Organization**: Use descriptive `--output` names for different experiment configurations

## Troubleshooting

### Import Errors

If you see import errors, make sure you're running from the project root or the script is finding the modules:

```bash
cd /path/to/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem
python results_gen/run_benchmark.py --dataset sample --algorithms all
```

### Missing Dependencies

```bash
pip install pandas openpyxl ortools
```

### Out of Memory

For large datasets (set_1000_1), consider:
- Using `--limit` to test on subset
- Reducing `--iterations` or using `--max-time`
- Running algorithms separately

## Output Location

By default, results are saved to `results_gen/outputs/` with timestamped filenames like:
- `benchmark_results_20231028_143052.xlsx`

Specify custom location with `--output-dir` and `--output`.

## Analyzing Results

### Automated Analysis

Use the included analyzer script to generate summary reports:

```bash
# Analyze results and print to console
python analyze_results.py outputs/benchmark_results_20231028_143052.xlsx

# Save analysis to text file
python analyze_results.py outputs/benchmark_results_20231028_143052.xlsx --output analysis_report.txt
```

The analyzer provides:
- **Algorithm Comparison**: Statistical comparison of all algorithms
- **Dataset Performance**: How each algorithm performs on different datasets
- **Efficiency Analysis**: Reward per second metrics
- **Parallel Speedup**: Analysis of parallel algorithm performance
- **Top Solutions**: Best solutions found across all runs

### Manual Analysis

The Excel output includes summary statistics. You can:

1. Compare algorithms by average reward
2. Analyze time vs. quality tradeoffs
3. Identify which problems are challenging for which algorithms
4. Study budget utilization patterns

For deeper analysis, use the JSON output format with your own analysis scripts.
