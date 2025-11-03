"""
WU-UCT Tree Visualization

Adapted from the MCTS visualization tools to show the development of 
the WU-UCT shared tree across parallel workers. Shows both completed 
visits and pending simulations (unobserved samples).
"""

import math
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
import numpy as np
import sys
import os

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
simple_wu_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(simple_wu_dir)
sys.path.extend([project_root, simple_wu_dir])

from orienteering.orienteering_traditional import OrienteeringProblem
from simple_wu_coordinator import SimpleWUUCT
from simple_wu_worker import SimpleWUWorker


# ---- Config ----
PROBLEM_PATH = "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
ITERATIONS = 10000
INITIAL_MAX_DEPTH = 8
MAX_NODES = 500  # Limit nodes to prevent overcrowding


def collect_wu_tree(root, max_depth):
    """
    Traverse the WU-UCT tree up to max_depth from root.
    
    Args:
        root: WUUCTNode root of the tree
        max_depth: Maximum depth to traverse
        
    Returns:
        nodes: List of WUUCTNode objects
        edges: List of (parent, child) tuples
    """
    nodes = []
    edges = []
    if root is None:
        return nodes, edges

    stack = [(root, 0)]
    seen = set()
    while stack and (MAX_NODES is None or len(nodes) < MAX_NODES):
        node, depth = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        nodes.append(node)
        if depth < max_depth:
            # Add children to stack (reversed for consistent left-to-right layout)
            for c in reversed(node.children):
                edges.append((node, c))
                stack.append((c, depth + 1))
    return nodes, edges


def layout_wu_tree(root, max_depth):
    """
    Compute a layered tree layout for WU-UCT tree.
    
    Args:
        root: WUUCTNode root of the tree
        max_depth: Maximum depth to include
        
    Returns:
        pos: Dictionary mapping node -> (x, y) position
        nodes: List of nodes in the layout
        edges: List of (parent, child) edges
    """
    nodes, edges = collect_wu_tree(root, max_depth)
    if not nodes:
        return {}, [], []

    # Build depth mapping using BFS
    depth_map = {root: 0}
    by_depth = {0: [root]}
    queue = [root]
    seen = {root}
    
    while queue:
        cur = queue.pop(0)
        d = depth_map[cur]
        if d >= max_depth:
            continue
        for c in cur.children:
            if c not in seen:
                seen.add(c)
                depth_map[c] = d + 1
                by_depth.setdefault(d + 1, []).append(c)
                queue.append(c)

    # Assign positions
    pos = {}
    max_d = max(depth_map.values()) if depth_map else 0
    
    for d in range(0, max_d + 1):
        level = by_depth.get(d, [])
        n = max(1, len(level))
        for i, node in enumerate(level):
            x = (i + 1) / (n + 1)  # Spread evenly across [0,1]
            y = 1.0 - (d / max(1, max_d)) if max_d > 0 else 0.5
            pos[node] = (x, y)

    return pos, nodes, edges


def wu_node_label(node):
    """
    Create label for WU-UCT node showing key information.
    
    Args:
        node: WUUCTNode to create label for
        
    Returns:
        String label with node info
    """
    try:
        # Get last node in path (current location)
        last = node.state.path[-1] if node.state.path else "S"
    except Exception:
        last = "?"
    
    # Basic visit information
    visits = node.visits
    pending = getattr(node, 'pending_simulations', 0)
    
    # Show visits and pending simulations if any
    if pending > 0:
        return f"{last}\nN:{visits}+{pending}"
    else:
        return f"{last}\nN:{visits}"


def get_node_color(node, active_workers=None):
    """
    Determine node color based on WU-UCT state.
    
    Args:
        node: WUUCTNode to color
        active_workers: List of worker info (optional)
        
    Returns:
        Color string for matplotlib
    """
    # Root node is always special
    if hasattr(node, 'parent') and node.parent is None:
        return 'red'
    
    # Check if node has pending simulations (unobserved samples)
    pending = getattr(node, 'pending_simulations', 0)
    if pending > 0:
        return 'orange'  # Node with pending work
    
    # Color by expansion state
    if node.children:
        return 'lightblue'  # Expanded node
    else:
        return 'lightgreen'  # Leaf node


