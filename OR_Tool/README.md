# OR-Tools Solver for Orienteering Problem

This directory contains an implementation using Google OR-Tools to solve Orienteering Problem instances from the benchmark sets.

## Overview

The orienteering problem is formulated as a Vehicle Routing Problem (VRP) with:
- **Single vehicle** (one tour)
- **Distance constraint** (budget limit)
- **Objective**: Maximize collected rewards (node scores)

## Installation

OR-Tools is already installed in the virtual environment. If you need to reinstall:

```bash
# Activate virtual environment
.venv\Scripts\activate

# Install OR-Tools
pip install ortools
```

## Usage

### Solve a Single Problem

```bash
python OR_Tool\or_tools_solver.py OP_Benchmark_Set\grid_sample\grid_10x10_medium_30.txt
```

### Solve All Problems in a Directory (Batch Mode)

```bash
python OR_Tool\or_tools_solver.py OP_Benchmark_Set\grid_sample --batch
```

### Set Time Limit

```bash
python OR_Tool\or_tools_solver.py OP_Benchmark_Set\grid_sample\grid_10x10_medium_30.txt --time-limit 60
```

### Quiet Mode (minimal output)

```bash
python OR_Tool\or_tools_solver.py OP_Benchmark_Set\grid_sample\grid_10x10_easy_20.txt --quiet
```

## Examples

### Test on Grid Problems (Recommended)

```bash
# Single grid problem
python OR_Tool\or_tools_solver.py OP_Benchmark_Set\grid_sample\grid_10x10_easy_20.txt

# Medium difficulty
python OR_Tool\or_tools_solver.py OP_Benchmark_Set\grid_sample\grid_10x10_medium_30.txt

# Long budget
python OR_Tool\or_tools_solver.py OP_Benchmark_Set\grid_sample\grid_10x10_long_50.txt

# All grid problems
python OR_Tool\or_tools_solver.py OP_Benchmark_Set\grid_sample --batch --time-limit 60
```

### Test on Other Benchmark Sets

```bash
# Grid patterns
python OR_Tool\or_tools_solver.py OP_Benchmark_Set\grid_patterns --batch --time-limit 60

# Parallel friendly problems
python OR_Tool\or_tools_solver.py OP_Benchmark_Set\parallel_friendly_v2\small --batch --time-limit 30

# Tsiligirides benchmark
python OR_Tool\or_tools_solver.py OP_Benchmark_Set\Tsiligirides_1 --batch --time-limit 60
```

## Output

The solver provides:
- **Path**: Sequence of visited nodes
- **Total Reward**: Sum of scores from visited nodes
- **Total Distance**: Distance traveled (must be ≤ budget)
- **Solve Time**: Time taken by OR-Tools
- **Validation**: Checks if solution is valid (budget satisfied, starts/ends at depot, no duplicates)

### Example Output

```
================================================================================
OR-TOOLS SOLUTION
================================================================================

Path: 0 -> 66 -> 77 -> 88 -> 89 -> 100 -> 101 -> 112 -> 113 -> 114 -> ... -> 1
Total Reward: 303.00
Total Distance: 29.8863 / 30.0000
Distance Used: 99.6%
Nodes Visited: 28

Solve Time: 60.00 seconds
Status: SOLVED

--------------------------------------------------------------------------------
VALIDATION
--------------------------------------------------------------------------------
✓ Budget satisfied: 29.8863 <= 30.0000
✓ Path starts at node 0 (start depot)
✓ Path ends at node 1 (end depot)
✓ No duplicate nodes in path

✅ Solution is VALID
================================================================================
```

## Algorithm Details

OR-Tools uses advanced metaheuristics including:
- **Guided Local Search (GLS)**: Default metaheuristic
- **Path Cheapest Arc**: Initial solution construction
- **Constraint propagation**: Enforces distance budget

The solver formulates the problem as a routing problem with:
1. Distance dimension with budget constraint
2. Optional node visits (disjunctions)
3. Node rewards to maximize

## Comparison with MCTS

Use this OR-Tools solver to:
- **Generate reference solutions** for your MCTS implementations
- **Benchmark quality**: Compare MCTS rewards vs OR-Tools
- **Verify correctness**: Ensure MCTS finds valid paths
- **Set time limits**: Compare solution quality at different time limits

## Performance Tips

1. **Adjust time limit**: Longer times may find better solutions
   - Small problems (< 100 nodes): 10-30 seconds
   - Medium problems (100-500 nodes): 30-120 seconds
   - Large problems (> 500 nodes): 120-300 seconds

2. **Batch processing**: Use `--batch` to test entire benchmark sets

3. **Compare methods**: Run both OR-Tools and your MCTS implementation on the same problems

## Files

- `or_tools_solver.py`: Main solver implementation
- `batch_test.py`: Script for comprehensive benchmark testing
- `README.md`: This file

## References

- [Google OR-Tools Documentation](https://developers.google.com/optimization)
- [Vehicle Routing Problem Guide](https://developers.google.com/optimization/routing)
- [Orienteering Problem](https://en.wikipedia.org/wiki/Orienteering_problem)
