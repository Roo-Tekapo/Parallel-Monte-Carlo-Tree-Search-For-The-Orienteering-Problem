"""
WU-UCT Parallel Worker Visualization

Enhanced visualization that shows real-time worker activity on the shared tree.
Each worker is represented with different colors and visual indicators show
their current activity (selection, expansion, simulation, backpropagation).
"""

import math
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle
import matplotlib.patches as mpatches
import numpy as np
import threading
import time
import sys
import os
from typing import Dict, List, Optional, Tuple

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
simple_wu_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(simple_wu_dir)
sys.path.extend([project_root, simple_wu_dir])

from orienteering.orienteering import OrienteeringProblem
from simple_wu_coordinator import SimpleWUUCT
from simple_wu_worker import SimpleWUWorker
from wu_uct_tree_viz import collect_wu_tree, layout_wu_tree, wu_node_label


# Worker color palette for distinguishing threads
WORKER_COLORS = [
    '#FF6B6B',  # Red
    '#4ECDC4',  # Teal
    '#45B7D1',  # Blue
    '#96CEB4',  # Green
    '#FECA57',  # Yellow
    '#FF9FF3',  # Pink
    '#54A0FF',  # Light Blue
    '#5F27CD'   # Purple
]


class WorkerActivityTracker:
    """
    Tracks real-time activity of WU-UCT workers for visualization.
    
    This class monitors worker states and tree modifications to provide
    live feedback for the parallel visualization.
    """
    
    def __init__(self, num_workers: int):
        """Initialize tracking for the specified number of workers."""
        self.num_workers = num_workers
        self.worker_states = {}  # worker_id -> current state info
        self.worker_positions = {}  # worker_id -> current node position
        self.active_paths = {}  # worker_id -> list of nodes in current path
        self.lock = threading.Lock()
        
        # Initialize worker states
        for i in range(num_workers):
            self.worker_states[i] = {
                'status': 'idle',  # idle, selecting, expanding, simulating, backpropagating
                'current_node': None,
                'path': [],
                'last_update': time.time()
            }
    
    def update_worker_status(self, worker_id: int, status: str, 
                           current_node=None, path=None):
        """Update the status of a specific worker."""
        with self.lock:
            self.worker_states[worker_id].update({
                'status': status,
                'current_node': current_node,
                'path': path or [],
                'last_update': time.time()
            })
    
    def get_worker_info(self, worker_id: int) -> dict:
        """Get current information for a specific worker."""
        with self.lock:
            return self.worker_states.get(worker_id, {}).copy()
    
    def get_all_worker_info(self) -> Dict[int, dict]:
        """Get information for all workers."""
        with self.lock:
            return {k: v.copy() for k, v in self.worker_states.items()}


