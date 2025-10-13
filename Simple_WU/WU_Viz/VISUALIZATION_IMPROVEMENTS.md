# WU-UCT Grid Visualization Improvements

## Overview
The WU-UCT grid visualization has been significantly enhanced to provide better visual feedback during algorithm execution, similar to the successful `viz/mcts_viz.py` implementation. The algorithm was previously running too fast to observe, and the visualization wasn't showing exploration activity clearly.

## Key Improvements

### 1. **Step-by-Step Execution Mode** ⏱️
- **Problem**: Algorithm ran at full speed in background thread, making it impossible to see exploration
- **Solution**: Added `step_by_step` mode that synchronizes algorithm execution with animation frames
- Each animation frame now runs a configurable number of iterations (default: 5)
- Naturally slows down visualization to human-observable speed
- Can still use fast mode by setting `step_by_step=False`

### 2. **Real-Time Selection Path Visualization** 🎯
- **Problem**: Only showed final best path, not current exploration
- **Solution**: Added tracking of worker selection paths during tree traversal
- Shows thin, bright colored lines for each worker's current selection path
- Similar to orange selection line in `mcts_viz.py`
- Each worker gets a distinct color from the palette
- Toggle with 'S' key

### 3. **Node Visit Count Overlays** 📊
- **Problem**: No indication of which nodes are being explored
- **Solution**: Added visit count display beneath each node
- Counts are aggregated across all tree nodes ending at the same graph node
- Color intensity indicates relative activity (darker = more visits)
- Similar to the visit/avg display in `mcts_viz.py`

### 4. **Interactive Speed and Pause Controls** ⏯️
- **Problem**: No way to control visualization speed or pause
- **Solution**: Comprehensive keyboard controls added:
  - `SPACE` - Pause/Resume execution
  - `+` or `=` - Speed up (doubles iterations per frame)
  - `-` - Slow down (halves iterations per frame)
  - `P` - Toggle worker paths display
  - `S` - Toggle selection paths display
- Status indicators show current state (RUNNING, PAUSED, COMPLETED)

### 5. **Enhanced Node Activity Highlighting** 🎨
- **Problem**: Nodes didn't show when they were being actively explored
- **Solution**: Multi-level highlighting system:
  - **Gold border (thick)**: Nodes in current best path
  - **Magenta border (medium)**: Nodes currently being explored (in selection paths)
  - **Orange border (thin)**: Nodes in worker exploration paths
  - **Black border (default)**: Inactive nodes

### 6. **Improved Statistics Display** 📈
- Shows execution mode (Step/Fast)
- Shows current speed multiplier and iterations per frame
- Progress percentage
- Real-time status with emoji indicators (▶ ⏸ ✓)
- Clearer formatting with better visual hierarchy

## Usage

### Basic Usage
```python
from wu_uct_grid_viz import WUUCTGridVisualizer
import math

visualizer = WUUCTGridVisualizer(
    problem_path='../../OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt',
    iterations=10000,
    num_workers=4,
    exploration_constant=math.sqrt(2),
    max_edge_distance=1.42,
    update_interval=50,  # 50ms between frames
    grid_size=(15, 10),
    step_by_step=True,  # Enable step-by-step mode
    iterations_per_frame=5  # Start with 5 iterations per frame
)

visualizer.run()
```

### Running from Command Line
```bash
cd Simple_WU/WU_Viz
python3 wu_uct_grid_viz.py
```

### Interactive Controls While Running

| Key | Action |
|-----|--------|
| `SPACE` | Pause/Resume |
| `+` or `=` | Speed up (2x) |
| `-` | Slow down (0.5x) |
| `P` | Toggle worker paths |
| `S` | Toggle selection paths |

### Configuration Options

#### Step-by-Step Mode (Recommended for Visualization)
```python
step_by_step=True
iterations_per_frame=5  # Lower = slower, higher = faster
update_interval=50  # milliseconds between frames
```

#### Fast Mode (For Quick Results)
```python
step_by_step=False  # Algorithm runs in background thread at full speed
```

## Visual Elements

### Path Types
1. **Best Path** (Gold, thick line): Current best solution found
2. **Selection Paths** (Colored, thin lines): Active exploration by each worker
3. **Worker Paths** (Colored, dashed lines): Historical exploration paths

### Node Indicators
- **Node ID**: Large text in center
- **Visit Count**: Small blue text below (darker = more visits)
- **Border Color**: Indicates activity level
- **Size**: Based on node score (larger = higher reward)

### Color Scheme
- **Green square**: Start node
- **Red square**: End/target node
- **Viridis gradient**: Regular nodes (darker = higher score)
- **Worker colors**: Red, Teal, Blue, Green, Yellow, Pink, Light Blue, Purple

## Technical Details

### Step-by-Step Implementation
Instead of running workers as threads, the visualization:
1. Creates worker objects without starting their threads
2. Calls `worker._perform_iteration()` directly from animation update
3. Tracks selection paths by sampling the tree after each iteration
4. Updates visualization synchronously with algorithm progress

### Performance Considerations
- Default 5 iterations/frame gives ~100 iters/sec at 50ms update interval
- Can increase with `+` key for faster exploration
- Tree traversal for statistics is limited to prevent slowdown
- Concurrent modification protection when reading tree state

### Comparison with mcts_viz.py
Similar features implemented:
- ✅ Step-by-step execution (1 iteration per frame in mcts_viz)
- ✅ Selection path visualization (orange line)
- ✅ Current node highlight (magenta)
- ✅ Node visit counts overlay
- ✅ Pause/resume functionality
- ✅ Best path display (green line)

Additional features in WU-UCT version:
- ✅ Multi-worker visualization (multiple colors)
- ✅ Worker status panel
- ✅ Speed control (+/- keys)
- ✅ Selection path toggle
- ✅ Enhanced statistics panel

## Troubleshooting

### Visualization appears frozen
- Check if paused (press SPACE)
- Check status panel for PAUSED indicator

### Algorithm running too fast
- Press `-` to slow down
- Reduce `iterations_per_frame` in constructor

### Algorithm running too slow
- Press `+` to speed up
- Increase `iterations_per_frame` in constructor
- Consider using `step_by_step=False` for fast mode

### Paths not showing
- Press `P` to toggle worker paths
- Press `S` to toggle selection paths
- Check that algorithm is running (not COMPLETED)

### High CPU usage
- This is normal in step-by-step mode
- Increase `update_interval` for less frequent updates
- Use fast mode for long runs

## Future Enhancements
- [ ] Replay mode to review completed runs
- [ ] Save/load visualization state
- [ ] Heat map of node exploration
- [ ] Tree structure visualization panel
- [ ] Real-time worker thread monitoring
- [ ] Export animation to video
- [ ] Adjustable animation speed during replay

## Credits
Inspired by the successful `viz/mcts_viz.py` implementation.
Enhanced for parallel WU-UCT algorithm visualization.
