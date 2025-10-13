# How to Control Expansion Worker Type in WU-UCT

## Quick Answer

**By default, WU-UCT now uses the OPTIMIZED expansion worker** (5-10x faster). You don't need to do anything special!

## Command Line Usage

### Use Optimized (Default) ✅
```bash
# Optimized is now the default
python -m UCT.main --algorithm wu-uct --problem-file <file>

# Or explicitly specify (optional)
python -m UCT.main --algorithm wu-uct --problem-file <file> --use-optimized
```

### Use Original (For Testing/Debugging)
```bash
# Explicitly request original expansion worker
python -m UCT.main --algorithm wu-uct --problem-file <file> --use-original
```

### Adjust Batch Size (Optimized Only)
```bash
# Default batch size is 5
python -m UCT.main --algorithm wu-uct --problem-file <file> --batch-size 10
```

## Python API Usage

### Option 1: Using WUUCT Class Directly

```python
from orienteering.orienteering import OrienteeringProblem
from UCT.wu_uct_coordinator import WUUCT

# Load problem
nodes, budget = OrienteeringProblem.load_problem("problem.txt")
problem = OrienteeringProblem(nodes, budget)

# Use OPTIMIZED (default, recommended)
wu_uct = WUUCT(
    problem,
    expansion_workers=2,
    simulation_workers=4,
    use_optimized=True,  # ← This is the default
    batch_size=5         # ← Optional, default is 5
)
best_state = wu_uct.run(max_iterations=10000, verbose=True)

# Use ORIGINAL (for debugging)
wu_uct = WUUCT(
    problem,
    expansion_workers=2,
    simulation_workers=4,
    use_optimized=False  # ← Explicitly request original
)
best_state = wu_uct.run(max_iterations=10000, verbose=True)
```

### Option 2: Using Convenience Function

```python
from orienteering.orienteering import OrienteeringProblem
from UCT.wu_uct_coordinator import run_wu_uct

# Load problem
nodes, budget = OrienteeringProblem.load_problem("problem.txt")
problem = OrienteeringProblem(nodes, budget)

# Use OPTIMIZED (default)
best_state = run_wu_uct(
    problem,
    max_iterations=10000,
    simulation_workers=4,
    use_optimized=True,  # ← Default
    batch_size=5,        # ← Optional
    verbose=True
)

# Use ORIGINAL
best_state = run_wu_uct(
    problem,
    max_iterations=10000,
    simulation_workers=4,
    use_optimized=False,  # ← Explicitly request original
    verbose=True
)
```

## Complete Examples

### Example 1: Quick Test with Optimized (Recommended)
```bash
python -m UCT.main \
  --algorithm wu-uct \
  --problem-file OP_Benchmark_Set/set_64_1/set_64_1_80.txt \
  --max-iterations 10000 \
  --expansion-workers 2 \
  --simulation-workers 4 \
  --verbose
```

### Example 2: Performance Test with Larger Batch
```bash
python -m UCT.main \
  --algorithm wu-uct \
  --problem-file OP_Benchmark_Set/parallel_friendly_v2/xlarge/xlarge_40x40_r0_42.txt \
  --max-iterations 50000 \
  --expansion-workers 4 \
  --simulation-workers 8 \
  --batch-size 10 \
  --verbose
```

### Example 3: Debug with Original Worker
```bash
python -m UCT.main \
  --algorithm wu-uct \
  --problem-file OP_Benchmark_Set/sample/sample_30.txt \
  --max-iterations 1000 \
  --expansion-workers 1 \
  --simulation-workers 2 \
  --use-original \
  --verbose
```

### Example 4: Time-Limited Run
```bash
python -m UCT.main \
  --algorithm wu-uct \
  --problem-file OP_Benchmark_Set/set_64_1/set_64_1_80.txt \
  --max-time 60 \
  --expansion-workers 2 \
  --simulation-workers 4 \
  --verbose
```

## Parameter Guide

