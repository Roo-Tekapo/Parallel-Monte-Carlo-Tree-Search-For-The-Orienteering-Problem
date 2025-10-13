# UCT (Upper Confidence bounds applied to Trees) Implementation

This package contains both single-threaded UCT and parallel WU-UCT (Work Unit UCT) implementations for the Orienteering Problem, based on the MCTS foundation from the main MCTS package.

## Files Overview

### Core Implementation
- `uct_single_thread.py` - Single-threaded UCT implementation (UCTNode, UCTSingleThread)

### Modular WU-UCT Components  
- `work_units.py` - Data structures for worker communication (WorkUnit, SimulationResult)
- `expansion_worker.py` - Tree management and coordination (WUUCTExpansionWorker)
- `simulation_worker.py` - Parallel simulation workers (WUUCTSimulationWorker, SimulationWorkerPool)
- `wu_uct_coordinator.py` - Main algorithm coordinator (WUUCT, run_wu_uct)

### Interface and Testing
- `main.py` - Command-line interface for both algorithms
- `test_modular.py` - Testing suite for modular components
- `__init__.py` - Package initialization

## Algorithms

### Single-threaded UCT
Classic Upper Confidence bounds applied to Trees algorithm that performs:
1. **Selection**: Traverse tree using UCT formula until reaching a leaf
2. **Expansion**: Add a new child node by trying an untried action
3. **Simulation**: Perform random rollout from the new node
4. **Backpropagation**: Update visit counts and rewards up the tree

### WU-UCT (Work Unit UCT)
Parallel version where:
- **1 Expansion Worker**: Manages tree structure (selection & expansion)
- **N Simulation Workers**: Perform rollouts in parallel
- **Work Units**: Represent leaf nodes that need simulation
- **Coordination**: Thread-safe communication via queues

## Key Features

### UCT Node
- State management for orienteering problem
- UCT selection with exploration constant
- Parent-child relationship tracking
- Visit count and reward accumulation

### WU-UCT Architecture
- **Thread-safe**: Uses locks and queues for coordination
- **Scalable**: Configurable number of simulation workers
- **Efficient**: Work unit distribution prevents idle workers
- **Robust**: Proper cleanup and error handling

## Usage

### Command Line Interface

```bash
# Run WU-UCT with 3 simulation workers
python3 main.py --problem-file ../OP_Benchmark_Set/set_64_1/set_64_1_80.txt \
                --algorithm wu-uct \
                --max-iterations 100000 \
                --simulation-workers 3 \
                --verbose

# Run single-threaded UCT
python3 main.py --problem-file ../OP_Benchmark_Set/set_64_1/set_64_1_80.txt \
                --algorithm uct \
                --max-iterations 100000 \
                --verbose
```

python3 main.py --problem-file ../OP_Benchmark_Set/set_64_1/set_64_1_80.txt --algorithm wu-uct --max-iterations 1000 --verbose --simulation-workers 3

python3 main.py --problem-file /Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/OP_Benchmark_Set/set_64_1/set_64_1_80.txt --algorithm wu-uct --max-iterations 100000 --verbose --simulation-workers 3 --output-file /UCT/uct-output/wu-set_64_80_100k.txt

/Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/OP_Benchmark_Set/set_64_1/set_64_1_80.txt

### Programmatic Usage

```python
from UCT import UCTSingleThread, WUUCT
from orienteering.orienteering import OrienteeringProblem

# Load problem
nodes, budget = OrienteeringProblem.load_problem("problem.txt")
problem = OrienteeringProblem(nodes, budget)

# Single-threaded UCT
uct = UCTSingleThread(problem, iterations=10000)
best_state = uct.run()

# Parallel WU-UCT
wu_uct = WUUCT(problem, simulation_workers=4)
best_state = wu_uct.run(max_iterations=10000)
```

## Parameters

- `--problem-file`: Path to orienteering problem file
- `--algorithm`: Choice of 'uct' or 'wu-uct' (default: wu-uct)
- `--max-iterations`: Maximum number of iterations (default: 100000)
- `--exploration-constant`: UCT exploration parameter (default: √2)
- `--simulation-workers`: Number of simulation workers for WU-UCT (default: 4)
- `--expansion-workers`: Must be 1 for WU-UCT (default: 1)
- `--verbose`: Enable detailed progress output
- `--output-file`: Save results to file
-  `--max-distance`: Sets max travle from given node

## Performance Comparison

Based on testing with `set_64_1_80.txt` and 100,000 iterations:

| Algorithm | Time | Reward | Nodes | Workers |
|-----------|------|--------|-------|---------|
| Single UCT | 3.27s | 1140 | 160 | 1 |
| WU-UCT | 126.66s | 1230 | 190 | 1+3 |

**Notes:**
- WU-UCT found a better solution (higher reward: 1230 vs 1140)
- WU-UCT explored more nodes (190 vs 160)  
- WU-UCT has coordination overhead but better exploration
- Single UCT is faster for same iteration count due to no thread overhead

## Architecture Details

### WU-UCT Components

1. **WUUCTExpansionWorker**
   - Manages tree structure with thread-safe operations
   - Performs selection and expansion phases
   - Distributes work units to simulation workers
   - Processes simulation results and backpropagates

2. **WUUCTSimulationWorker**
   - Receives work units from expansion worker
   - Performs random rollout simulations
   - Returns results to expansion worker
   - Tracks individual worker statistics

3. **WUUCT Main Coordinator**
   - Orchestrates expansion and simulation workers
   - Manages worker lifecycle and cleanup
   - Provides unified interface and statistics

### Thread Safety
- Locks protect tree modifications
- Queues handle work distribution
- Proper shutdown sequence prevents deadlocks
- Exception handling prevents worker crashes

## Modular Architecture Benefits

The WU-UCT implementation has been refactored from a single 850+ line monolithic file into focused, modular components (~150 lines each):

### Advantages of Modular Design

1. **Single Responsibility Principle**
   - `work_units.py`: Data structures only
   - `expansion_worker.py`: Tree management only  
   - `simulation_worker.py`: Simulation logic only
   - `wu_uct_coordinator.py`: Orchestration only

2. **Improved Maintainability**
   - Easier to locate and fix bugs in specific components
   - Changes to simulation logic don't affect tree management
   - Clear boundaries between threading concerns

3. **Better Testing**
   - Each component can be unit tested independently
   - Mock objects can isolate specific functionality
   - Easier to identify performance bottlenecks

4. **Enhanced Readability**
   - Smaller files are easier to understand
   - Clear imports show component dependencies
   - Logical flow is more apparent

5. **Development Efficiency**
   - Multiple developers can work on different components
   - Reduced merge conflicts in version control
   - Faster compilation and IDE navigation

### File Size Comparison
- **Before**: Single `wu_uct.py` file (850+ lines)
- **After**: Four focused files (~150 lines each)
- **Result**: Same functionality with 4x better organization

## Differences from Original MCTS

This UCT implementation improves upon the original MCTS base:

1. **Better Structure**: Clear separation of UCT logic from orienteering specifics
2. **True Parallelism**: WU-UCT implements proper work unit distribution
3. **Thread Safety**: Robust multi-threading with proper synchronization
4. **Comprehensive Testing**: Command-line interface for easy benchmarking
5. **Documentation**: Clear code documentation and usage examples

## Future Enhancements

- Adaptive exploration constant tuning
- Progressive widening for large action spaces
- RAVE (Rapid Action Value Estimation) integration
- Domain-specific heuristics for orienteering
- GPU acceleration for simulations