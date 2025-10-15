# Virtual Loss Quick Start Guide

Get started with Virtual Loss MCTS in 5 minutes!

## Installation

No installation needed! The VL implementation is ready to use.

## Quick Test

Run a simple test to verify everything works:

```bash
python VL/test_vl.py
```

You should see:
```
✅ Test 1 PASSED: VL Node Operations
✅ Test 2 PASSED: Basic VL-MCTS Execution
✅ Test 3 PASSED: Virtual Loss Collision Tracking
✅ Test 4 PASSED: Thread Safety

🎉 ALL TESTS PASSED! 🎉
```

## Your First Run

### Command Line

```bash
python VL/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt
```

Expected output:
```
Virtual Loss MCTS Statistics
============================================================
Overall Performance:
  Total Time: 5.23s
  Total Iterations: 10000
  ...
Best Solution Found:
  Path: [0, 5, 12, 18, 25, 30, 1]
  Reward: 2.3456
```

### Python Script

```python
from orienteering.orienteering_traditional import OrienteeringProblem
from VL.vl_coordinator import VirtualLossMCTS

# Load problem
problem = OrienteeringProblem(
    "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt",
    normalize_rewards=True
)

# Create VL-MCTS
vl = VirtualLossMCTS(
    problem=problem,
    num_workers=4,
    virtual_loss_value=1.0
)

# Run and get solution
solution = vl.run(max_iterations=10000, verbose=True)

print(f"Best path: {solution.path}")
print(f"Reward: {solution.reward_so_far}")
```

## Understanding the Output

### Key Metrics

**Collision Rate**: How often threads select nodes with existing virtual loss
- < 5%: Excellent thread separation
- 5-10%: Good coordination
- 10-20%: Acceptable
- > 20%: Too much overlap (increase `--vl-value`)

**Iterations/sec**: Processing speed
- Should scale with number of workers
- If not scaling: reduce worker count or increase problem size

### Example Output Explained

```
Virtual Loss Coordination:
  VL Value: 1.0              ← Your penalty value
  Total Collisions: 523      ← Times threads overlapped
  Avg Collision Rate: 5.23%  ← Lower is better
```

## Tuning Virtual Loss Value

Start with default (1.0) and adjust based on collision rate:

```bash
# Too many collisions (>15%)? Increase VL
python VL/main.py --problem-file myfile.txt --vl-value 2.0

# Too few collisions (<3%)? Decrease VL  
python VL/main.py --problem-file myfile.txt --vl-value 0.5
```

### Quick Reference Table

| Workers | Small Problem | Medium Problem | Large Problem |
|---------|---------------|----------------|---------------|
| 2-4     | VL = 0.5-1.0  | VL = 1.0       | VL = 1.0-1.5  |
| 4-8     | VL = 1.0-1.5  | VL = 1.5       | VL = 1.5-2.0  |
| 8-16    | VL = 1.5-2.0  | VL = 2.0       | VL = 2.0-3.0  |

## Common Commands

### Basic run
```bash
python VL/main.py -p OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt
```

### More workers
```bash
python VL/main.py -p myfile.txt --workers 8
```

### More iterations
```bash
python VL/main.py -p myfile.txt --iterations 50000
```

### Time limit
```bash
python VL/main.py -p myfile.txt --time-limit 60  # 60 seconds
```

### Tune VL value
```bash
python VL/main.py -p myfile.txt --vl-value 2.0
```

### Verbose output
```bash
python VL/main.py -p myfile.txt --verbose
```

### Quiet mode
```bash
python VL/main.py -p myfile.txt --quiet
```

## Comparing with WU-UCT

Run both and compare:

```bash
# Virtual Loss
python VL/main.py -p myfile.txt --workers 4 --iterations 10000

# WU-UCT
python Simple_WU/main.py -p myfile.txt --workers 4 --iterations 10000
```

Both should give similar results, but VL is easier to tune!

## Troubleshooting

### Problem: High collision rate (>20%)

**Solution**: Increase VL value
```bash
python VL/main.py -p myfile.txt --vl-value 2.0
```

### Problem: Low collision rate (<2%) but poor results

**Solution**: Decrease VL value (threads too separated)
```bash
python VL/main.py -p myfile.txt --vl-value 0.5
```

### Problem: Not scaling with workers

**Solution**: Problem too small or need more iterations
```bash
# Increase iterations
python VL/main.py -p myfile.txt --workers 4 --iterations 50000

# Or reduce workers
python VL/main.py -p myfile.txt --workers 2 --iterations 10000
```

### Problem: Out of memory

**Solution**: Reduce workers or use time limit
```bash
python VL/main.py -p myfile.txt --workers 2 --time-limit 30
```

## Next Steps

1. ✅ Run `test_vl.py` to verify installation
2. ✅ Try basic run with default parameters
3. ✅ Experiment with different VL values
4. ✅ Compare with your WU-UCT implementation
5. ✅ Read `README.md` for detailed documentation
6. ✅ Check `VL_vs_WU_UCT_COMPARISON.md` for in-depth comparison

## Quick Reference

### Command Line Options

```
Required:
  -p, --problem-file PATH     Problem file to solve

Algorithm:
  -w, --workers N             Number of workers (default: 4)
  -i, --iterations N          Total iterations (default: 10000)
  -t, --time-limit SECONDS    Time limit (overrides iterations)
  -v, --vl-value VALUE        Virtual loss value (default: 1.0)
  -e, --exploration VALUE     UCT exploration constant (default: 1.414)

Options:
  --normalize                 Enable reward normalization (default)
  --no-normalize             Disable reward normalization
  --verbose                  Detailed output
  -q, --quiet                Minimal output
```

### Python API

```python
from VL.vl_coordinator import VirtualLossMCTS

# Basic usage
vl = VirtualLossMCTS(problem, num_workers=4, virtual_loss_value=1.0)
solution = vl.run(max_iterations=10000)

# With time limit
solution = vl.run(max_iterations=999999, max_time=60.0)

# Get statistics
stats = vl.get_tree_statistics()
```

## Need Help?

- 📖 Full documentation: `VL/README.md`
- 🔬 Comparison guide: `VL/VL_vs_WU_UCT_COMPARISON.md`
- 🧪 Run tests: `python VL/test_vl.py`
- 🐛 Check test output for detailed diagnostics

## Success Criteria

You're ready to use VL-MCTS when:
- ✅ Tests pass
- ✅ Can run basic example
- ✅ Understand collision rate metric
- ✅ Know how to tune VL value

Happy tree searching! 🌲🔍
