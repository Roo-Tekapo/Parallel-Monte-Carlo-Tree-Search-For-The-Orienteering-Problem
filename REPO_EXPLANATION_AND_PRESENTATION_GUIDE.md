# Parallel Monte Carlo Tree Search for the Orienteering Problem: Complete Architecture & Presentation Guide

> **Project Origin:** University Capstone Research Project  
> **Domain:** Strategic Robotics Mission Planning & Combinatorial Optimization  
> **Key Comparison:** Root Parallel, Tree-Parallel, Virtual Loss (VL-UCT), and WU-UCT (Decoupled Queue)  

---

## 1. Executive Summary

This repository investigates **parallelization strategies for Monte Carlo Tree Search (MCTS)** applied to the **Orienteering Problem (OP)**—an NP-hard combinatorial optimization problem central to autonomous robotic mission planning (e.g., planetary rovers, autonomous underwater vehicles, and search-and-rescue UAVs).

In robotics, an autonomous agent operating under strict energy/battery/time constraints must plan a trajectory that collects the maximum total reward from a set of points of interest and safely reaches a designated recovery terminal.

### The Research Question:
> *"How do different shared-tree parallelization schemes (Standard Mutex Locking, Virtual Loss, and Decoupled Asynchronous WU-UCT) compare against embarrassingly parallel Root Parallelization in terms of throughput, scalability, and solution quality?"*

---

## 2. Problem Formulation: The Orienteering Problem (OP)

The Orienteering Problem combines the characteristics of two classic problems:
1. **The 0/1 Knapsack Problem**: Selecting a subset of valuable items within a capacity constraint.
2. **The Traveling Salesperson Problem (TSP)**: Determining the shortest route visiting the chosen subset.

```
                  (Node 4, Score=15)
                      /        \
                     /          \
   (Node 1, Start) -------> (Node 3, Score=25) -------> (Node 2, Goal)
        |                                                    ^
        \-----------------> (Node 5, Score=10) -------------/
                      [Total Path Distance <= T_max]
```

### Mathematical Formulation:
- Given a set of vertices $V = \{1, 2, \dots, n\}$, where vertex $1$ is the starting point and vertex $2$ is the terminal destination.
- Each vertex $i \in V$ has an associated score (prize) $S_i \ge 0$ (with $S_1 = S_2 = 0$).
- Travel cost $d(i, j)$ represents the Euclidean distance:
  $$d(i, j) = \sqrt{(x_i - x_j)^2 + (y_i - y_j)^2}$$
- An available travel budget $T_{\max} > 0$.
- **Objective:**
  $$\max \sum_{i \in \text{Path}} S_i \quad \text{subject to} \quad \sum_{(i, j) \in \text{Path}} d(i, j) \le T_{\max}$$

### Why Heuristic Tree Search is Essential:
Exact methods like Mixed-Integer Linear Programming (MILP using Gurobi or Google OR-Tools) find proven optimal solutions for small instances ($n < 40$), but their runtime scales exponentially. In field robotics requiring online replanning in dynamic environments, MCTS produces high-quality anytime solutions within tight time budgets.

---

## 3. Monte Carlo Tree Search (MCTS) & The UCT Formula

MCTS builds an asymmetric search tree through repeated stochastic sampling of the state space. Each iteration consists of four classic phases:

```
  [Selection]           [Expansion]          [Simulation]         [Backpropagation]
       (R)                  (R)                  (R)                    (R)
      /   \                /   \                /   \                 ^/   \^
    (A)   (B)            (A)   (B)            (A)   (B)             (A)     (B)
     |                    |                    |                     ^|
    (C)                  (C)                  (C)                   (C)
                          |                    |                      ^
                        [D]*                 [D]                    [D]
                                              | (Random Rollout)
                                             (.)
                                              |
                                           [Reward]
```

1. **Selection:** Starting at the root, recursively traverse child nodes using the **Upper Confidence Bound applied to Trees (UCT)** until a leaf or expandable node is reached.
2. **Expansion:** If the leaf is not terminal, instantiate one or more unvisited child states.
3. **Simulation (Rollout):** Rapidly simulate actions to the end of the mission using a default randomized or heuristic policy.
4. **Backpropagation:** Propagate the rollout reward back up the selected path, incrementing visit counts $N$ and updating cumulative reward $Q$.

