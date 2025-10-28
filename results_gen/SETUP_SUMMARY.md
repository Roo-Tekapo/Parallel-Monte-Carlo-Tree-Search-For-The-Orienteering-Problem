# Results Generation System - Complete Setup

This folder contains a comprehensive benchmarking system for testing multiple MCTS algorithms and OR-Tools on orienteering problem datasets.

## Files Created

### Core Scripts

1. **run_benchmark.py** - Main benchmark runner
   - Runs UCT, Simple_WU, VL, and OR-Tools algorithms
   - Supports multiple datasets and configuration options
   - Exports results to Excel or JSON

2. **quick_test.py** - Quick verification script
   - Tests each algorithm once on a small problem
   - Useful for verifying everything works before full runs
   - Fast (~30 seconds)

3. **analyze_results.py** - Results analyzer
   - Loads Excel results and generates summary statistics
   - Compares algorithms across multiple metrics
   - Can save analysis reports to text files

4. **presets.sh** - Preset configurations
   - Interactive menu with common benchmark scenarios
   - Quick access to useful configurations

### Documentation

5. **README.md** - Complete usage guide
   - Installation instructions
   - Command-line options
   - Examples and tips

6. **SETUP_SUMMARY.md** - This file

### Directories

7. **outputs/** - Results storage
   - All benchmark results saved here
   - .gitignore configured to ignore output files

## Quick Start

### 1. Install Dependencies

```bash
pip install pandas openpyxl
```

### 2. Verify Setup

```bash
cd results_gen
python quick_test.py
```

This will test each algorithm once. If all tests pass, you're ready to go!

### 3. Run Your First Benchmark

```bash
# Simple test on sample dataset
python run_benchmark.py --dataset sample --algorithms all --iterations 5000
```

This will run all algorithms on the sample dataset and create an Excel file in `outputs/`.

### 4. Analyze Results

```bash
# Find your results file
ls -lt outputs/

# Analyze it
python analyze_results.py outputs/benchmark_results_TIMESTAMP.xlsx
```

## Common Use Cases

### Scenario 1: Compare All Algorithms

```bash
python run_benchmark.py --dataset grid_sample --algorithms all --iterations 10000
```

### Scenario 2: Test Different Worker Counts

```bash
python run_benchmark.py --dataset sample --algorithms vl --workers 2 --output vl_2w.xlsx
python run_benchmark.py --dataset sample --algorithms vl --workers 4 --output vl_4w.xlsx
python run_benchmark.py --dataset sample --algorithms vl --workers 8 --output vl_8w.xlsx
```

### Scenario 3: Quick Comparison with Time Limits

```bash
python run_benchmark.py --dataset set_64_1 --algorithms all --max-time 30 --limit 10
```

### Scenario 4: Comprehensive Test

```bash
python run_benchmark.py --dataset all --algorithms all --iterations 10000
```

**Warning**: This may take several hours!

## Algorithm Descriptions

- **UCT**: Single-threaded Upper Confidence Tree (baseline)
- **Simple_WU**: Simplified WU-UCT with unified workers
- **VL**: Virtual Loss parallel MCTS
- **OR-Tools**: Google OR-Tools optimization solver (exact/near-exact)

## Tips and Best Practices

### Testing Strategy

1. **Start with quick_test.py** to verify everything works
2. **Use --limit 5** for initial parameter exploration
3. **Run small datasets first** (sample, grid_sample)
4. **Scale up gradually** to larger datasets

### Performance Tuning

- **Iterations**: Start with 5000-10000, increase if needed
- **Workers**: Test 2, 4, 8 workers to find optimal parallelization
- **Time Limits**: Use `--max-time` for fair comparison across problem sizes
- **VL Value**: Experiment with 0.5, 1.0, 2.0 for Virtual Loss

### Output Management

- Results are automatically timestamped
- Use descriptive `--output` names for different experiments
- Excel files include multiple sheets for easy analysis
- Use `--format both` to get both Excel and JSON

### Memory Management

For very large datasets (set_1000_1):
- Use `--limit` to test subsets
- Reduce `--iterations` or use `--max-time`
- Run algorithms separately instead of all at once

## Troubleshooting

### Import Errors

Make sure you're in the project root or the script can find modules:

```bash
cd /path/to/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem
python results_gen/run_benchmark.py --dataset sample --algorithms all
```

### Missing Dependencies

```bash
pip install pandas openpyxl ortools
```

### Algorithm Fails

Check the "Failed Runs" sheet in the Excel output for error details.

### Slow Performance

- Reduce iterations: `--iterations 1000`
- Use time limits: `--max-time 10`
- Test fewer problems: `--limit 5`
- Run algorithms separately

## Example Workflow

Here's a complete workflow from setup to analysis:

```bash
# 1. Install dependencies
pip install pandas openpyxl

# 2. Navigate to results_gen
cd results_gen

# 3. Quick test
python quick_test.py

# 4. Run benchmark on sample dataset
python run_benchmark.py --dataset sample --algorithms all --iterations 5000

# 5. Check outputs
ls -lt outputs/

# 6. Analyze results
python analyze_results.py outputs/benchmark_results_*.xlsx --output analysis.txt

# 7. View analysis
cat analysis.txt
```

## Advanced Usage

### Custom Dataset Selection

```bash
# Run on specific dataset
python run_benchmark.py --dataset Tsiligirides_1 --algorithms all

# Run on all datasets
python run_benchmark.py --dataset all --algorithms ortools
```

### Algorithm-Specific Options

```bash
# Tune Virtual Loss value
python run_benchmark.py --dataset sample --algorithms vl --vl-value 1.5

# Increase OR-Tools time limit
python run_benchmark.py --dataset sample --algorithms ortools --ortools-time 60

# More parallel workers
python run_benchmark.py --dataset sample --algorithms simple_wu --workers 8
```

### Batch Experiments

Use the preset menu for common configurations:

```bash
bash presets.sh
```

Or create your own batch script:

```bash
#!/bin/bash
for workers in 2 4 8; do
    python run_benchmark.py --dataset grid_sample --algorithms vl \
        --workers $workers --output "vl_${workers}w.xlsx"
done
```

## Output Structure

### Excel File Sheets

1. **All Results**: Complete data for every run
2. **Successful Runs**: Only successful algorithm runs
3. **Algorithm Summary**: Statistical summary (mean, std, min, max)
4. **Failed Runs**: Error information for debugging

### Key Columns

- `algorithm`: Algorithm name
- `problem_file`: Problem filename
- `dataset`: Dataset name
- `raw_reward`: Total reward collected
- `elapsed_time`: Execution time in seconds
- `budget_used_pct`: Percentage of distance budget used
- `path_length`: Number of nodes in solution path

## Next Steps

1. Run `quick_test.py` to verify setup
2. Try a small benchmark run
3. Analyze the results
4. Scale up to larger experiments
5. Compare different configurations

For detailed options and examples, see `README.md`.

## Support

If you encounter issues:

1. Check that all dependencies are installed
2. Verify you're running from the correct directory
3. Look at the "Failed Runs" sheet in Excel output
4. Check the traceback in the error column
5. Try running `quick_test.py` to isolate the problem

## Credits

This benchmarking system integrates:
- UCT implementation from `UCT/`
- Simple WU-UCT from `Simple_WU/`
- Virtual Loss MCTS from `VL/`
- OR-Tools solver from `OR_Tool/`
- Benchmark datasets from `OP_Benchmark_Set/`