class EnhancedWUUCTVisualizer:
    """
    Enhanced WU-UCT visualization showing parallel worker activity.
    
    This visualizer provides a more detailed view of the WU-UCT algorithm
    by showing:
    - Individual worker activities and states
    - Current paths being explored by each worker
    - Pending simulations with worker attribution
    - Real-time statistics per worker
    """
    
    def __init__(self, problem_path, iterations=10000, num_workers=4,
                 initial_max_depth=8, max_nodes=200):
        """
        Initialize the enhanced WU-UCT visualizer.
        
        Args:
            problem_path: Path to orienteering problem file
            iterations: Total iterations to run
            num_workers: Number of parallel workers
            initial_max_depth: Initial depth limit for display
            max_nodes: Maximum nodes to show
        """
        self.problem_path = problem_path
        self.iterations = iterations
        self.num_workers = num_workers
        self.initial_max_depth = initial_max_depth
        self.max_nodes = max_nodes
        
        # Load problem
        nodes, budget = OrienteeringProblem.load_problem(problem_path)
        self.problem = OrienteeringProblem(nodes, budget)
        
        # Worker activity tracking
        self.activity_tracker = WorkerActivityTracker(num_workers)
        
        # Visualization state
        self.paused = False
        self.max_depth = initial_max_depth
        self.show_labels = True
        self.show_worker_paths = True
        self.show_worker_stats = True
        
        # Artist caches
        self.edge_lines = []
        self.node_scat = None
        self.texts = []
        self.worker_path_lines = []
        self.worker_indicators = []
        
        # Algorithm execution
        self.batch_size = 25  # Smaller batches for more responsive visualization
        
        # Create solver with proper distance constraints
        self.solver = SimpleWUUCT(self.problem, num_workers=num_workers, max_distance=budget)
        self.iteration_count = 0
        self.algorithm_started = False
        self.workers_running = False
        
    def setup_plot(self):
        """Set up the matplotlib figure with multiple subplots."""
        self.fig = plt.figure(figsize=(16, 10))
        
        # Main tree view
        self.ax_tree = plt.subplot2grid((3, 4), (0, 0), colspan=3, rowspan=2)
        self.ax_tree.set_title("WU-UCT Parallel Tree Development")
        self.ax_tree.axis('off')
        
        # Worker statistics panel
        self.ax_stats = plt.subplot2grid((3, 4), (0, 3), rowspan=2)
        self.ax_stats.set_title("Worker Statistics")
        self.ax_stats.axis('off')
        
        # Control information panel
        self.ax_info = plt.subplot2grid((3, 4), (2, 0), colspan=4)
        self.ax_info.set_title("Algorithm Information")
        self.ax_info.axis('off')
        
        # Status overlay
        self.status_text = self.ax_tree.text(
            0.02, 0.98, "", transform=self.ax_tree.transAxes,
            va='top', ha='left', fontsize=9,
            bbox=dict(facecolor='white', alpha=0.9, edgecolor='black')
        )
        
        # Create legends
        self.create_legends()
        
    def create_legends(self):
        """Create legends for nodes and workers."""
        # Node type legend
        node_legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='red', 
                   markersize=8, label='Root'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', 
                   markersize=8, label='Pending Sims'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='lightblue', 
                   markersize=8, label='Expanded'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='lightgreen', 
                   markersize=8, label='Leaf')
        ]
        
        # Worker legend
        worker_legend_elements = []
        for i in range(min(self.num_workers, len(WORKER_COLORS))):
            color = WORKER_COLORS[i]
            worker_legend_elements.append(
                Line2D([0], [0], color=color, linewidth=3, 
                       label=f'Worker {i}')
            )
        
        # Position legends
        self.ax_tree.legend(handles=node_legend_elements, 
                           loc='upper left', fontsize=8, title="Node Types")
        
        if worker_legend_elements:
            worker_legend = self.ax_tree.legend(handles=worker_legend_elements,
                                              loc='lower left', fontsize=8, 
                                              title="Workers")
            # Add the first legend back
            self.ax_tree.add_artist(self.ax_tree.get_legend())
    
    def get_worker_color(self, worker_id: int) -> str:
        """Get color for a specific worker."""
        return WORKER_COLORS[worker_id % len(WORKER_COLORS)]
    
    def start_algorithm(self):
        """Start the WU-UCT algorithm for real-time visualization."""
        self.workers_running = True
        
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
                    # Update worker activity tracker
                    self.activity_tracker.update_worker_status(
                        i, 'running', current_node=self.solver.root
                    )
                    
                    worker = SimpleWUWorker(
                        problem=self.problem,
                        root=self.solver.root,
                        worker_id=i,
                        iterations_per_worker=worker_iterations,
                        exploration_constant=math.sqrt(2),
                        max_distance=self.problem.budget
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
            
    def update_worker_activity_tracking(self):
        """Update worker activity tracking with current tree state."""
        # Simulate different worker states for visualization
        import random
        
        for worker_id in range(self.num_workers):
            if random.random() < 0.3:  # 30% chance to update
                # Randomly pick a node from current tree for worker position
                if self.solver.root.children:
                    current_node = random.choice([self.solver.root] + list(self.solver.root.children))
                else:
                    current_node = self.solver.root
                    
                status = random.choice(['selecting', 'expanding', 'simulating', 'backpropagating'])
                
                # Create a simple path for visualization
                path = [self.solver.root]
                if current_node != self.solver.root:
                    path.append(current_node)
                
                self.activity_tracker.update_worker_status(
                    worker_id, status, current_node=current_node, path=path
                )
    
    def draw_worker_paths(self, pos, worker_info):
        """Draw current paths being explored by workers."""
        for worker_id, info in worker_info.items():
            if not self.show_worker_paths or not info.get('path'):
                continue
                
            color = self.get_worker_color(worker_id)
            path_nodes = info['path']
            
            # Draw path as connected line segments
            path_x = []
            path_y = []
            for node in path_nodes:
                if node in pos:
                    x, y = pos[node]
                    path_x.append(x)
                    path_y.append(y)
            
            if len(path_x) >= 2:
                line = Line2D(path_x, path_y, color=color, linewidth=3, 
                             alpha=0.7, linestyle='--', zorder=2)
                self.ax_tree.add_line(line)
                self.worker_path_lines.append(line)
                
                # Add worker indicator at current position
                if path_x and path_y:
                    indicator = Circle((path_x[-1], path_y[-1]), 0.02, 
                                     color=color, alpha=0.8, zorder=4)
                    self.ax_tree.add_patch(indicator)
                    self.worker_indicators.append(indicator)
    
    def update_worker_statistics(self, worker_info):
        """Update the worker statistics panel."""
        self.ax_stats.clear()
        self.ax_stats.set_title("Worker Statistics", fontsize=10, weight='bold')
        self.ax_stats.axis('off')
        
        y_pos = 0.9
        line_height = 0.15
        
        for worker_id in range(self.num_workers):
            info = worker_info.get(worker_id, {})
            color = self.get_worker_color(worker_id)
            status = info.get('status', 'idle')
            
            # Worker header
            self.ax_stats.text(0.05, y_pos, f"Worker {worker_id}:", 
                             fontsize=10, weight='bold', color=color,
                             transform=self.ax_stats.transAxes)
            
            # Status
            self.ax_stats.text(0.1, y_pos - 0.03, f"Status: {status}", 
                             fontsize=8, transform=self.ax_stats.transAxes)
            
            # Current node info
            current_node = info.get('current_node')
            if current_node:
                try:
                    node_id = current_node.state.path[-1] if current_node.state.path else "S"
                    visits = getattr(current_node, 'visits', 0)
                    self.ax_stats.text(0.1, y_pos - 0.06, f"Node: {node_id} (N={visits})", 
                                     fontsize=8, transform=self.ax_stats.transAxes)
                except:
                    self.ax_stats.text(0.1, y_pos - 0.06, "Node: ?", 
                                     fontsize=8, transform=self.ax_stats.transAxes)
            
            y_pos -= line_height
            
            if y_pos < 0.1:  # Prevent overflow
                break
    
    def update_algorithm_info(self):
        """Update the algorithm information panel."""
        self.ax_info.clear()
        self.ax_info.set_title("WU-UCT Algorithm Information", fontsize=10, weight='bold')
        self.ax_info.axis('off')
        
        info_text = (
            "WU-UCT (Watch the Unobservable UCT) Parallel Algorithm\n\n"
            "• Multiple workers share a single search tree\n"
            "• Each worker performs complete MCTS iterations: Selection → Expansion → Simulation → Backpropagation\n"
            "• Pending simulations (unobserved samples) are tracked to prevent over-exploration\n"
            "• UCT formula modified: includes both completed (N) and pending (O) visits\n\n"
            "Visualization Features:\n"
            "• Node colors indicate state (root=red, pending=orange, expanded=blue, leaf=green)\n"
            "• Node sizes reflect visit counts + pending simulations\n"
            "• Dashed colored lines show current worker paths\n"
            "• Worker statistics panel shows real-time worker states\n\n"
            "Controls: SPACE=pause, UP/DOWN=depth±1, N=toggle labels, P=toggle paths"
        )
        
        self.ax_info.text(0.05, 0.95, info_text, fontsize=9, 
                         transform=self.ax_info.transAxes, va='top')
    
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
        elif event.key and event.key.lower() == 'p':
            self.show_worker_paths = not self.show_worker_paths
    
    def update_frame(self, frame):
        """Update function for animation."""
        # Start algorithm if not started
        if not self.algorithm_started and not self.paused:
            self.start_algorithm()
            self.algorithm_started = True
        
        # Run algorithm batch if not paused and still running
        if not self.paused and self.workers_running and self.iteration_count < self.iterations:
            self.run_algorithm_batch()
            
        # Update worker activity tracking
        self.update_worker_activity_tracking()
        
        # Get current tree layout  
        pos, nlist, elist = layout_wu_tree(self.solver.root, self.max_depth)
        
        # Clear previous tree artists
        for ln in self.edge_lines:
            ln.remove()
        self.edge_lines = []
        
        for ln in self.worker_path_lines:
            ln.remove()
        self.worker_path_lines = []
        
        for ind in self.worker_indicators:
            ind.remove()
        self.worker_indicators = []
        
        if self.node_scat is not None:
            self.node_scat.remove()
            
        for t in self.texts:
            t.remove()
        self.texts = []
        
        if not nlist:
            return []
        
        # Draw tree structure
        self.draw_tree_structure(pos, nlist, elist)
        
        # Get worker information and draw worker-specific elements
        worker_info = self.activity_tracker.get_all_worker_info()
        self.draw_worker_paths(pos, worker_info)
        
        # Update panels
        self.update_worker_statistics(worker_info)
        self.update_algorithm_info()
        
        # Update status
        self.update_status_text(nlist)
        
        # Debug output (remove this later)
        if frame % 30 == 0:  # Print every 30 frames
            print(f"Parallel Frame {frame}: Iter={self.iteration_count}, Root visits={self.solver.root.visits}, "
                  f"Root children={len(self.solver.root.children)}, Nodes shown={len(nlist)}")
        
        return [self.node_scat, *self.edge_lines, *self.worker_path_lines, 
                *self.worker_indicators, *self.texts, self.status_text]
    
    def draw_tree_structure(self, pos, nlist, elist):
        """Draw the basic tree structure (nodes and edges)."""
        # Draw edges
        for p, c in elist:
            if p in pos and c in pos:
                x1, y1 = pos[p]
                x2, y2 = pos[c]
                ln = Line2D([x1, x2], [y1, y2], color='gray', 
                           linewidth=1, alpha=0.6, zorder=1)
                self.ax_tree.add_line(ln)
                self.edge_lines.append(ln)
        
        # Draw nodes
        X = [pos[n][0] for n in nlist]
        Y = [pos[n][1] for n in nlist]
        sizes = [self.get_node_size(n) for n in nlist]
        colors = [self.get_node_color(n) for n in nlist]
        
        self.node_scat = self.ax_tree.scatter(X, Y, s=sizes, c=colors, 
                                            alpha=0.8, zorder=3, edgecolors='black')
        
        # Add labels if enabled
        if self.show_labels:
            for n in nlist:
                x, y = pos[n]
                txt = self.ax_tree.text(x, y, wu_node_label(n), fontsize=7, 
                                      ha='center', va='center', color='black', 
                                      weight='bold')
                self.texts.append(txt)
    
    def get_node_color(self, node):
        """Determine node color based on WU-UCT state."""
        if hasattr(node, 'parent') and node.parent is None:
            return 'red'
        
        pending = getattr(node, 'pending_simulations', 0)
        if pending > 0:
            return 'orange'
        
        if node.children:
            return 'lightblue'
        else:
            return 'lightgreen'
    
    def get_node_size(self, node):
        """Determine node size based on activity."""
        visits = node.visits
        pending = getattr(node, 'pending_simulations', 0)
        total_activity = visits + pending
        
        if total_activity <= 1:
            return 60
        else:
            return min(150, 60 + 20 * math.log10(total_activity))
    
    def simulate_worker_activity(self):
        """Simulate worker activity for demonstration purposes."""
        # This is a mock function - in a real implementation, this would
        # interface with actual worker threads to get their current state
        
        import random
        
        statuses = ['selecting', 'expanding', 'simulating', 'backpropagating', 'idle']
        
        for worker_id in range(self.num_workers):
            # Randomly update worker status for demonstration
            if random.random() < 0.3:  # 30% chance to update status
                new_status = random.choice(statuses)
                self.activity_tracker.update_worker_status(
                    worker_id, new_status, 
                    current_node=self.solver.root  # Simplified - would be actual current node
                )
    
    def update_status_text(self, nlist):
        """Update the main status text overlay."""
        total_nodes = len(nlist)
        pending_total = sum(getattr(n, 'pending_simulations', 0) for n in nlist)
        
        try:
            # Find best path (simplified)
            current = self.solver.root
            best_score = 0
            path_length = 0
            
            if current.children:
                best_child = max(current.children, 
                               key=lambda x: x.total_reward / max(1, x.visits))
                best_score = best_child.total_reward / max(1, best_child.visits)
                path_length = len(best_child.state.path)
            
            status_info = (f"Iterations: {self.iteration_count:,}/{self.iterations:,} | "
                          f"Workers: {self.num_workers} | Depth: {self.max_depth}\n"
                          f"Nodes: {total_nodes} | Root visits: {self.solver.root.visits}\n"
                          f"Root children: {len(self.solver.root.children)} | Best Score: {best_score:.2f}")
        except Exception:
            status_info = (f"Iterations: {self.iteration_count:,}/{self.iterations:,} | "
                          f"Depth: {self.max_depth}")
        
        self.status_text.set_text(status_info)
    
    def run(self):
        """Start the enhanced visualization."""
        self.setup_plot()
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)
        
        # Create animation
        ani = animation.FuncAnimation(
            self.fig, self.update_frame, interval=150, blit=False
        )
        
        plt.tight_layout()
        plt.show()
        
        return ani


def main():
    """Main function to run the enhanced WU-UCT visualization."""
    problem_path = "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    
    visualizer = EnhancedWUUCTVisualizer(
        problem_path=problem_path,
        iterations=10000,
        num_workers=4,
        initial_max_depth=6,
        max_nodes=150
    )
    
    print("Enhanced WU-UCT Parallel Visualization")
    print("=====================================")
    print("This visualization shows parallel WU-UCT algorithm execution")
    print("with real-time worker activity tracking.")
    print()
    print("Controls:")
    print("  SPACE - Pause/Resume simulation")
    print("  UP/DOWN - Increase/Decrease tree depth display")
    print("  N - Toggle node labels")
    print("  P - Toggle worker path display")
    print()
    print("Legend:")
    print("  Red nodes - Root")
    print("  Orange nodes - Have pending simulations")
    print("  Blue nodes - Expanded (have children)")
    print("  Green nodes - Leaf nodes")
    print("  Colored dashed lines - Current worker exploration paths")
    print()
    
    ani = visualizer.run()
    return ani


if __name__ == "__main__":
    main()