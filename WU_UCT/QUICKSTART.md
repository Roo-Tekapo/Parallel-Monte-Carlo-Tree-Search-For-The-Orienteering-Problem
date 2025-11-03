# Quick Start Guide: True WU-UCT

Get started with the True WU-UCT implementation in 5 minutes!

## Installation

No special installation needed - just use the existing Python environment.

## Quick Test

```bash
# Run the tests
cd WU_UCT
python test_wu_uct.py
```

## Basic Usage

### 1. Simple Example

```python
from WU_UCT.wu_uct_coordinator import WUUCTCoordinator
from WU_UCT.orienteering_adapter import OrienteeringAdapter

# Load problem
problem = OrienteeringAdapter.load_problem("path/to/problem.txt")

# Create coordinator
coordinator = WUUCTCoordinator(
    problem=problem,
    num_expansion_workers=4,    # Workers for tree traversal
    num_simulation_workers=8     # Workers for simulations
)

# Run algorithm
best_state = coordinator.run(
    max_iterations=10000,
    verbose=True
)

# Print result
print(f"Best reward: {best_state.reward_so_far}")
print(f"Path: {best_state.path}")
```

### 2. Command Line

```bash
# Basic run
python main.py -p ../OP_Benchmark_Set/sample/problem.txt

# Specify workers
python main.py -p problem.txt -e 4 -s 8

# With time limit
python main.py -p problem.txt --max-time 30.0 -v

# Save results
python main.py -p problem.txt -o results.txt -v
```

## Understanding the Output

```
Starting True WU-UCT
Expansion workers: 4        ← Number of tree traversal workers
Simulation workers: 8       ← Number of simulation workers
Target iterations: 10000

...

Expansion Phase:
  Total iterations: 10000   ← Tree selections performed
  Total expansions: 8234    ← New nodes added
  Iterations/sec: 803.2     ← Throughput

Simulation Phase:
  Total simulations: 10000  ← Rollouts completed
  Simulations/sec: 803.2    ← Simulation throughput

Efficiency Metrics:
  Worker utilization: 100.0%           ← How well workers stayed busy
  Expansion/Simulation ratio: 1:1.00   ← Balance between phases
```

## Tuning Workers

### General Rules

**Expansion Workers:**
- Perform tree traversal and expansion
- Rule of thumb: 1 per 2-4 CPU cores
- More expansion workers = more tree exploration

**Simulation Workers:**
- Perform independent simulations
- Rule of thumb: 2-3× expansion workers
- More simulation workers = better utilization

### Example Configurations

| CPU Cores | Expansion | Simulation | Total Workers |
|-----------|-----------|------------|---------------|
| 4         | 2         | 4          | 6             |
| 8         | 4         | 8          | 12            |
| 16        | 4         | 12         | 16            |
| 32        | 8         | 24         | 32            |

### Adjust Based on Workload

**Fast Simulations (< 1ms):**
- Increase expansion workers
- Example: 8 expansion, 8 simulation

**Slow Simulations (> 10ms):**
- Increase simulation workers
- Example: 4 expansion, 16 simulation

**Deep Trees:**
- More expansion workers for traversal
- Example: 6 expansion, 12 simulation

**Wide Trees:**
- Balance both types
- Example: 8 expansion, 16 simulation

## Common Issues

### Issue: Queue fills up
**Symptom:** `work_queue.qsize()` is always at max

**Solution:** Increase simulation workers
```python
coordinator = WUUCTCoordinator(
    problem=problem,
    num_expansion_workers=4,
    num_simulation_workers=16,  # ← Increase this
)
```

### Issue: Queue is empty
**Symptom:** Simulation workers waiting for work

**Solution:** Increase expansion workers
```python
coordinator = WUUCTCoordinator(
    problem=problem,
    num_expansion_workers=8,    # ← Increase this
    num_simulation_workers=8,
)
```

### Issue: Poor CPU utilization
**Symptom:** CPUs not fully utilized

**Solution:** Increase total workers
```python
# Use more workers than CPU cores (2-3× is OK)
coordinator = WUUCTCoordinator(
    problem=problem,
    num_expansion_workers=8,
    num_simulation_workers=16,  # Total: 24 workers on 8-core CPU
)
```

## Comparing with Simple_WU

Run both and compare:

```bash
# Run Simple_WU
cd ../Simple_WU
python main.py -p problem.txt -n 8 --max-iterations 10000

# Run True WU-UCT
cd ../WU_UCT
python main.py -p problem.txt -e 4 -s 8 --max-iterations 10000
```

Expected differences:
- **WU-UCT:** Higher iterations/sec with 8+ total workers
- **Simple_WU:** Simpler output, easier to understand
- **WU-UCT:** Better scalability, more complex stats

## Next Steps

1. **Read the paper:** Chen et al. (2018) "Watch the Unobservable"
2. **Check COMPARISON.md:** Detailed comparison with Simple_WU
3. **Experiment:** Try different worker configurations
4. **Profile:** Use verbose mode to understand bottlenecks
5. **Benchmark:** Compare on your specific problems

## Advanced: Custom Problems

To use WU-UCT with your own problem:

```python
class MyProblem:
    def create_initial_state(self):
        return MyState(...)
    
    def get_distance(self, from_node, to_node):
        # Return cost between nodes
        pass
    
    # ... other methods ...

class MyState:
    def is_terminal(self):
        # Return True if state is terminal
        pass
    
    def get_available_actions(self):
        # Return list of available actions
        pass
    
    def apply_action(self, action):
        # Return new state after action
        pass
    
    def copy(self):
        # Return copy of state
        pass

# Use with WU-UCT
problem = MyProblem()
coordinator = WUUCTCoordinator(problem=problem, ...)
```

## Help & Support

- Check `README.md` for detailed documentation
- See `COMPARISON.md` for Simple_WU vs WU-UCT
- Read tests in `test_wu_uct.py` for examples
- Review code comments for implementation details

## Performance Tips

1. **Start small:** Test with 100-1000 iterations first
2. **Profile:** Use verbose mode to see where time is spent
3. **Tune workers:** Adjust based on queue size and CPU utilization
4. **Compare:** Run both Simple_WU and WU-UCT to see differences
5. **Scale up:** Once tuned, increase iterations for better results

Happy parallel MCTS! 🚀
