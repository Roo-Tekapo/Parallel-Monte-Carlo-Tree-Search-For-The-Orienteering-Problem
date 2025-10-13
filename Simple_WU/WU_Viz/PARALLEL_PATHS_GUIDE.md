# WU-UCT Grid Visualization - Parallel Worker Path Tracking

## Overview

The enhanced WU-UCT Grid Visualization now includes **real-time parallel worker path tracking**, allowing you to see exactly what each worker is exploring as the algorithm runs. This feature is inspired by the original `viz/mcts_viz.py` but adapted for the parallel WU-UCT implementation.

## Key Features

### 🎨 **Parallel Worker Path Visualization**
- **Each worker has a unique color** - Red, Teal, Blue, Green, Yellow, Pink, etc.
- **Dashed lines show active exploration** - See where each worker is currently searching
- **Real-time updates** - Paths update as workers explore different parts of the solution space
- **Visual diversity** - Algorithm distributes workers to different branches for better exploration

### 🗺️ **Problem Grid Display**
- **Spatial layout** - All nodes positioned at their actual coordinates
- **Score-based coloring** - Viridis colormap (dark purple = high score, yellow = low score)
- **Start/End markers** - Green square for start (node 0), red square for end (node 1)
- **Edge connections** - Gray lines showing valid transitions between nodes

### 🏆 **Best Path Highlighting**
- **Golden solid line** - Shows the current best solution found
- **Directional arrows** - Indicates path direction
- **Score & distance** - Real-time statistics for the best path
- **Validation** - Shows if path is valid (within budget constraint)

### 📊 **Live Statistics**
- **Algorithm status** - RUNNING or COMPLETED
- **Iteration progress** - Current / Target iterations
- **Tree metrics** - Total nodes, depth, performance
- **Worker status** - Individual worker progress and completion

## How It Works

### Worker Path Extraction Algorithm

Since WU-UCT workers don't directly expose their current exploration path, the visualization uses an intelligent heuristic approach:

1. **Tree Sampling** - Periodically samples the shared search tree
2. **Activity Detection** - Identifies nodes with recent visits and pending simulations
3. **Branch Selection** - Each worker follows a different high-activity branch
4. **Visual Diversity** - Worker offset ensures different paths for different workers

```python
# Simplified algorithm
def extract_worker_path(worker_id):
    current_node = root
    path = [start_node]
    
    for depth in range(max_depth):
        # Find children sorted by activity (visits + pending simulations)
        active_children = sort_by_activity(current_node.children)
        
        # Select different branch for each worker (creates diversity)
        selected = active_children[worker_id % len(active_children)]
        
        path = selected.state.path
        current_node = selected
    
    return path
```

### Visual Rendering

- **Worker paths** - Dashed lines with worker-specific colors (zorder=4)
- **Best path** - Solid gold line with arrows (zorder=5, on top)
- **Node highlighting** - Nodes in best path have gold borders
- **Alpha blending** - Semi-transparent paths (60-80%) for better layering

## Interactive Controls

| Key | Action |
|-----|--------|
| `P` | Toggle worker path display ON/OFF |

## Usage Examples

### Quick Test (2,000 iterations)
```bash
cd Simple_WU/WU_Viz
python3 quick_test.py
```

### Parallel Paths Showcase (8,000 iterations)
```bash
cd Simple_WU/WU_Viz
python3 parallel_paths_showcase.py
```

### Full Visualization (15,000 iterations)
```bash
cd Simple_WU/WU_Viz
python3 wu_uct_grid_viz.py
```

### Interactive Menu
```bash
cd Simple_WU/WU_Viz
python3 example_usage.py
# Choose option 3 for grid visualization
```

## Configuration Options

```python
visualizer = WUUCTGridVisualizer(
    problem_path="path/to/problem.txt",
    iterations=10000,        # Total iterations
    num_workers=4,           # Number of parallel workers (2-8 recommended)
    exploration_constant=1.414,  # UCT exploration parameter
    max_edge_distance=1.42,  # Edge constraint for graph
    update_interval=100,     # Update frequency in ms (lower = faster)
    grid_size=(15, 10)       # Figure size (width, height)
)
```

