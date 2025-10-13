# Reward Normalization in Simple WU-UCT

## Overview

The Simple WU-UCT implementation now includes **reward normalization** to ensure consistent exploration-exploitation balance in the UCT formula, regardless of the problem's actual reward scale.

## Why Normalize?

### The Problem with Raw Rewards

In the UCT formula:
```
UCT = exploitation + exploration
    = (total_reward / visits) + c * sqrt(2*log(N_parent) / N_child)
```

The exploitation term uses **raw reward values**, which can vary dramatically:
- Small problem: rewards might be 5-50
- Large problem: rewards might be 500-5000

This means:
1. The exploration constant `c` (typically √2 ≈ 1.414) may be too large or too small
2. Different problems require different exploration constants
3. The algorithm behavior is scale-dependent

### The Solution: Normalization

By normalizing rewards to [0, 1], we ensure:
1. ✅ Consistent exploration-exploitation balance across all problems
2. ✅ The exploration constant √2 works as theoretically intended
3. ✅ More stable and predictable behavior
4. ✅ Better alignment with UCT's theoretical foundations

## Implementation

### 1. RewardNormalizer Class

**Location**: `Simple_WU/reward_normalizer.py`

```python
normalizer = RewardNormalizer()
normalizer.update(reward)  # Update bounds after each simulation
normalized = normalizer.normalize(raw_reward)  # Normalize a value
```

**Features**:
- Thread-safe for parallel access
- Tracks min/max observed rewards
- Normalizes to [0, 1] range: `(reward - min) / (max - min)`

### 2. EstimatedRewardNormalizer Class

Uses problem structure to **estimate bounds** instead of discovering them:
- Min reward: Start node score (often 0)
- Max reward: Sum of all node scores (theoretical upper bound)

**Advantages**:
- Better normalization from the very first iteration
- No need to discover bounds during early search
- More consistent across multiple runs

```python
normalizer = EstimatedRewardNormalizer(problem)
```

## Usage

### In SimpleWUUCT Coordinator

```python
# Enable normalization with estimated bounds (RECOMMENDED)
solver = SimpleWUUCT(
    problem=problem,
    num_workers=4,
    use_reward_normalization=True,    # Enable normalization
    use_estimated_bounds=True          # Use problem-based bounds
)

# Enable normalization with discovered bounds
solver = SimpleWUUCT(
    problem=problem,
    num_workers=4,
    use_reward_normalization=True,    # Enable normalization
    use_estimated_bounds=False         # Discover bounds during search
)

# Disable normalization (original behavior)
solver = SimpleWUUCT(
    problem=problem,
    num_workers=4,
    use_reward_normalization=False     # No normalization
)
```

### Default Behavior

**By default, normalization is ENABLED with estimated bounds.**

This provides the best out-of-the-box performance for most problems.

## How It Works

### 1. Initialization
```python
# Coordinator creates a shared normalizer
self.reward_normalizer = EstimatedRewardNormalizer(problem)
# Bounds: [0, sum_of_all_scores]
```

### 2. During Simulation
```python
# Worker performs simulation
reward = simulation_state.reward_so_far

# Update normalizer with observed reward
self.reward_normalizer.update(reward)
```

### 3. During Selection
```python
# Calculate average reward
avg_reward = child.total_reward / child.visits

# Normalize it
if self.reward_normalizer:
    exploitation = self.reward_normalizer.normalize(avg_reward)
else:
    exploitation = avg_reward  # Raw value

# Combine with exploration
uct_value = exploitation + c * sqrt(...)
```

## Testing

Run the comparison test to see the impact:

```bash
cd Simple_WU
python test_reward_normalization.py
```

This will compare three configurations:
1. No normalization (original)
2. Normalization with discovered bounds
3. Normalization with estimated bounds (recommended)

## Statistics

Access normalization statistics after search:

```python
stats = solver.get_tree_statistics()
if 'reward_normalization' in stats:
    norm_stats = stats['reward_normalization']
    print(f"Min reward: {norm_stats['min_reward']}")
    print(f"Max reward: {norm_stats['max_reward']}")
    print(f"Range: {norm_stats['reward_range']}")
```

## Theoretical Background

UCT was originally designed for the **multi-armed bandit problem** where rewards are in [0, 1]. The exploration constant √2 is theoretically justified for this range. When rewards are outside [0, 1], the theoretical guarantees may not hold, and empirical performance can suffer.

### References

1. Kocsis & Szepesvári (2006): "Bandit based Monte-Carlo Planning"
   - Original UCT paper, assumes [0, 1] rewards

2. Browne et al. (2012): "A Survey of Monte Carlo Tree Search Methods"
   - Discusses reward normalization as a best practice

3. Enzenberger & Müller (2010): "A Lock-free Multithreaded Monte-Carlo Tree Search Algorithm"
   - Discusses virtual loss and parallelization (WU-UCT basis)

## Migration Guide

### Existing Code

If you have existing code using `SimpleWUUCT`:

```python
# Old code - still works! (normalization is on by default)
solver = SimpleWUUCT(problem=problem, num_workers=4)
```

### To Disable Normalization

If you want the original behavior:

```python
solver = SimpleWUUCT(
    problem=problem, 
    num_workers=4,
    use_reward_normalization=False
)
```

### Custom Exploration Constant

With normalization, you may need to adjust your exploration constant:

```python
# With normalization, √2 usually works well
solver = SimpleWUUCT(
    problem=problem,
    num_workers=4,
    exploration_constant=math.sqrt(2),  # Standard value
    use_reward_normalization=True
)

# Without normalization, you may need problem-specific tuning
solver = SimpleWUUCT(
    problem=problem,
    num_workers=4,
    exploration_constant=100.0,  # Example: much larger for high-reward problems
    use_reward_normalization=False
)
```

## Troubleshooting

### Problem: All rewards are the same

If all simulations produce the same reward, normalization returns 0.5 (neutral value).

**Solution**: This is correct behavior. If all actions have equal value, exploration should dominate.

### Problem: Rewards outside observed range

The normalizer clamps values to [0, 1] even if they're outside the observed range.

**Solution**: This is safe. Early in search, bounds may not be fully discovered yet.

### Problem: Performance difference

Normalization changes the scale of the exploitation term, which can affect which nodes are selected.

**Solution**: This is expected and usually improves performance. If not, check your exploration constant.

## Summary

✅ **Reward normalization is now enabled by default**  
✅ **Uses estimated bounds from problem structure**  
✅ **Provides more stable and theoretically sound behavior**  
✅ **Can be disabled for backward compatibility**

For most use cases, the default settings work best!
