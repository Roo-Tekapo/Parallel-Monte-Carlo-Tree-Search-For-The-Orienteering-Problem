# Simulation Reward Standardization Fix

**Date:** November 4, 2025  
**Issue:** High standard deviation in VL and WU-UCT algorithms across repeated runs

## Problem Identified

The high variance in VL and WU-UCT results was caused by **inconsistent completion bonuses and penalties** across algorithms:

### Original Reward Bonuses (Before Fix)

| Algorithm | Completion Bonus | Incomplete Penalty | Variance |
|-----------|------------------|-------------------|----------|
| **VL**    | **+1.0** ⚠️      | 0.7× (30% penalty) | **HIGH** |
| **WU-UCT**| **+1.0** ⚠️      | 0.7× (30% penalty) | **HIGH** |
| Simple_WU | +0.15            | 0.7× (30% penalty) | High    |
| Tree      | +0.05            | 0.9× (10% penalty) | Low     |
| UCT       | +0.05            | 0.8× (20% penalty) | Low     |

### Why This Caused High Standard Deviation

1. **VL and WU-UCT had 20x larger bonuses** (+1.0 vs +0.05) compared to UCT/Tree
2. **Amplification Effect**: A single early path completion would dominate tree exploration
3. **Timing Sensitivity**: With 8 parallel workers, small timing differences led to:
   - Different workers discovering completions at different times
   - Dramatically different tree exploration patterns
   - Vastly different final solutions across runs

4. **Race Condition Impact**: The large bonus made the algorithm extremely sensitive to:
   - Which worker completed a path first
   - Thread scheduling variations
   - Lock acquisition timing

## Solution Applied

**Standardized all algorithms to use UCT's conservative values:**

- **Completion Bonus:** `+0.05` (reduced from 1.0 for VL/WU-UCT)
- **Incomplete Penalty:** `0.8×` (20% penalty, standardized across all)

### Changes Made

#### 1. VL (Virtual Loss) - `VL/vl_worker.py`
```python
# BEFORE:
reward += 1.0  # Significant bonus (equivalent to 2+ good nodes)
reward *= 0.7  # 30% penalty

# AFTER:
reward += 0.05  # Completion bonus (standardized)
reward *= 0.8   # 20% penalty (standardized)
```

#### 2. WU-UCT - `WU_UCT/simulation_worker.py`
```python
# BEFORE:
reward += 1.0  # STRONG completion bonus (matches VL)
reward *= 0.7  # Incomplete penalty

# AFTER:
reward += 0.05  # Completion bonus (standardized)
reward *= 0.8   # 20% penalty (standardized)
```

#### 3. Simple_WU - `Simple_WU/simple_wu_worker.py`
```python
# BEFORE:
reward += 0.15  # Meaningful bonus
reward *= 0.7   # 30% penalty

# AFTER:
reward += 0.05  # Completion bonus (standardized)
reward *= 0.8   # 20% penalty (standardized)
```

#### 4. Tree - `Tree/tree_parallel_worker.py`
```python
# BEFORE:
reward += 0.05  # Small bonus
reward *= 0.9   # 10% penalty

# AFTER:
reward += 0.05  # Completion bonus (standardized)
reward *= 0.8   # 20% penalty (standardized)
```

#### 5. UCT - `UCT/uct_single_thread.py`
```python
# Already standardized:
reward += 0.05  # Completion bonus
reward *= 0.8   # 20% penalty
```

## Expected Results

### Before Fix:
- VL: High standard deviation (e.g., σ = 15-20% of mean)
- WU-UCT: High standard deviation
- Tree/UCT: Low standard deviation (σ = 2-5% of mean)

### After Fix (Expected):
- **All algorithms:** Low standard deviation (~2-5% of mean)
- **Fair comparison:** All algorithms now use identical reward shaping
- **Reproducibility:** Reduced sensitivity to parallel execution timing

## Testing Recommendations

1. **Re-run benchmarks** with 5+ runs per problem:
   ```bash
   python .\results_gen\run_benchmark.py -d grid_patterns -w 8 --runs 5 --output standardized_rewards.xlsx
   ```

2. **Compare standard deviations** before/after the fix

3. **Verify algorithm rankings** remain consistent (relative performance should be similar)

4. **Check for completion rates** - ensure paths still reach END node at similar rates

## Technical Notes

### Why Small Bonuses Are Better

1. **Stability:** Small bonuses (0.05) provide gentle guidance without overwhelming the reward signal
2. **Exploration:** Allows algorithm to explore multiple good paths rather than fixating on first completion
3. **Robustness:** Less sensitive to random variations in simulation outcomes
4. **Fairness:** Creates level playing field for comparing parallel coordination strategies

### Why Standardize?

The goal is to benchmark **parallel coordination mechanisms** (Virtual Loss, WU-UCT, Tree Parallel), not **reward shaping strategies**. Inconsistent rewards confound the comparison.

## Files Modified

- `VL/vl_worker.py` (line ~276)
- `WU_UCT/simulation_worker.py` (line ~135)
- `Simple_WU/simple_wu_worker.py` (line ~282)
- `Tree/tree_parallel_worker.py` (line ~179)

## Related Issues

This fix addresses the core cause of variance but other factors may contribute:
- Thread scheduling non-determinism
- Random seed management across workers
- Lock contention patterns

Consider adding deterministic seeding for fully reproducible benchmarks if needed.
