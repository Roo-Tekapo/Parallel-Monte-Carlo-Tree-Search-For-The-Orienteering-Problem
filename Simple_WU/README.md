# Simple_WU - Simplified WU-UCT Implementation

This directory contains a simplified version of the WU-UCT (Work Unit UCT) algorithm where each worker handles both tree expansion and simulation, eliminating the complexity of separate worker types and work unit coordination.

## Key Differences from Full UCT Implementation

### Architecture Simplification
- **Single Worker Type**: Instead of separate expansion and simulation workers, `SimpleWUWorker` handles both responsibilities
- **No Work Queues**: Workers perform complete MCTS iterations directly on the shared tree
- **Direct Tree Access**: Workers access the tree directly with proper synchronization instead of using work units
- **Simpler Coordination**: The coordinator just creates workers and waits for completion

### Benefits
- **Reduced Complexity**: Fewer classes, no queue management, simpler debugging
- **Lower Overhead**: No work unit creation/passing between workers
- **Easier Understanding**: Each worker does a complete MCTS iteration
- **Better Cache Locality**: Workers operate on tree data directly

### Trade-offs
- **Less Flexible**: Cannot easily vary expansion vs simulation ratios
- **Potentially Less Scalable**: All workers compete for tree access
- **Coarser Granularity**: Work division is at the iteration level, not operation level

## Files

### Core Implementation
- `simple_wu_worker.py` - Unified worker that handles both expansion and simulation
- `simple_wu_coordinator.py` - Simplified coordinator managing unified workers
- `main.py` - Main entry point with examples and benchmarking
- `test_simple_wu.py` - Basic tests for the implementation

### Key Classes

#### `SimpleWUWorker`
Unified worker that performs complete MCTS iterations:
1. **Selection**: Traverse tree using UCT until leaf node
2. **Expansion**: Add new child if unexplored actions available
3. **Simulation**: Perform random rollout from new/leaf state
4. **Backpropagation**: Update all nodes in path with result

#### `SimpleWUUCT`
Simplified coordinator that:
- Creates multiple `SimpleWUWorker` instances
- Divides total iterations among workers
- Manages worker lifecycle
- Extracts best solution from shared tree
- Provides statistics and monitoring

## Usage

### Basic Usage
```python
from Simple_WU.simple_wu_coordinator import SimpleWUUCT
from orienteering.orienteering import OrienteeringProblem

# Load problem
problem = OrienteeringProblem.from_file("problem.txt")

# Create and run Simple WU-UCT
simple_wu_uct = SimpleWUUCT(
    problem=problem,
    num_workers=4,
    exploration_constant=1.414
)

best_state = simple_wu_uct.run(
    max_iterations=10000,
    verbose=True
)

print(f"Best reward: {best_state.total_reward}")
```

### Command Line Usage
```bash
# Basic run with required problem file
python main.py --problem-file /path/to/problem.txt

# Specify iterations and workers
python main.py --problem-file /path/to/problem.txt --max-iterations 10000 --num-workers 4

# With time limit and verbose output
python main.py --problem-file /path/to/problem.txt --max-time 30.0 --verbose

# Run benchmark comparison
python main.py --benchmark

# Show all options
python main.py --help
```

## Algorithm Flow

### Single Worker Iteration
1. **Tree Traversal**: Start at root, use UCT to select path to leaf
2. **Expansion Check**: If leaf has unexplored actions, add one child
3. **Simulation**: Perform random rollout from expanded/leaf node
4. **Backpropagation**: Update visit counts and rewards for all path nodes

### Multi-Worker Coordination
- Each worker performs `total_iterations // num_workers` iterations
- Workers access shared tree with node-level locking
- No communication between workers during execution
- Final solution extracted by following most-visited path

## Thread Safety

### Synchronization Strategy
- Each `WUUCTNode` has its own lock (`threading.Lock`)
- Workers acquire node locks during:
  - UCT selection (reading visit counts, rewards)
  - Expansion (adding new children)
  - Backpropagation (updating visit counts, rewards)
- Fine-grained locking allows good parallelism
- Lock ordering prevents deadlocks (always root-to-leaf)

### Race Condition Prevention
- State copying prevents shared state corruption
- Node expansion uses atomic child addition
- Statistics updates are protected by locks

## Performance Characteristics

### Scalability
- **Good**: 1-8 workers typically show improvement
- **Diminishing Returns**: Beyond 8 workers due to lock contention
- **Problem Dependent**: Larger trees scale better

### Memory Usage
- Shared tree structure saves memory vs separate trees
- Node locking adds small overhead per node
- Linear growth with tree size

### CPU Utilization
- High CPU utilization during simulation phases
- Some serialization during tree operations
- Better with compute-intensive simulation

## Testing

Run tests to verify functionality:
```bash
python test_simple_wu.py
```

Tests cover:
- Basic functionality with different worker counts
- Statistics collection
- Tree growth verification
- Solution quality checks

## Comparison with Full UCT

| Aspect | Simple_WU | Full UCT |
|--------|-----------|----------|
| Complexity | Low | High |
| Worker Types | 1 (unified) | 2 (expansion + simulation) |
| Communication | Direct tree access | Work queues |
| Scalability | Good (1-8 workers) | Better (more workers) |
| Overhead | Low | Higher |
| Flexibility | Limited | High |
| Debug Ease | Easy | Harder |

## When to Use Simple_WU

### Good For:
- **Learning**: Understanding MCTS parallelization
- **Prototyping**: Quick algorithm variations
- **Small-Medium Problems**: Where complexity isn't needed
- **Limited Workers**: When using 1-8 workers
- **Simple Deployments**: Fewer moving parts

### Use Full UCT For:
- **High Scalability**: Need many workers (>8)
- **Complex Coordination**: Need specialized worker behaviors
- **Production Systems**: Where maximum performance matters
- **Research**: Exploring advanced parallelization strategies

## Future Improvements

### Potential Enhancements
1. **Adaptive Work Distribution**: Dynamic iteration rebalancing
2. **NUMA Awareness**: Better memory locality on multi-socket systems
3. **Hybrid Approach**: Switch between simple/complex based on problem size
4. **Progressive Widening**: Limit expansion early, broaden later
5. **Virtual Loss**: Reduce lock contention during selection

### Monitoring
- Add real-time progress visualization
- Detailed per-worker performance metrics
- Tree structure analysis tools
- Convergence detection