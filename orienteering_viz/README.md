# Parallel MCTS Orienteering Problem Visualizer

An interactive, high-performance web visualizer for the **Orienteering Problem (OP)** with **Parallel Monte Carlo Tree Search (MCTS)**.

---

## Quickstart & Launching

You can run the visualizer using any of the following methods:

### Option 1: Direct Double-Click (Windows Batch)
Double-click `open_orienteering_viz.bat` in the root repository directory. It will automatically detect Google Chrome or Microsoft Edge and open the visualizer immediately.

### Option 2: Local Python Server & Discovery API
Run the Python launcher in your terminal:
```bash
python run_orienteering_viz.py
```
This serves the application at `http://localhost:8081` with live REST endpoints (`/api/benchmarks` and `/api/benchmark?path=...`) to dynamically discover and stream any benchmark file from `OP_Benchmark_Set`.

### Option 3: Direct File Opening
Open `orienteering_viz/index.html` directly in any modern web browser (Chrome, Edge, Firefox, Safari).

---

## Key Features

### 1. Full Parallel MCTS Algorithm Suite
- **Single UCT**: Standard sequential MCTS with UCB1 exploration. **Strictly single-threaded (1 thread)** — worker selection is locked to 1.
- **Tree-Parallel UCT**: Shared central search tree with worker lock contention tracking across 2–16 threads.
- **Virtual Loss (VL-UCT)**: Dynamic path penalties ($L$) applied during selection to divert concurrent workers down alternative, diverse routes and prevent redundant exploration.
- **WU-UCT (Weighted Update)**: Lock-free asynchronous coordination separating Expansion and Simulation workers via a dedicated WorkUnit queue, updating unobserved counts ($O$) in the tree.
- **Root-Parallel UCT**: Independent parallel search trees aggregated at the root for ensemble decisions.

### 2. What is the Simulation (Rollout) Policy?
In MCTS **Phase 3 (Simulation)**, the tree has only been built up to a shallow leaf state. To evaluate how promising that partial route is without building millions of nodes, the algorithm executes a rapid **rollout** from that leaf state all the way to the terminal END node (or until the travel budget is exhausted). The **Simulation Policy** controls how decisions are made during this fast rollout:
- **Greedy Score/Distance Ratio (Heuristic)**: Greedily hops to neighbor nodes with the highest $\frac{\text{Score}}{\text{Distance}}$ ratio (with 80% greed / 20% exploration) while reserving sufficient budget to return to End. Yields significantly faster convergence to high-quality tours.
- **Score-Biased Weighted Rollout**: Chooses candidate moves with probability proportional to the node's reward score ($P(i) \propto \text{Score}_i$). Prioritizes high-reward hubs while maintaining stochastic variety.
- **Pure Uniform Random**: Traditional textbook MCTS rollout: every feasible next move has equal probability ($1/K$). Fully unbiased, but exhibits high variance on large benchmark topologies.

### 3. Universal Benchmark Set Support
Load **ANY** problem from **ANY** benchmark set:
- **Pre-packaged Catalog**:
  - `sample`: `sample_6_small.txt` (ideal for inspecting every branch), `sample_30.txt`
  - `Tsiligirides_1`: Budgets 15, 30, 50, 85
  - `set_64_1`: Budgets 15, 30, 50, 80
  - `set_100_1`: Budgets 20, 40, 60
  - `grid_patterns`: Center peak, Checkerboard, Concentric Ring, Diagonal Ridge
- **Custom File Upload**: Drag-and-drop or browse ANY `.txt` benchmark file from disk.
- **Paste Benchmark**: Direct raw text paste modal.
- **Procedural Generator**: On-the-fly synthetic problem generator (clusters, corridors, random).

### 4. Dual Interactive Visualizations
- **2D Problem Map**:
  - Interactive Canvas with high-DPI scaling, Pan, and Zoom.
  - Start node (Green, 0) and End node (Red, 1) with score badges.
  - Live animated trails of active parallel workers.
  - Rollout simulation paths during the simulation phase.
  - Glowing **Current Best Tour** with direction arrows and step indices.
  - Interactive hover tooltips showing node coordinates, scores, and feasibility.
- **Hierarchical MCTS Tree**:
  - Responsive SVG tree with Pan, Zoom, Fit, Center, and Depth limit filtering.
  - Node cards displaying Action (visited node ID), visits ($N$), total reward ($Q$), and average reward ($Q/N$).
  - Heatmap color grading based on reward quality.
  - Virtual loss indicators ($L$), unobserved counts ($O$), and active worker badges.
  - Click any node to inspect its live mathematical breakdown in the **Formula Inspector**!

### 4. Interactive Formula Inspector
Clicking any node in the search tree reveals the exact live mathematical formula:
$$\text{UCT} = \frac{Q}{N} + c \sqrt{\frac{\ln N_p}{N}} - \frac{L}{N + V} + \text{WU Corrections}$$
with live numerical values for $Q$, $N$, $N_p$, $c$, $L$, $V$, and $O$.

### 5. Analytics & Live Event Feed
- **Convergence Plot**: Best Tour Score vs. Iteration curve.
- **Best Route Chips**: Ordered sequence of visited nodes from Start to End.
- **Budget Utilization Gauge**: Distance used vs. $T_{max}$.
- **Search Event Log**: Streaming real-time audit feed of expansions, rollouts, and backpropagations.
