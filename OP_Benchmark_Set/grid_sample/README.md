# Grid Sample - 10x10 Orienteering Problems

This directory contains orienteering test problems on a regular 10×10 grid.

## Problem Structure

- **Grid**: 11×11 points from (0,0) to (10,10) = 121 total nodes
- **Start**: (5,0) - Node ID 0 (reward = 0)
- **End**: (5,10) - Node ID 1 (reward = 0)  
- **Other nodes**: Random rewards between 1-20

## Test Cases

| File | Budget | Description | Use Case |
|------|--------|-------------|----------|
| `grid_10x10_easy_20.txt` | 20 | Short budget | Forces selective pathing, tests basic optimization |
| `grid_10x10_medium_30.txt` | 30 | Medium budget | Allows some exploration, balanced difficulty |
| `grid_10x10_hard_40.txt` | 40 | Longer budget | More strategic choices, complex trade-offs |
| `grid_10x10_long_50.txt` | 50 | Long budget | Near-optimal solutions possible, thoroughness test |

## Distance Characteristics

- Minimum distance between adjacent nodes: 1.0 (horizontal/vertical)
- Diagonal distance: √2 ≈ 1.414
- Start to end direct distance: √(0² + 10²) = √100 = 10.0

## Example Usage

Test with WU-UCT:
```bash
cd UCT
python3 main.py --problem-file ../OP_Benchmark_Set/grid_sample/grid_10x10_easy_20.txt \
    --algorithm wu-uct --max-iterations 10000 --verbose
```

Test with single-threaded MCTS:
```bash  
cd MCTS
python3 mcts_single_thread.py --problem-file ../OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt \
    --max-iterations 10000
```

## Grid Layout

```
(0,10) ─ (1,10) ─ (2,10) ─ ... ─ (10,10)
  │        │        │               │
(0,9)  ─ (1,9)  ─ (2,9)  ─ ... ─ (10,9)
  │        │        │               │
  ...      ...      ...             ...
  │        │        │               │
(0,1)  ─ (1,1)  ─ (2,1)  ─ ... ─ (10,1)
  │        │        │               │
(0,0)  ─ (1,0)  ─ (2,0)  ─ ... ─ (10,0)

START: (5,0) 
END:   (5,10)
```

## Generation Info

- Random seed used for reproducible results
- Rewards assigned with uniform distribution 1-20
- All nodes are fully connected (complete graph)
- Generated using `generate_grid_sample.py`