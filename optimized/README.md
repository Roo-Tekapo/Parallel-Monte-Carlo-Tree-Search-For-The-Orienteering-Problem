# Optimized MCTS Package

This folder contains optimized implementations and examples for Monte Carlo Tree Search applied to the Orienteering Problem.

## Files Overview

### Core Implementation Files
- **`optimized_simulation_strategies.py`** - Various simulation strategies (greedy, epsilon-greedy, etc.)
- **`optimized_mcts.py`** - Main optimized MCTS with caching and parallel support
- **`adaptive_mcts.py`** - Adaptive parameters and early stopping
- **`__init__.py`** - Package initialization and exports

### Example and Test Files
- **`run_simulation_strategies.py`** - Compare all simulation strategies with performance stats
- **`custom_simulation_example.py`** - How to use strategies with your existing MCTS
- **`test_individual_strategies.py`** - Test individual strategy behavior and consistency

### Documentation
- **`MCTS_OPTIMIZATION_GUIDE.md`** - Comprehensive guide to all optimization techniques
- **`README.md`** - This file

## Quick Start

### 1. Basic Usage
```python
from optimized import OptimizedMCTS
from orienteering.orienteering import OrienteeringProblem

# Load your problem
nodes, budget = OrienteeringProblem.load_problem('../OP_Benchmark_Set/sample/sample_6_small.txt')
problem = OrienteeringProblem(nodes, budget)

# Use optimized MCTS
solver = OptimizedMCTS(problem, iterations=5000, simulation_strategy="epsilon_greedy")
result = solver.run(verbose=True)
```

### 2. Run Examples from the optimized folder
```bash
# Compare all simulation strategies
python3 run_simulation_strategies.py

# Test individual strategies
python3 test_individual_strategies.py

# Custom MCTS integration
python3 custom_simulation_example.py
```

### 3. Available Simulation Strategies
- **`"greedy"`** - Always picks best reward/distance ratio (fast, consistent)
- **`"epsilon_greedy"`** - Mix of greedy (80%) and random (20%) (recommended)
- **`"heavy"`** - Multiple rollouts per simulation (slower, more accurate)
- **`"early_termination"`** - Limits simulation depth (faster)
- **`"random"`** - Original random simulation (baseline)

### 4. Advanced Features
```python
from optimized import AdaptiveMCTS, ParallelMCTS

# Adaptive MCTS with early stopping
adaptive_solver = AdaptiveMCTS(
    problem,
    max_iterations=10000,
    time_limit=30.0,  # Stop after 30 seconds
    simulation_strategy="epsilon_greedy"
)

# Parallel MCTS
parallel_solver = ParallelMCTS(
    problem,
    iterations=20000,
    num_threads=4,
    simulation_strategy="epsilon_greedy"
)
```

## Performance Tips

1. **Start with epsilon_greedy** - Best balance of quality and speed
2. **Use caching** - Automatically included in optimized implementations
3. **Parallel for large problems** - Use ParallelMCTS for 10k+ iterations
4. **Adaptive for unknown problems** - Use AdaptiveMCTS when you're unsure about iteration count

## Running from Parent Directory

If you want to run these examples from the main project directory:

```bash
# From main project directory
python3 -m optimized.run_simulation_strategies
python3 -m optimized.test_individual_strategies
python3 -m optimized.custom_simulation_example
```

## Import from Parent Directory

```python
# From parent directory
from optimized import OptimizedMCTS, AdaptiveMCTS, ParallelMCTS

# Or specific strategies
from optimized.optimized_simulation_strategies import OptimizedSimulationStrategies
```