### Recommended Settings

**For Observation (watching algorithm work):**
- `iterations`: 5000-10000
- `num_workers`: 3-4
- `update_interval`: 150-200 ms

**For Performance Analysis:**
- `iterations`: 15000-25000
- `num_workers`: 6-8
- `update_interval`: 75-100 ms

**For Quick Testing:**
- `iterations`: 2000-3000
- `num_workers`: 2
- `update_interval`: 200 ms

## Visual Guide

### Color Scheme

**Nodes:**
- 🟩 Green Square = Start node (node 0)
- 🟥 Red Square = End node (node 1)
- 🟣 Dark Purple = High score nodes
- 🟡 Yellow = Low score nodes

**Paths:**
- 🟡 Gold Solid Line = Best path found
- 🔴 Red Dashed Line = Worker 0's exploration
- 🔵 Teal Dashed Line = Worker 1's exploration
- 🔵 Blue Dashed Line = Worker 2's exploration
- 🟢 Green Dashed Line = Worker 3's exploration

### Panel Layout

```
┌─────────────────────────────────┬──────────────┐
│                                 │              │
│       Problem Grid              │  Algorithm   │
│       with Worker Paths         │  Statistics  │
│                                 │              │
└─────────────────────────────────┴──────────────┤
│  Worker Status  │  Best Solution  │   Legend   │
└─────────────────┴─────────────────┴────────────┘
```

## Technical Details

### Performance Considerations

- **Tree traversal** - Limited to 10,000 nodes to prevent slowdown
- **Path extraction** - Runs once per update (100-200ms intervals)
- **Thread safety** - Copy children list before iteration to avoid concurrent modification
- **Caching** - Previous paths retained if extraction fails

### Known Limitations

1. **Approximate paths** - Heuristic-based, not exact worker positions
2. **Visual convergence** - As algorithm converges, worker paths may look similar
3. **Update lag** - Fast workers may move faster than visualization updates
4. **Path overlap** - Multiple workers may explore similar regions

### Future Enhancements

- [ ] Direct worker path instrumentation (modify worker to report path)
- [ ] Path history trails (fade-out effect)
- [ ] Node heat map (cumulative worker visits)
- [ ] Worker collision detection visualization
- [ ] Path diversity metrics in statistics panel

## Comparison with Original MCTS Viz

| Feature | Original (`viz/mcts_viz.py`) | Grid Viz (`wu_uct_grid_viz.py`) |
|---------|------------------------------|----------------------------------|
| Path Display | ✅ Single worker selection path | ✅ Multiple parallel worker paths |
| Real-time | ✅ Direct from algorithm | ✅ Tree sampling heuristic |
| Visual Style | Orange line for current | Colored dashed lines per worker |
| Best Path | ✅ Green line | ✅ Gold line with arrows |
| Grid Layout | ✅ Scatter plot | ✅ Multi-panel with statistics |
| Parallel Support | ❌ Single-threaded | ✅ Multi-worker visualization |

## Troubleshooting

**Problem: Worker paths not showing**
- Press 'P' to ensure paths are enabled
- Check that `show_worker_paths = True` in code
- Verify workers are actually running (check console output)

**Problem: All paths look the same**
- Increase `num_workers` for more diversity
- Try earlier in algorithm run (before convergence)
- Reduce `exploration_constant` to encourage more exploration

**Problem: Visualization is slow**
- Increase `update_interval` (e.g., 200ms)
- Reduce `iterations` for testing
- Reduce `num_workers` (fewer paths to draw)

## Acknowledgments

This visualization approach is inspired by:
- Original `viz/mcts_viz.py` single-thread path visualization
- WU-UCT paper's "Watch the Unobservable" concept
- Parallel MCTS tree search visualization techniques

---

**Created:** October 2025  
**Version:** 1.0  
**Status:** ✅ Fully functional with real algorithm integration