### Core Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--algorithm` | `wu-uct` | Choose `uct` or `wu-uct` |
| `--problem-file` | Required | Path to problem file |
| `--max-iterations` | 100000 | Number of MCTS iterations |
| `--max-time` | None | Time limit (overrides iterations) |

### Worker Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--expansion-workers` | 2 | Number of expansion workers |
| `--simulation-workers` | 4 | Number of simulation workers |
| `--use-optimized` | True | Use optimized expansion worker |
| `--use-original` | False | Use original expansion worker |
| `--batch-size` | 5 | Work unit batch size (optimized only) |

### Algorithm Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--exploration-constant` | √2 | UCT exploration constant |
| `--max-distance` | None | Max edge distance constraint |

### Output Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--verbose` | False | Print detailed progress |
| `--output-file` | None | Save results to file |

## Performance Tuning

### Batch Size Recommendations

| Problem Size | Recommended Batch Size |
|--------------|------------------------|
| Small (< 100 nodes) | 3-5 |
| Medium (100-500 nodes) | 5-10 |
| Large (500-1000 nodes) | 10-15 |
| Very Large (1000+ nodes) | 15-20 |

**Higher batch size = less queue overhead but more work per batch**

### Worker Count Recommendations

| Cores Available | Expansion Workers | Simulation Workers |
|-----------------|-------------------|--------------------|
| 4 cores | 1 | 2-3 |
| 8 cores | 2 | 4-6 |
| 16 cores | 2-4 | 8-12 |
| 32 cores | 4-8 | 16-24 |

**Rule of thumb:** 1 expansion worker per 4-8 cores, rest for simulation

## Output Differences

### Optimized Worker Output
```
Starting WU-UCT with 2 OPTIMIZED expansion workers and 4 simulation workers
  Using fine-grained locking with batch_size=5
```

### Original Worker Output
```
Starting WU-UCT with 2 ORIGINAL expansion workers and 4 simulation workers
```

## When to Use Each

### Use OPTIMIZED When:
- ✅ Running production experiments
- ✅ Need maximum performance
- ✅ Using multiple workers (2+)
- ✅ Large problems (> 100 nodes)
- ✅ High iteration counts (> 10,000)

### Use ORIGINAL When:
- ✅ Debugging algorithm logic
- ✅ Learning/understanding code
- ✅ Single worker testing
- ✅ Simplicity is priority
- ✅ Comparing implementations

## Migrating Existing Code

If you have existing code using WU-UCT:

### Before (Still Works!)
```python
wu_uct = WUUCT(problem, simulation_workers=4)
best_state = wu_uct.run(max_iterations=10000)
```

### After (Explicitly Control)
```python
# Optimized (default behavior)
wu_uct = WUUCT(problem, simulation_workers=4, use_optimized=True)
best_state = wu_uct.run(max_iterations=10000)

# Original (if needed)
wu_uct = WUUCT(problem, simulation_workers=4, use_optimized=False)
best_state = wu_uct.run(max_iterations=10000)
```

**No code changes required!** The optimized worker is now the default, so existing code automatically gets the performance boost.

## Troubleshooting

### Problem: Not seeing performance improvement
**Solution:** Make sure you're using multiple workers and a large problem:
```bash
python -m UCT.main --algorithm wu-uct --problem-file <large_file> \
  --expansion-workers 2 --simulation-workers 4 --verbose
```

### Problem: Want to verify which worker is being used
**Solution:** Use `--verbose` flag to see worker type at startup:
```bash
python -m UCT.main --algorithm wu-uct --problem-file <file> --verbose
```

### Problem: Optimized worker seems unstable
**Solution:** Try reducing batch size or use original for debugging:
```bash
python -m UCT.main --algorithm wu-uct --problem-file <file> \
  --batch-size 3 --verbose
# OR
python -m UCT.main --algorithm wu-uct --problem-file <file> \
  --use-original --verbose
```

## Summary

**TL;DR:**
- Optimized is now the **default** ✅
- No code changes needed 🎉
- 5-10x faster with multiple workers 🚀
- Use `--use-original` to switch back if needed 🔧
- Adjust `--batch-size` to tune performance 🎚️

---

**Updated:** October 7, 2025
