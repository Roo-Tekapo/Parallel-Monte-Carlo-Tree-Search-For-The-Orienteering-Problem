# Testing Solution Tools

This folder contains comprehensive validation and testing tools for Orienteering Problem solutions.

## 📁 Files

- **`validate_solution.py`** - Validates individual solutions and checks constraints
- **`benchmark_solution.py`** - Runs statistical analysis across multiple trials
- **`solve_optimal.py`** - Finds optimal or near-optimal solutions
- **`compare_methods.py`** - Compares MCTS vs Optimal vs Greedy
- **`VALIDATION_GUIDE.md`** - Detailed guide on validation strategies
- **`TESTING_SUMMARY.md`** - Summary of all testing capabilities and results

## 🚀 Quick Start

### Validate a Single Solution
```bash
python testing_solution/validate_solution.py OP_Benchmark_Set/set_64_1/set_64_1_80.txt
```

### Benchmark with Multiple Trials
```bash
python testing_solution/benchmark_solution.py OP_Benchmark_Set/set_64_1/set_64_1_80.txt 10
```

### Find Optimal Path
```bash
python testing_solution/solve_optimal.py OP_Benchmark_Set/set_64_1/set_64_1_80.txt
```

### Compare All Methods
```bash
python testing_solution/compare_methods.py OP_Benchmark_Set/set_64_1/set_64_1_80.txt
```

## 📖 Documentation

See `TESTING_SUMMARY.md` for complete documentation and examples.