### The Standard UCT Formula:
$$\text{UCT}(s, a) = \frac{Q(s, a)}{N(s, a)} + c \sqrt{\frac{\ln N(s)}{N(s, a)}}$$

- **Exploitation Term ($\frac{Q}{N}$):** Favors actions that have historically yielded high average rewards.
- **Exploration Term ($c \sqrt{\frac{\ln N_{\text{parent}}}{N_{\text{child}}}}$):** Favors actions with few visits relative to their parent, preventing premature convergence.
- **Exploration Constant ($c$):** Theoretically $\sqrt{2} \approx 1.414$, tuning the exploration-exploitation balance.

---

## 4. The Parallelization Dilemma

When multiple worker threads attempt to execute MCTS concurrently, two primary bottlenecks arise:
1. **Thread Collision & Redundant Exploration:** Multiple threads reading the same node state simultaneously will compute identical UCT scores and select the identical path, conducting redundant rollouts.
2. **Lock Contention:** Protecting tree data structures with mutexes causes worker threads to serialize, spending more time waiting on locks than doing computation.

---

## 5. Parallel MCTS Strategies Implemented in this Codebase

The repository implements and benchmarks four distinct parallelization paradigms:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         PARALLEL MCTS STRATEGIES                                 │
├──────────────────────────┬───────────────────────────────────────────────────────┤
│ 1. Root Parallel         │ Independent trees per worker; vote at the root.       │
├──────────────────────────┼───────────────────────────────────────────────────────┤
│ 2. Tree-Parallel         │ Shared tree; coarse-grained mutex on node expansion.  │
├──────────────────────────┼───────────────────────────────────────────────────────┤
│ 3. Virtual Loss (VL-UCT) │ Shared tree; temporary pessimistic penalty diverts.   │
├──────────────────────────┼───────────────────────────────────────────────────────┤
│ 4. WU-UCT (Decoupled)    │ Shared tree; Expansion queue → Simulation workers.    │
└──────────────────────────┴───────────────────────────────────────────────────────┘
```

### 1. Root Parallelization (`MCTS/root_parallel_mcts.py`)
- **Mechanism:** Each worker thread maintains its own completely independent search tree. No shared memory, no locks, no inter-thread communication.
- **Decision Phase:** When time expires, visit counts for all legal root moves are summed across all trees:
  $$\text{Action}^* = \arg\max_{a} \sum_{w=1}^{W} N_w(\text{root}, a)$$
- **Pros:** Zero synchronization overhead, embarrassingly parallel, 100% CPU utilization.
- **Cons:** Information learned by Worker A is completely invisible to Worker B.

### 2. Tree-Parallel MCTS (`Tree/tree_parallel_coordinator.py`)
- **Mechanism:** Workers operate on a single shared search tree. A global or per-node mutex lock protects the tree during node expansion and statistics backpropagation.
- **Selection Formula:** Standard UCT.
- **Bottleneck:** High lock contention near the root node, where all threads must frequently acquire locks.

### 3. Virtual Loss: VL-UCT (`VL/vl_coordinator.py`, `VL/vl_node.py`)
- **Mechanism:** When Worker A selects a path down the tree, it immediately applies a **Virtual Loss** penalty ($L$) and increments virtual visits ($V$) along that path before initiating rollout.
- **Formula:**
  $$\text{UCT}_{\text{VL}} = \frac{Q - L}{N + V} + c \sqrt{\frac{\ln N_{\text{parent}}}{N + V}}$$
- **Effect:** The artificial penalty immediately drops the UCT score of that branch. When Worker B runs selection micro-seconds later, it chooses an alternate promising branch instead of colliding with Worker A!
- **Commit:** When Worker A finishes simulation, it removes the virtual loss ($L \to 0, V \to 0$) and backpropagates the actual result ($Q += R, N += 1$).

### 4. WU-UCT: "Watch the Unobservable" (`WU_UCT/wu_uct_coordinator.py`)
- **Mechanism:** Decouples fast tree navigation from slow simulation rollouts using a Producer-Consumer pipeline:
  - **Expansion Workers (Producers):** Perform lock-free tree selection and expansion, generate a `WorkUnit`, and place it on a thread-safe `Queue`.
  - **Simulation Workers (Consumers):** Pull `WorkUnit` items from the queue, run the rollouts independently, and commit results.
- **Two-Phase Commit Protocol:**
  - **Phase 1: Update-Incomplete:** Expansion worker increments an unobserved counter ($O$) on the path.
  - **Phase 2: Update-Complete:** Simulation worker decrements $O$ and atomically increments $N$ and $Q$.
- **Formula:**
  $$\text{UCT}_{\text{WU}} = \frac{Q}{N} + c \sqrt{\frac{\ln (N_{\text{parent}} + O_{\text{parent}})}{N + O}}$$

---

## 6. Key Formulas Comparison

| Algorithm | Selection Formula | Coordination Mechanism |
| :--- | :--- | :--- |
| **Standard UCT** | $\frac{Q}{N} + c \sqrt{\frac{\ln N_p}{N}}$ | Synchronous, locks required |
| **Virtual Loss (VL-UCT)** | $\frac{Q - L}{N + V} + c \sqrt{\frac{\ln N_p}{N + V}}$ | Temporary penalty $L$ & virtual visits $V$ |
| **WU-UCT** | $\frac{Q}{N} + c \sqrt{\frac{\ln(N_p + O_p)}{N + O}}$ | Decoupled queue & unobserved counter $O$ |

---

## 7. Empirical Findings & The Capstone Revelation

A major finding of this capstone research was the empirical performance comparison between shared-tree approaches and Root Parallelization in Python:

### Benchmark Throughput (simulations/sec on `set_64_1_80.txt`, 10K iterations):
| Workers | Root Parallel | Original WU-UCT | Optimized WU-UCT (Fine Locks) | Winner |
| :---: | :---: | :---: | :---: | :---: |
| **1 Worker** | 12,637/s | 1,196/s | 1,893/s | **Root (10.6x)** |
| **2 Workers** | 11,517/s | 3,148/s | 1,139/s | **Root (3.7x)** |
| **4 Workers** | 8,521/s | 2,275/s | 1,808/s | **Root (3.7x)** |
| **8 Workers** | 6,180/s | 4,510/s | 1,681/s | **Root (1.4x)** |

### Why Did Root Parallelization Win in Python?
1. **The Lock Convoy Problem at Root:** In shared-tree MCTS, every completed simulation must backpropagate through the root node. With 8 workers, the root node becomes an extreme bottleneck where threads convoy waiting for lock acquisition.
2. **Python's Global Interpreter Lock (GIL):** Python threads cannot execute pure CPU-bound bytecode truly in parallel. Mutex locking operations incur substantial GIL contention and context-switching overhead.
3. **Fine-Grained Locks Made it Worse:** Adding per-node locks instead of global locks degraded performance with 8 workers because each backpropagation had to acquire and release locks on every ancestor node up to the root.

### Why VL-UCT and WU-UCT Remain Academically & Industrially Vital:
- In compiled environments without a GIL (C++, CUDA, Rust, Go), lock-free atomic CAS (`std::atomic`) allows shared-tree search sharing with near-zero overhead.
- In domains where simulation rollouts are computationally intensive (e.g., deep neural network evaluations in AlphaGo/AlphaZero taking 10-100ms per rollout), tree-sharing prevents massive duplication of expensive GPU inference.

---

## 8. Directory & File Map of the Codebase

```
Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/
├── orienteering/                # Domain models for OP
│   ├── orienteering.py         # Standard OP class (budget, Euclidean distance, scoring)
│   ├── orienteering_no_end.py  # Variant without a fixed terminal node
│   └── orienteering_optimized.py # Precomputed distances & neighbor graphs
├── MCTS/                        # Base Single-Thread & Root Parallel MCTS
│   ├── mcts_base.py            # Baseline single-thread UCT solver
│   ├── mcts_node.py            # Base MCTS node
│   └── root_parallel_mcts.py   # Multi-threaded independent tree solver
├── Tree/                        # Tree-Parallel (Shared Tree with Mutexes)
│   ├── tree_parallel_coordinator.py
│   ├── tree_parallel_worker.py
│   └── tree_parallel_node.py
├── VL/                          # Virtual Loss Implementation (VL-UCT)
│   ├── vl_coordinator.py       # Virtual loss coordinator & auto-tuning
│   ├── vl_worker.py            # Worker with VL penalty acquisition & release
│   └── vl_node.py              # Node tracking per-thread virtual loss
├── WU_UCT/                      # Weighted Update UCT (Asynchronous Decoupled)
│   ├── wu_uct_coordinator.py   # Queue coordinator managing worker pools
│   ├── expansion_worker.py     # Fast tree selection & unobserved tagging (Phase 1)
│   ├── simulation_worker.py    # Asynchronous rollout execution & commit (Phase 2)
│   └── wu_uct_node.py          # Node tracking unobserved simulation count O
├── OP_Benchmark_Set/            # Standard benchmark test instances
│   ├── set_64_1/               # 64-node benchmark instances (Tsiligirides/Chao)
│   ├── set_100_1/              # 100-node benchmark instances
│   └── grid_sample/            # Synthetic grid test topologies
├── testing_solution/            # Validation and optimal ground-truth solvers
│   ├── validate_solution.py    # Verifies budget constraints and calculates score
│   └── solve_optimal.py        # Small-instance optimal branch-and-bound solver
├── tictactoe_viz/               # Interactive Educational Demonstration Application
│   ├── index.html              # Full web UI (Dark mode, SVG Tree, Worker Sim)
│   ├── style.css               # Styling, glassmorphism, animations
│   └── app.js                  # Complete Tic-Tac-Toe MCTS engine & parallel visualizer
├── open_tictactoe_viz.bat       # One-click Windows desktop launcher
└── run_tictactoe_viz.py         # Python HTTP server & launcher
```

---

## 9. How to Demonstrate the Algorithm Using the Tic-Tac-Toe Visualizer

The included interactive visualizer in `tictactoe_viz/` allows you to demonstrate the algorithm live to an interviewer, thesis committee, or team in under 3 minutes.

### Step 1: Launch the Visualizer
Double-click `open_tictactoe_viz.bat` or run:
```bash
python run_tictactoe_viz.py
```
*(Or simply open `tictactoe_viz/index.html` in any browser!)*

### Step 2: Explain the 4 MCTS Phases (Single UCT Mode)
1. Keep the default **Single UCT** algorithm selected.
2. Click **"⏭ Step Phase"** 4 times:
   - **Click 1 (Selection):** Point out the active gold path descending from root using UCT.
   - **Click 2 (Expansion):** Show the new child node appearing on the tree frontier.
   - **Click 3 (Simulation):** Point to the **Rollout Simulation Preview** board showing the rapid random moves played to terminal state.
   - **Click 4 (Backprop):** Watch visit counts $N$ and rewards $Q$ update up to the root.

### Step 3: Demonstrate Virtual Loss (VL-UCT)
1. Switch algorithm to **"Virtual Loss (VL-UCT)"**.
2. Explain to the audience: *"In a naive parallel search, Worker 1 and Worker 2 both want the center square [1,1] because it has the highest win rate. Watch how Virtual Loss solves this without locks."*
3. Click **"⏭ Step Phase"**:
   - Worker 1 selects the center square [1,1] and applies Virtual Loss penalty ($L=0.20, V=1$).
   - The UI immediately shows **"⚡ Collision avoided! Worker #2 diverted to alternate child"**.
   - Show the **UCT Formula Inspector** on the right: The $-(L / (N+V))$ term mathematically depresses the score, nudging Worker 2 to explore a corner move.
   - On backprop, the penalty clears and true rollout reward is committed.

### Step 4: Demonstrate Continuous Search & AI Decision
1. Click **"▶ Run"** and watch the search tree grow in real time with hundreds of simulations per second.
2. Click **"🤖 AI Choose Best Move"**: The AI selects the move with the highest visit count ($N$), plays it on the board, and advances the game.
3. Switch to **Custom Setup Mode** to set up a defensive fork or winning block, and show that MCTS reliably finds the optimal tactical move.