def get_node_size(node):
    """
    Determine node size based on visit count and pending simulations.
    
    Args:
        node: WUUCTNode to size
        
    Returns:
        Size value for matplotlib scatter plot
    """
    visits = node.visits
    pending = getattr(node, 'pending_simulations', 0)
    
    # Base size on total activity (visits + pending)
    total_activity = visits + pending
    
    # Scale size logarithmically to prevent huge nodes
    if total_activity <= 1:
        return 80
    else:
        return min(200, 80 + 30 * math.log10(total_activity))


class WUUCTTreeVisualizer:
    """
    Real-time visualization of WU-UCT tree development.
    
    Shows the shared tree as it's built by parallel workers,
    highlighting pending simulations and worker activity.
    """
    
    def __init__(self, problem_path, iterations=10000, num_workers=4, 
                 initial_max_depth=8, max_nodes=200):
        """
        Initialize the WU-UCT tree visualizer.
        
        Args:
            problem_path: Path to orienteering problem file
            iterations: Total iterations to run
            num_workers: Number of parallel workers
            initial_max_depth: Initial depth limit for display
            max_nodes: Maximum nodes to show (prevents overcrowding)
        """
        self.problem_path = problem_path
        self.iterations = iterations
        self.num_workers = num_workers
        self.initial_max_depth = initial_max_depth
        self.max_nodes = max_nodes
        
        # Load problem and create solver with distance constraint
        nodes, budget = OrienteeringProblem.load_problem(problem_path)
        # Create problem with max edge distance of 1.42 (orienteering constraint)
        self.problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)
        
        # Pass the budget as max_distance to the WU-UCT solver for path length constraint
        self.solver = SimpleWUUCT(self.problem, num_workers=num_workers, max_distance=budget)
        
        # Visualization state
        self.paused = False
        self.max_depth = initial_max_depth
        self.show_labels = True
        self.iteration_count = 0
        self.algorithm_started = False
        self.workers_running = False
        
        # Artist caches
        self.edge_lines = []
        self.node_scat = None
        self.texts = []
        
    def start_algorithm(self):
        """Start the WU-UCT algorithm for real-time visualization."""
        # For real-time visualization, we'll run small batches of iterations
        # This allows us to see the tree grow incrementally
        self.workers_running = True
        self.batch_size = 50  # Run 50 iterations per batch
        
    def run_algorithm_batch(self):
        """Run a small batch of algorithm iterations."""
        if self.iteration_count >= self.iterations or not self.workers_running:
            return
            
        # Calculate remaining iterations
        remaining = min(self.batch_size, self.iterations - self.iteration_count)
        
        try:
            # Create temporary workers for this batch
            iterations_per_worker = max(1, remaining // self.num_workers)
            remainder = remaining % self.num_workers
            
            batch_workers = []
            for i in range(self.num_workers):
                worker_iterations = (iterations_per_worker + 1 
                                   if i < remainder 
                                   else iterations_per_worker)
                
                if worker_iterations > 0:
                    worker = SimpleWUWorker(
                        problem=self.problem,
                        root=self.solver.root,
                        worker_id=i,
                        iterations_per_worker=worker_iterations,
                        exploration_constant=self.solver.exploration_constant,
                        max_distance=self.solver.max_distance
                    )
                    batch_workers.append(worker)
                    worker.start()
            
            # Wait for batch to complete
            for worker in batch_workers:
                worker.join()
                
            self.iteration_count += remaining
            
        except Exception as e:
            print(f"Batch execution error: {e}")
            self.workers_running = False
        
    def setup_plot(self):
        """Set up the matplotlib figure and axes."""
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.ax.set_title("WU-UCT Tree Development: space=pause/resume, up/down=depth±1, n=labels on/off")
        self.ax.axis('off')
        
        # Status overlay (top-left)
        self.status_text = self.ax.text(
            0.02, 0.98, "", transform=self.ax.transAxes,
            va='top', ha='left', fontsize=10,
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='black')
        )
        
        # Legend for node colors
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='red', 
                   markersize=10, label='Root Node'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', 
                   markersize=10, label='Pending Simulations'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='lightblue', 
                   markersize=10, label='Expanded Node'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='lightgreen', 
                   markersize=10, label='Leaf Node')
        ]
        self.ax.legend(handles=legend_elements, loc='upper right')
        
    def on_key(self, event):
        """Handle keyboard input for interactive control."""
        if event.key == ' ':
            self.paused = not self.paused
        elif event.key == 'up':
            self.max_depth = min(self.max_depth + 1, 20)
        elif event.key == 'down':
            self.max_depth = max(1, self.max_depth - 1)
        elif event.key and event.key.lower() == 'n':
            self.show_labels = not self.show_labels
    
    def update_frame(self, frame):
        """Update function for animation."""
        # Start algorithm if not started
        if not self.algorithm_started and not self.paused:
            self.start_algorithm()
            self.algorithm_started = True
        
        # Run algorithm batch if not paused and still running
        if not self.paused and self.workers_running and self.iteration_count < self.iterations:
            self.run_algorithm_batch()
        
        # Get current tree layout
        pos, nlist, elist = layout_wu_tree(self.solver.root, self.max_depth)
        
        # Clear previous artists
        for ln in self.edge_lines:
            ln.remove()
        self.edge_lines = []
        
        if self.node_scat is not None:
            self.node_scat.remove()
            
        for t in self.texts:
            t.remove()
        self.texts = []
        
        if not nlist:
            return []
        
        # Draw edges
        for p, c in elist:
            if p in pos and c in pos:
                x1, y1 = pos[p]
                x2, y2 = pos[c]
                ln = Line2D([x1, x2], [y1, y2], color='gray', linewidth=1, alpha=0.6)
                self.ax.add_line(ln)
                self.edge_lines.append(ln)
        
        # Draw nodes
        X = [pos[n][0] for n in nlist]
        Y = [pos[n][1] for n in nlist]
        sizes = [get_node_size(n) for n in nlist]
        colors = [get_node_color(n) for n in nlist]
        
        self.node_scat = self.ax.scatter(X, Y, s=sizes, c=colors, 
                                        alpha=0.8, zorder=3, edgecolors='black')
        
        # Add labels if enabled
        if self.show_labels:
            for n in nlist:
                x, y = pos[n]
                txt = self.ax.text(x, y, wu_node_label(n), fontsize=8, 
                                 ha='center', va='center', color='black', weight='bold')
                self.texts.append(txt)
        
        # Update status text
        total_nodes = len(nlist)
        pending_total = sum(getattr(n, 'pending_simulations', 0) for n in nlist)
        
        try:
            # Get best path information
            best_node = self.solver.root
            # Simple traversal to find best leaf
            current = best_node
            while current.children:
                current = max(current.children, 
                            key=lambda x: x.total_reward / max(1, x.visits))
            
            best_score = current.total_reward / max(1, current.visits)
            path_length = len(current.state.path)
            
            status_info = (f"Iterations: {self.iteration_count}/{self.iterations} | "
                          f"Workers: {self.num_workers} | Depth: {self.max_depth}\n"
                          f"Nodes: {total_nodes} | Pending: {pending_total}\n"
                          f"Best Score: {best_score:.2f} | Path Length: {path_length}")
        except Exception as e:
            status_info = f"Iterations: {self.iteration_count}/{self.iterations} | Depth: {self.max_depth}"
        
        self.status_text.set_text(status_info)
        
        # Debug output (remove this later)
        if frame % 20 == 0:  # Print every 20 frames
            print(f"Frame {frame}: Iterations={self.iteration_count}, Root visits={self.solver.root.visits}, "
                  f"Root children={len(self.solver.root.children)}, Total nodes={len(nlist)}")
        
        return [self.node_scat, *self.edge_lines, *self.texts, self.status_text]
    
    def run(self):
        """Start the visualization."""
        self.setup_plot()
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)
        
        # Create animation
        ani = animation.FuncAnimation(
            self.fig, self.update_frame, interval=100, blit=False
        )
        
        plt.tight_layout()
        plt.show()
        
        return ani


def main():
    """Main function to run the WU-UCT tree visualization."""
    visualizer = WUUCTTreeVisualizer(
        problem_path=PROBLEM_PATH,
        iterations=ITERATIONS,
        num_workers=4,
        initial_max_depth=INITIAL_MAX_DEPTH,
        max_nodes=MAX_NODES
    )
    
    print("WU-UCT Tree Visualization")
    print("Controls:")
    print("  SPACE - Pause/Resume")
    print("  UP/DOWN - Increase/Decrease depth")
    print("  N - Toggle node labels")
    print()
    
    ani = visualizer.run()
    return ani


if __name__ == "__main__":
    main()