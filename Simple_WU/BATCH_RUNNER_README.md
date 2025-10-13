# Batch Runner for Benchmark Datasets

This script (`run_parallel_friendly_batch.py`) allows you to run Simple WU-UCT on multiple problem files from two benchmark sets:
- **parallel_friendly_v2**: Problems designed for parallel algorithms
- **grid_patterns**: Problems with specific spatial reward patterns

## Default Test Files

### Parallel Friendly Dataset (default)

One representative file from each of 6 categories:

1. **Clustered**: `clustered_c4_s5_sp8_32.txt` - Problems with clustered reward patterns
2. **Corridors**: `corridors_n4_l20_w3_24.txt` - Corridor-like problem structures
3. **Dense Grid**: `dense_20x20_r10_28.txt` - Dense grid problems
4. **Islands**: `islands_n6_s5_b30_28.txt` - Island-like problem structures
5. **Sparse Grid**: `sparse_30x30_d50_44.txt` - Sparse grid problems
6. **XLarge**: `xlarge_40x40_r0_84.txt` - Extra large problem instances

### Grid Patterns Dataset

One representative file from each of 10 pattern types:

1. **Corners High**: `grid_corners_b30.txt` - High rewards at corners
2. **Center High**: `grid_center_b30.txt` - High rewards in center
3. **Edges High**: `grid_edges_b30.txt` - High rewards on edges
4. **Diagonal High**: `grid_diagonal_b30.txt` - High rewards along diagonals
5. **Gradient Horizontal**: `grid_grad_horiz_b30.txt` - Gradual increase across grid
6. **Quadrants**: `grid_quadrants_b30.txt` - Different rewards per quarter
7. **Checkerboard**: `grid_checkerboard_b30.txt` - Alternating high/low pattern
8. **Ring**: `grid_ring_b30.txt` - Ring of high rewards around center
9. **Clustered**: `grid_clustered_b30.txt` - Rewards clustered near specific points
10. **Random**: `grid_random_b30.txt` - Baseline random distribution

## Usage

### Basic Usage (Default Settings)

Run parallel_friendly dataset with default settings (10,000 iterations, 4 workers):

```bash
cd Simple_WU
python run_parallel_friendly_batch.py
```

Or from the project root:

```bash
python Simple_WU/run_parallel_friendly_batch.py
```

### Run Grid Patterns Dataset

```bash
python run_parallel_friendly_batch.py --dataset grid_patterns
```

### Custom Iterations and Workers

```bash
python run_parallel_friendly_batch.py --max-iterations 20000 --num-workers 8
```

Run grid patterns with custom settings:

```bash
python run_parallel_friendly_batch.py --dataset grid_patterns --max-iterations 20000 --num-workers 8
```

### Time-Limited Runs

Run each problem for a maximum of 60 seconds:

```bash
python run_parallel_friendly_batch.py --max-time 60
```

Or for grid patterns:

```bash
python run_parallel_friendly_batch.py --dataset grid_patterns --max-time 60
```

### Verbose Output

Get detailed output for each problem:

```bash
python run_parallel_friendly_batch.py --verbose
```

### Custom Files

Run on specific files instead of the defaults:

```bash
python run_parallel_friendly_batch.py --files \
    OP_Benchmark_Set/parallel_friendly_v2/clustered/clustered_c4_s4_sp6_19.txt \
    OP_Benchmark_Set/parallel_friendly_v2/corridors/corridors_n3_l15_w2_18.txt \
    OP_Benchmark_Set/parallel_friendly_v2/dense_grid/dense_15x15_r0_15.txt
```

Or for grid patterns:

```bash
python run_parallel_friendly_batch.py --files \
    OP_Benchmark_Set/grid_patterns/grid_corners_b20.txt \
    OP_Benchmark_Set/grid_patterns/grid_center_b20.txt \
    OP_Benchmark_Set/grid_patterns/grid_edges_b20.txt
```

### Custom Output Directory

Save results to a specific directory:

```bash
python run_parallel_friendly_batch.py --output-dir results/my_experiment
```

## Command-Line Options

- `--dataset`: Dataset to use: `parallel_friendly` or `grid_patterns` (default: `parallel_friendly`)
- `--files`: Specific problem files to test (relative to project root)
- `--max-iterations`: Maximum number of iterations per problem (default: 10000)
- `--max-time`: Maximum time in seconds per problem (optional)
- `--num-workers`: Number of unified workers (default: 4)
- `--exploration-constant`: UCT exploration constant (default: 1.414)
- `--verbose`: Enable verbose output for each problem
- `--output-dir`: Directory to save results (default: Simple_WU/)

