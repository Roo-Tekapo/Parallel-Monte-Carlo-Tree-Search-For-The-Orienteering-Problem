# UCT (Upper Confidence bounds applied to Trees) Implementation

This package contains a single-threaded UCT implementation for the Orienteering Problem.

## Files Overview

### Core Implementation
- `uct_single_thread.py` - Single-threaded UCT implementation (UCTNode, UCTSingleThread)
- `orienteering_adapter.py` - Adapter for orienteering problem variants (traditional/no-end)
- `main.py` - Command-line interface
- `__init__.py` - Package initialization

## Algorithm

### Single-threaded UCT
Classic Upper Confidence bounds applied to Trees algorithm that performs:
1. **Selection**: Traverse tree using UCT formula until reaching a leaf
2. **Expansion**: Add a new child node by trying an untried action
3. **Simulation**: Perform random rollout from the new node
4. **Backpropagation**: Update visit counts and rewards up the tree

## Key Features

### UCT Node
- State management for orienteering problem
- UCT selection with exploration constant
- Parent-child relationship tracking
- Visit count and reward accumulation

### UCT Algorithm
- Configurable exploration constant
- Support for time-based or iteration-based termination
- Normalized reward handling
- Statistics tracking

## Usage

### Command Line Interface

```bash
# Run UCT with default settings (10,000 iterations)
python main.py --problem-file ../OP_Benchmark_Set/set_64_1/set_64_1_80.txt --verbose

# Run UCT with 100,000 iterations
python main.py --problem-file ../OP_Benchmark_Set/grid_sample/grid_10x10_hard_40.txt \
               --max-iterations 100000 \
               --verbose

# Run UCT with time limit (60 seconds)
python main.py --problem-file ../OP_Benchmark_Set/set_64_1/set_64_1_80.txt \
               --max-time 60 \
               --verbose

# Run UCT with custom exploration constant and output file
python main.py --problem-file ../OP_Benchmark_Set/set_64_1/set_64_1_80.txt \
               --max-iterations 50000 \
               --exploration-constant 1.41 \
               --output-file results.txt \
               --verbose

# Run with no-end variant (no end node requirement)
python main.py --problem-file ../OP_Benchmark_Set/grid_sample/grid_10x10_hard_40.txt \
               --use-no-end \
               --verbose
```

### Programmatic Usage

```python
from UCT import UCTSingleThread
from UCT.orienteering_adapter import OrienteeringProblem

# Load problem
nodes, budget = OrienteeringProblem.load_problem("problem.txt")
problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)

# Run UCT
uct = UCTSingleThread(problem, iterations=10000)
best_state = uct.run()

print(f"Best path: {best_state.get_path()}")
print(f"Reward: {best_state.get_reward()}")
print(f"Cost: {best_state.get_cost()}")
```

## Parameters

- `--problem-file` / `-p`: Path to orienteering problem file (required)
- `--max-iterations`: Maximum number of iterations (default: 10000)
- `--max-time`: Maximum time in seconds (optional, overrides max-iterations)
- `--exploration-constant`: UCT exploration parameter (default: √2)
- `--max-distance`: Maximum distance limit for simulations (optional)
- `--use-no-end` / `-no-end`: Use no-end orienteering variant
- `--verbose`: Enable detailed progress output
- `--output-file`: Save results to file (saved in uct-output/ by default)

## Output

Results are automatically saved to the `uct-output/` folder with filenames in the format:
```
uct_<problem_name>_<iterations>.txt
```

Example output file content:
```
# UCT Results
# Problem: OP_Benchmark_Set/grid_sample/grid_10x10_hard_40.txt
# Iterations: 10000
# Exploration constant: 1.4142135623730951
# Execution time: 2.45s
#
Path= 0 15 25 35 45 46 47 48 49 39 29 19 9 99
Normalized_Reward= 0.8523
Raw_Reward= 1140
Cost= 39.5
```

## Differences from Original MCTS

This UCT implementation improves upon the original MCTS base:

1. **Better Structure**: Clear separation of UCT logic from orienteering specifics
2. **Orienteering Adapter**: Support for both traditional and no-end variants
3. **Comprehensive CLI**: Easy-to-use command-line interface for benchmarking
4. **Statistics**: Detailed tracking of tree growth and performance
5. **Documentation**: Clear code documentation and usage examples