## Output

The script produces:

1. **Console Output**: Progress and summary statistics
2. **Results File**: Detailed results saved to `Simple_WU/results/batch_results_TIMESTAMP.txt`

All output files are automatically saved to the `Simple_WU/results/` directory.

### Example Output - Parallel Friendly Dataset

```
================================================================================
Simple WU-UCT Batch Run - Parallel Friendly Dataset
================================================================================
Test files: 6
Max iterations per file: 10000
Number of workers: 4
Exploration constant: 1.414
================================================================================

[1/6] Running: clustered_c4_s5_sp8_32.txt
--------------------------------------------------------------------------------
✓ Completed: Reward=245, Time=12.45s

[2/6] Running: corridors_n4_l20_w3_24.txt
--------------------------------------------------------------------------------
✓ Completed: Reward=187, Time=8.32s

...

================================================================================
BATCH RUN SUMMARY
================================================================================
Total problems: 6
Successful runs: 6
Failed runs: 0

Problem                                       Nodes   Reward   Time(s)
--------------------------------------------------------------------------------
clustered_c4_s5_sp8_32.txt                   120     245      12.45
corridors_n4_l20_w3_24.txt                   93      187      8.32
dense_20x20_r10_28.txt                       156     312      15.67
islands_n6_s5_b30_28.txt                     108     221      10.89
sparse_30x30_d50_44.txt                      198     398      18.34
xlarge_40x40_r0_84.txt                       402     567      25.11
--------------------------------------------------------------------------------
Total execution time: 90.78s
Average time per problem: 15.13s
Total reward collected: 1930
```

### Example Output - Grid Patterns Dataset

```
================================================================================
Simple WU-UCT Batch Run - Grid Patterns Dataset
================================================================================
Test files: 10
Max iterations per file: 10000
Number of workers: 4
Exploration constant: 1.414
================================================================================

[1/10] Running: grid_corners_b30.txt
--------------------------------------------------------------------------------
✓ Completed: Reward=412, Time=8.21s

[2/10] Running: grid_center_b30.txt
--------------------------------------------------------------------------------
✓ Completed: Reward=356, Time=7.89s

...

================================================================================
BATCH RUN SUMMARY
================================================================================
Total problems: 10
Successful runs: 10
Failed runs: 0

Problem                                       Nodes   Reward   Time(s)
--------------------------------------------------------------------------------
grid_corners_b30.txt                         100     412      8.21
grid_center_b30.txt                          100     356      7.89
grid_edges_b30.txt                           100     445      8.56
grid_diagonal_b30.txt                        100     398      8.34
grid_grad_horiz_b30.txt                      100     321      7.92
grid_quadrants_b30.txt                       100     367      8.11
grid_checkerboard_b30.txt                    100     289      7.65
grid_ring_b30.txt                            100     378      8.45
grid_clustered_b30.txt                       100     401      8.23
grid_random_b30.txt                          100     298      7.78
--------------------------------------------------------------------------------
Total execution time: 81.14s
Average time per problem: 8.11s
Total reward collected: 3665
```

## Quick Reference

See `DATASETS_QUICK_REF.md` for a quick overview of available datasets and commands.

## Comparing Datasets

You can run both datasets and compare results:

```bash
# Run parallel_friendly
python run_parallel_friendly_batch.py --dataset parallel_friendly --max-iterations 10000

# Run grid_patterns
python run_parallel_friendly_batch.py --dataset grid_patterns --max-iterations 10000
```

The grid_patterns dataset is particularly useful for:
- Testing algorithm performance on structured reward distributions
- Evaluating how well the algorithm handles different spatial patterns
- Comparing against known optimal solutions for geometric patterns

The parallel_friendly dataset is better for:
- Testing scalability and parallel performance
- Evaluating performance on larger, more complex problem instances
- Benchmarking against other parallel MCTS implementations

## Notes

- Results are timestamped and saved automatically
- The script handles file path resolution from the project root
- Failed runs are reported but don't stop the batch execution
- Tree statistics (nodes, depth, visits) are included in the detailed results file
- Grid patterns typically run faster due to smaller problem sizes (100 nodes vs 100-400+ nodes)
- Both datasets use budget constraints suitable for testing (b20-b40 range)
