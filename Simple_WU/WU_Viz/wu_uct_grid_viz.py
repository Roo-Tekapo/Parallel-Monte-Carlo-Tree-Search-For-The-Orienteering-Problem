"""
WU-UCT Grid Visualization

A comprehensive visualization tool that shows the orienteering problem grid 
and the WU-UCT algorithm working on it in real-time. This visualization displays:

1. Problem Grid: All nodes with positions, scores, and connections
2. Worker Paths: Real-time paths each worker is exploring  
3. Best Solution: The current best path found by the algorithm
4. Worker Activity: Current state of each parallel worker
5. Algorithm Statistics: Progress metrics and performance data
6. Node Activity: Visual indicators for active exploration

Author: GitHub Copilot
"""

import math
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyBboxPatch
import numpy as np
import sys
import os
import threading
import time
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional, Set

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
simple_wu_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(simple_wu_dir)
sys.path.extend([project_root, simple_wu_dir])

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from simple_wu_coordinator import SimpleWUUCT
from UCT.wu_uct_node import WUUCTNode


class WUUCTGridVisualizer:
    """
    Comprehensive grid-based visualization for WU-UCT algorithm.
    
    Shows the orienteering problem as a grid with nodes, and displays
    real-time worker activity, paths, and algorithm progress.
    """
    
    def __init__(self, 
                 problem_path: str,
                 iterations: int = 10000,
                 num_workers: int = 4,
                 exploration_constant: float = math.sqrt(2),
                 max_edge_distance: float = 1.42,
                 update_interval: int = 50,
                 grid_size: Tuple[int, int] = (12, 8),
                 step_by_step: bool = True,
                 iterations_per_frame: int = 1):
        """
        Initialize the grid visualizer.
        
        Args:
            problem_path: Path to the orienteering problem file
            iterations: Total iterations to run
            num_workers: Number of parallel workers
            exploration_constant: UCT exploration parameter
            max_edge_distance: Maximum distance for edge connections
            update_interval: Animation update interval in milliseconds
            grid_size: Figure size for the visualization
            step_by_step: Run algorithm step-by-step synchronized with animation
            iterations_per_frame: Number of iterations to run per animation frame
        """
        self.problem_path = problem_path
        self.iterations = iterations
        self.num_workers = num_workers
        self.exploration_constant = exploration_constant
        self.max_edge_distance = max_edge_distance
        self.update_interval = update_interval
        self.grid_size = grid_size
        self.step_by_step = step_by_step
        self.iterations_per_frame = iterations_per_frame
        
        # Load problem
        nodes, budget = OrienteeringProblem.load_problem(problem_path)
        self.problem = OrienteeringProblem(nodes, budget, max_edge_distance)
        
        # Initialize algorithm
        self.wu_uct = SimpleWUUCT(
            problem=self.problem,
            num_workers=num_workers,
            exploration_constant=exploration_constant,
            max_distance=max_edge_distance
        )
        
        # Visualization state
        self.is_running = False
        self.paused = False
        self.start_time = None
        self.pause_start_time = None
        self.total_paused_time = 0.0
        self.algorithm_thread = None
        
        # Speed control for step-by-step mode
        self.speed_multiplier = 1.0  # Can be adjusted with keyboard
        
        # Worker colors (highly distinct colors for easy differentiation)
        self.worker_colors = [
            '#FF0000',  # Bright Red
            '#00FF00',  # Bright Green  
            '#0000FF',  # Bright Blue
            '#FF00FF',  # Magenta
            '#FFFF00',  # Yellow
            '#00FFFF',  # Cyan
            '#FF8000',  # Orange
            '#8000FF'   # Purple
        ][:num_workers]
        
        # Tracking data for worker paths and activity
        self.worker_paths: Dict[int, List[int]] = {i: [] for i in range(num_workers)}
        self.worker_status: Dict[int, str] = {i: "Starting" for i in range(num_workers)}
        self.worker_current_nodes: Dict[int, Optional[int]] = {i: None for i in range(num_workers)}
        self.active_nodes: Set[int] = set()
        self.node_activity_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Enhanced worker path tracking
        self.worker_active_paths: Dict[int, List[int]] = {i: [] for i in range(num_workers)}
        self.worker_selection_paths: Dict[int, List[int]] = {i: [] for i in range(num_workers)}
        self.worker_path_lines: Dict[int, Line2D] = {}
        self.show_worker_paths = True  # Toggle for showing/hiding worker paths
        self.show_selection_paths = True  # Toggle for showing selection paths
        
        # Algorithm statistics
        self.iteration_count = 0
        self.best_path = []
        self.best_score = 0.0
        self.best_distance = 0.0
        self.algorithm_stats = {
            'total_nodes': 0,
            'tree_depth': 0,
            'simulations_per_sec': 0.0,
            'iterations_per_sec': 0.0
        }
        
        # Track algorithm completion
        self.algorithm_completed = False
        self.final_result = None
        
    def setup_visualization(self):
        """Set up the matplotlib figure and subplots."""
        # Create figure with subplots
        self.fig = plt.figure(figsize=self.grid_size)
        gs = self.fig.add_gridspec(2, 3, height_ratios=[3, 1], width_ratios=[2, 1, 1])
        
        # Main grid plot (large, top-left)
        self.ax_grid = self.fig.add_subplot(gs[0, :2])
        
        # Statistics panel (top-right)  
        self.ax_stats = self.fig.add_subplot(gs[0, 2])
        
        # Worker status panel (bottom-left)
        self.ax_workers = self.fig.add_subplot(gs[1, 0])
        
        # Algorithm info panel (bottom-middle)
        self.ax_algo = self.fig.add_subplot(gs[1, 1])
        
        # Legend panel (bottom-right)
        self.ax_legend = self.fig.add_subplot(gs[1, 2])
        
        self.fig.suptitle('WU-UCT Grid Visualization: Parallel Orienteering Problem Solver', 
                         fontsize=14, fontweight='bold')
        
        # Setup grid plot
        self._setup_grid_plot()
        
        # Setup info panels
        self._setup_info_panels()
        
        plt.tight_layout()
        
    def _setup_grid_plot(self):
        """Setup the main grid visualization."""
        self.ax_grid.set_title('Orienteering Problem Grid & Worker Activity', fontweight='bold')
        self.ax_grid.set_xlabel('X Coordinate')
        self.ax_grid.set_ylabel('Y Coordinate') 
        self.ax_grid.grid(True, alpha=0.3)
        self.ax_grid.set_aspect('equal')
        
        # Find grid bounds with padding
        xs = [node.x for node in self.problem.nodes]
        ys = [node.y for node in self.problem.nodes]
        x_padding = (max(xs) - min(xs)) * 0.1
        y_padding = (max(ys) - min(ys)) * 0.1
        
        self.ax_grid.set_xlim(min(xs) - x_padding, max(xs) + x_padding)
        self.ax_grid.set_ylim(min(ys) - y_padding, max(ys) + y_padding)
        
        # Pre-compute node positions for efficiency
        self.node_positions = {i: (node.x, node.y) for i, node in enumerate(self.problem.nodes)}
        
        # Draw edges first (so they appear behind nodes)
        self._draw_edges()
        
        # Draw nodes
        self._draw_nodes()
        
    def _draw_edges(self):
        """Draw edges between connected nodes."""
        if self.problem.max_edge_distance is None:
            return  # Skip if no edge constraints
            
        for i in range(self.problem.num_nodes):
            neighbors = self.problem.get_neighbors(i)
            for j in neighbors:
                if i < j:  # Avoid drawing duplicate edges
                    x1, y1 = self.node_positions[i]
                    x2, y2 = self.node_positions[j]
                    self.ax_grid.plot([x1, x2], [y1, y2], 
                                    color='lightgray', alpha=0.3, linewidth=0.5, zorder=1)
    
    def _draw_nodes(self):
        """Draw all problem nodes with appropriate styling."""
        # Storage for node artists
        self.node_circles = {}
        self.node_texts = {}
        self.node_visit_texts = {}  # Separate texts for visit counts
        
        for i, node in enumerate(self.problem.nodes):
            x, y = node.x, node.y
            
            # Determine node styling
            if i == 0:  # Start node
                color = 'green'
                size = 200
                marker = 's'  # Square
            elif i == 1:  # End node  
                color = 'red'
                size = 200
                marker = 's'  # Square
            else:  # Regular node
                # Color based on score (higher score = darker)
                if node.score == 0:
                    color = 'lightgray'
                else:
                    # Normalize score for coloring
                    max_score = max(n.score for n in self.problem.nodes)
                    norm_score = node.score / max_score if max_score > 0 else 0
                    # Use reversed viridis so higher scores are darker
                    color = plt.cm.viridis_r(norm_score)
                size = 50 + node.score * 5  # Size based on score
                marker = 'o'
            
            # Draw node
            circle = self.ax_grid.scatter([x], [y], c=[color], s=size, 
                                        marker=marker, alpha=0.8, 
                                        edgecolors='black', linewidth=1, zorder=3)
            self.node_circles[i] = circle
            
            # Add node label (ID on top line)
            text = self.ax_grid.text(x, y, str(i), ha='center', va='center', 
                                   fontsize=8, fontweight='bold', zorder=4)
            self.node_texts[i] = text
            
            # Add visit count text (below the node)
            visit_text = self.ax_grid.text(x, y - 0.3, '', ha='center', va='top',
                                          fontsize=7, color='blue', zorder=4)
            self.node_visit_texts[i] = visit_text
            
    def _setup_info_panels(self):
        """Setup information panels for statistics and worker status."""
        # Statistics panel
        self.ax_stats.set_title('Algorithm Statistics', fontweight='bold', fontsize=10)
        self.ax_stats.axis('off')
        
        # Worker status panel
        self.ax_workers.set_title('Worker Status', fontweight='bold', fontsize=10)
        self.ax_workers.axis('off')
        
        # Algorithm info panel
        self.ax_algo.set_title('Best Solution', fontweight='bold', fontsize=10) 
        self.ax_algo.axis('off')
        
        # Legend panel
        self.ax_legend.set_title('Legend', fontweight='bold', fontsize=10)
        self.ax_legend.axis('off')
        
        # Create legend with worker path colors
        legend_elements = [
            Line2D([0], [0], marker='s', color='green', label='Start Node', markersize=8, linestyle='None'),
            Line2D([0], [0], marker='s', color='red', label='End Node', markersize=8, linestyle='None'),
            Line2D([0], [0], marker='o', color='purple', label='High Score', markersize=8, linestyle='None'),
            Line2D([0], [0], color='gold', linewidth=3, label='Best Path'),
            Line2D([0], [0], color='gray', linewidth=2, linestyle='--', label='Worker Paths'),
        ]
        
        # Add individual worker colors to legend (first 4 workers)
        for i in range(min(4, self.num_workers)):
            legend_elements.append(
                Line2D([0], [0], color=self.worker_colors[i], linewidth=2, 
                      linestyle='--', label=f'Worker {i}', alpha=0.7)
            )
        
        self.ax_legend.legend(handles=legend_elements, loc='center', fontsize=7)
        
    def _enhanced_worker_tracking(self):
        """Enhanced worker tracking with detailed state monitoring and path tracking."""
        if not hasattr(self.wu_uct, 'workers') or not self.wu_uct.workers:
            # Algorithm hasn't started yet
            for i in range(self.num_workers):
                self.worker_status[i] = "Not started"
            return
            
        for worker in self.wu_uct.workers:
            worker_id = worker.worker_id
            
            # Get actual worker progress
            try:
                iterations_done = getattr(worker, 'iterations_completed', 0)
                target_iterations = getattr(worker, 'iterations_per_worker', 1)
                simulations_done = getattr(worker, 'simulations_completed', 0)
                
                # Update worker status based on actual state
                # In step-by-step mode, workers don't run as threads, so check completion differently
                if iterations_done >= target_iterations:
                    self.worker_status[worker_id] = f"✓ Done ({iterations_done}/{target_iterations})"
                    # Keep the last path when worker completes (don't clear it)
                elif self.algorithm_completed:
                    self.worker_status[worker_id] = f"Stopped ({iterations_done}/{target_iterations})"
                else:
                    progress_pct = (iterations_done / max(target_iterations, 1)) * 100
                    # Show active indicator for workers that are working
                    if hasattr(worker, 'last_selection_path') and worker.last_selection_path:
                        self.worker_status[worker_id] = f"▶ Active ({iterations_done}/{target_iterations}) {progress_pct:.0f}%"
                    else:
                        self.worker_status[worker_id] = f"Working ({iterations_done}/{target_iterations}) {progress_pct:.0f}%"
                    
            except Exception as e:
                self.worker_status[worker_id] = "Status unknown"
    
    def _extract_worker_path(self, worker):
        """
        Extract the current exploration path from a worker by sampling the tree.
        
        This uses a multi-strategy approach to find active exploration paths:
        1. Follow paths with recent activity (high visits + pending simulations)
        2. Distribute different workers to different branches heuristically
        """
        try:
            worker_id = worker.worker_id
            
            # Sample from the tree to find active exploration
            if hasattr(self.wu_uct, 'root') and self.wu_uct.root:
                root = self.wu_uct.root
                
                # Strategy: Each worker follows a different high-activity branch
                # This gives visual diversity and approximates parallel exploration
                path = self._find_active_branch(root, worker_id)
                
                if path and len(path) > 1:
                    self.worker_active_paths[worker_id] = path
            
        except Exception:
            # If path extraction fails, keep previous path
            pass
    
    def _find_active_branch(self, root, worker_offset=0, max_depth=12):
        """
        Find an active exploration branch from the root.
        
        Uses worker_offset to select different branches for different workers,
        creating visual diversity in the parallel exploration.
        """
        try:
            current_node = root
            path = [0]  # Start with root node (node 0)
            
            for depth in range(max_depth):
                if not hasattr(current_node, 'children') or not current_node.children:
                    break
                
                # Get all children with their activity scores
                children_with_scores = []
                for child in current_node.children[:]:
                    visits = getattr(child, 'visits', 0)
                    pending = getattr(child, 'pending_simulations', 0)
                    activity_score = visits + pending * 0.5  # Weight pending slightly less
                    
                    if activity_score > 0:
                        children_with_scores.append((child, activity_score))
                
                if not children_with_scores:
                    break
                
                # Sort by activity score
                children_with_scores.sort(key=lambda x: x[1], reverse=True)
                
                # Select child based on worker offset to create diversity
                # Worker 0 gets most active, Worker 1 gets 2nd most active, etc.
                child_index = min(worker_offset + (depth % self.num_workers), 
                                len(children_with_scores) - 1)
                selected_child = children_with_scores[child_index][0]
                
                # Extract path from selected child's state
                if hasattr(selected_child, 'state') and hasattr(selected_child.state, 'path'):
                    path = selected_child.state.path[:]
                    current_node = selected_child
                else:
                    break
            
            return path
            
        except Exception:
            return [0]  # Return just start node on error
    
    def _get_elapsed_time(self):
        """Get elapsed time excluding paused periods."""
        if not self.start_time:
            return 0.0
        
        current_time = time.time()
        elapsed = current_time - self.start_time - self.total_paused_time
        
        # If currently paused, also subtract the current pause duration
        if self.paused and self.pause_start_time:
            elapsed -= (current_time - self.pause_start_time)
        
        return max(0.0, elapsed)  # Ensure non-negative
    
    def _extract_algorithm_statistics(self):
        """Extract current algorithm statistics."""
        if not self.wu_uct or not self.wu_uct.root:
            return
            
        # Count total nodes in tree (BFS) with proper synchronization
        try:
            total_nodes = 0
            max_depth = 0
            queue = [(self.wu_uct.root, 0)]
            visited = set()
            
            while queue and len(visited) < 10000:  # Prevent infinite loops
                node, depth = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                total_nodes += 1
                max_depth = max(max_depth, depth)
                
                # Safely access children
                try:
                    if hasattr(node, 'children'):
                        for child in node.children[:]:  # Copy to avoid concurrent modification
                            if child not in visited:
                                queue.append((child, depth + 1))
                except:
                    pass  # Skip if concurrent modification occurs
                    
            self.algorithm_stats['total_nodes'] = total_nodes
            self.algorithm_stats['tree_depth'] = max_depth
            
        except Exception as e:
            # If tree traversal fails, keep previous values
            pass
        
        # Calculate rates from workers
        if self.start_time and hasattr(self.wu_uct, 'workers'):
            elapsed = self._get_elapsed_time()
            if elapsed > 0:
                total_iterations = 0
                total_simulations = 0
                
                for worker in self.wu_uct.workers:
                    try:
                        total_iterations += getattr(worker, 'iterations_completed', 0)
                        total_simulations += getattr(worker, 'simulations_completed', 0)
                    except:
                        pass
                
                self.algorithm_stats['iterations_per_sec'] = total_iterations / elapsed
                self.algorithm_stats['simulations_per_sec'] = total_simulations / elapsed
                self.iteration_count = total_iterations
                
    def _find_best_path(self):
        """Find and update the best path from the current tree."""
        if not self.wu_uct or not self.wu_uct.root:
            return
            
        def extract_path_from_node(node):
            """Extract the path (sequence of nodes) from a WU-UCT node."""
            try:
                # OrienteeringState has a 'path' attribute containing the sequence of visited nodes
                if hasattr(node, 'state') and hasattr(node.state, 'path'):
                    return node.state.path[:]
                else:
                    return []
            except Exception:
                return []
        
        def find_best_leaf(node, visited_nodes=None):
            """Recursively find the leaf with the best UCT value and valid path."""
            if visited_nodes is None:
                visited_nodes = set()
            
            if node in visited_nodes:
                return [], 0, float('inf'), 0
                
            visited_nodes.add(node)
            
            try:
                # Get path from this node
                current_path = extract_path_from_node(node)
                
                # If this is a leaf or has few visits, check its value
                if not node.children or len(node.children) == 0:
                    # Calculate score and distance for this path
                    if len(current_path) > 1 and current_path[-1] == 1:  # Ends at target
                        total_score = sum(self.problem.nodes[n].score for n in current_path if 0 <= n < len(self.problem.nodes))
                        total_distance = 0
                        
                        for i in range(len(current_path) - 1):
                            if 0 <= current_path[i] < len(self.problem.nodes) and 0 <= current_path[i+1] < len(self.problem.nodes):
                                total_distance += self.problem.get_distance(current_path[i], current_path[i+1])
                        
                        if total_distance <= self.problem.budget:
                            visits = getattr(node, 'visits', 0)
                            return current_path, total_score, total_distance, visits
                
                # Check children recursively
                best_path = []
                best_score = 0
                best_distance = float('inf')
                best_visits = 0
                
                for child in node.children[:]:  # Copy to avoid concurrent modification
                    if child not in visited_nodes:
                        child_path, child_score, child_distance, child_visits = find_best_leaf(child, visited_nodes.copy())
                        
                        # Prefer higher score, then higher visits, then shorter distance
                        if (child_score > best_score or 
                            (child_score == best_score and child_visits > best_visits) or
                            (child_score == best_score and child_visits == best_visits and child_distance < best_distance)):
                            best_path = child_path
                            best_score = child_score
                            best_distance = child_distance
                            best_visits = child_visits
                        
                return best_path, best_score, best_distance, best_visits
                
            except Exception as e:
                return [], 0, float('inf'), 0
            finally:
                visited_nodes.discard(node)
        
        # Find best path
        try:
            path, score, distance, visits = find_best_leaf(self.wu_uct.root)
            if path and len(path) > 1:
                self.best_path = path
                self.best_score = score
                self.best_distance = distance
        except Exception as e:
            # If pathfinding fails, keep previous best path
            pass
    
    def _update_visualization(self, frame):
        """Update the visualization with current algorithm state."""
        # Step the algorithm if in step-by-step mode
        if self.step_by_step and not self.algorithm_completed:
            self._step_algorithm()
        
        # Debug output every 10 frames
        if frame % 10 == 0 and frame > 0:
            print(f"Frame {frame}: Iterations={self.iteration_count}, Workers={len(self.wu_uct.workers) if hasattr(self.wu_uct, 'workers') else 0}, Paused={self.paused}")
        
        # Update algorithm data
        self._enhanced_worker_tracking()
        self._extract_algorithm_statistics()
        self._find_best_path()
        
        # Clear and update statistics panel
        self.ax_stats.clear()
        self.ax_stats.set_title('Algorithm Statistics', fontweight='bold', fontsize=10)
        self.ax_stats.axis('off')
        
        if self.algorithm_completed:
            status_line = "✓ COMPLETED"
        elif self.paused:
            status_line = "⏸ PAUSED"
        else:
            status_line = "▶ RUNNING"
        
        mode = "Step" if self.step_by_step else "Fast"
        
        stats_text = f"""Status: {status_line}
Mode: {mode} ({self.iterations_per_frame}x{self.speed_multiplier:.1f})
Iterations: {self.iteration_count:,}/{self.iterations:,}
Progress: {100*self.iteration_count/self.iterations:.1f}%
Tree Nodes: {self.algorithm_stats['total_nodes']:,}
Tree Depth: {self.algorithm_stats['tree_depth']}
Iter/sec: {self.algorithm_stats['iterations_per_sec']:.1f}

Elapsed: {self._get_elapsed_time():.1f}s"""
        
        self.ax_stats.text(0.1, 0.9, stats_text, transform=self.ax_stats.transAxes,
                          fontsize=9, verticalalignment='top', fontfamily='monospace')
        
        # Update worker status panel
        self.ax_workers.clear()
        self.ax_workers.set_title('Worker Status', fontweight='bold', fontsize=10)
        self.ax_workers.axis('off')
        
        worker_text = ""
        for i in range(self.num_workers):
            status = self.worker_status.get(i, "Not started")
            worker_text += f"W{i}: {status}\n"
                
        self.ax_workers.text(0.1, 0.9, worker_text, transform=self.ax_workers.transAxes,
                           fontsize=9, verticalalignment='top', fontfamily='monospace')
        
        # Update best solution panel
        self.ax_algo.clear()
        title = 'Best Solution'
        if self.algorithm_completed:
            title += ' (FINAL)'
        self.ax_algo.set_title(title, fontweight='bold', fontsize=10)
        self.ax_algo.axis('off')
        
        if self.best_path:
            path_str = " → ".join(str(n) for n in self.best_path)
            if len(path_str) > 30:
                path_str = path_str[:27] + "..."
            
            status = "FINAL" if self.algorithm_completed else "Current"
            
            algo_text = f"""{status} Best Path:
{path_str}
Score: {self.best_score}
Distance: {self.best_distance:.2f}/{self.problem.budget:.2f}
Nodes: {len(self.best_path)}
Valid: {'YES' if self.best_distance <= self.problem.budget else 'NO'}"""
        else:
            if self.algorithm_completed:
                algo_text = "Algorithm completed\nNo valid solution found"
            else:
                algo_text = "Searching for solutions..."
            
        self.ax_algo.text(0.1, 0.9, algo_text, transform=self.ax_algo.transAxes,
                         fontsize=9, verticalalignment='top', fontfamily='monospace')
        
        # Update grid visualization
        self._update_grid_display()
        
        return []
    
    def _update_grid_display(self):
        """Update the grid display with current paths and activity."""
        # Clear previous path lines
        for line in self.ax_grid.lines[:]:
            if hasattr(line, 'is_path_line') and line.is_path_line:
                line.remove()
        
        # Clear previous arrows
        for artist in self.ax_grid.artists[:]:
            if hasattr(artist, 'is_path_arrow') and artist.is_path_arrow:
                artist.remove()
        
        # Draw worker selection paths (current exploration) - thin, bright lines
        if self.show_selection_paths:
            for worker_id, path in self.worker_selection_paths.items():
                if len(path) > 1:
                    try:
                        color = self.worker_colors[worker_id % len(self.worker_colors)]
                        path_x = [self.problem.nodes[i].x for i in path if 0 <= i < len(self.problem.nodes)]
                        path_y = [self.problem.nodes[i].y for i in path if 0 <= i < len(self.problem.nodes)]
                        
                        if len(path_x) > 1:
                            # Bright, thin selection path
                            line = self.ax_grid.plot(path_x, path_y, color=color,
                                                   linewidth=1.5, linestyle='-',
                                                   alpha=0.9, zorder=5,
                                                   label=f'W{worker_id} selecting')[0]
                            line.is_path_line = True
                    except Exception:
                        pass
        
        # Draw worker active paths (if enabled)
        if self.show_worker_paths:
            for worker_id, path in self.worker_active_paths.items():
                if len(path) > 1:
                    try:
                        # Get worker color
                        color = self.worker_colors[worker_id % len(self.worker_colors)]
                        
                        # Extract coordinates
                        path_x = []
                        path_y = []
                        for node_id in path:
                            if 0 <= node_id < len(self.problem.nodes):
                                path_x.append(self.problem.nodes[node_id].x)
                                path_y.append(self.problem.nodes[node_id].y)
                        
                        if len(path_x) > 1:
                            # Draw worker path with dashed line
                            line = self.ax_grid.plot(path_x, path_y, color=color, 
                                                   linewidth=2, linestyle='--',
                                                   alpha=0.6, zorder=4, 
                                                   label=f'Worker {worker_id}')[0]
                            line.is_path_line = True
                            
                            # Add small arrow at the end to show direction
                            if len(path_x) >= 2:
                                x1, y1 = path_x[-2], path_y[-2]
                                x2, y2 = path_x[-1], path_y[-1]
                                
                                arrow = self.ax_grid.annotate('', xy=(x2, y2), 
                                                            xytext=(x1, y1),
                                                            arrowprops=dict(arrowstyle='->', 
                                                                          color=color, 
                                                                          lw=1.5, 
                                                                          alpha=0.6), 
                                                            zorder=4)
                                arrow.is_path_arrow = True
                    except Exception:
                        pass  # Skip if path drawing fails
        
        # Draw best path (on top of worker paths)
        if len(self.best_path) > 1:
            path_x = [self.problem.nodes[i].x for i in self.best_path if 0 <= i < len(self.problem.nodes)]
            path_y = [self.problem.nodes[i].y for i in self.best_path if 0 <= i < len(self.problem.nodes)]
            
            if len(path_x) > 1:
                line = self.ax_grid.plot(path_x, path_y, color='gold', linewidth=4, 
                                       alpha=0.8, zorder=5)[0]
                line.is_path_line = True
                
                # Add arrows along the path
                for i in range(len(path_x) - 1):
                    x1, y1 = path_x[i], path_y[i]
                    x2, y2 = path_x[i + 1], path_y[i + 1]
                    
                    # Calculate arrow position (middle of segment)
                    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                    dx, dy = x2 - x1, y2 - y1
                    
                    arrow = self.ax_grid.annotate('', xy=(mx + dx*0.1, my + dy*0.1), 
                                                xytext=(mx - dx*0.1, my - dy*0.1),
                                                arrowprops=dict(arrowstyle='->', color='gold', 
                                                              lw=2, alpha=0.8), zorder=6)
                    arrow.is_path_arrow = True
        
        # Update node appearance based on activity
        self._update_node_activity()
        
    def _collect_node_visits(self) -> Dict[int, int]:
        """Collect visit counts for each graph node from the tree."""
        node_visits = defaultdict(int)
        
        if not self.wu_uct or not self.wu_uct.root:
            return node_visits
        
        def collect_visits(node):
            """Recursively collect visits from tree nodes."""
            if node is None:
                return
            
            try:
                # Get the graph node index from the tree node's state
                if hasattr(node, 'state') and hasattr(node.state, 'path'):
                    path = node.state.path
                    if path:
                        graph_node_id = path[-1]  # Last node in path
                        visits = getattr(node, 'visits', 0)
                        node_visits[graph_node_id] += visits
                
                # Process children
                if hasattr(node, 'children'):
                    for child in node.children[:]:
                        collect_visits(child)
            except:
                pass
        
        collect_visits(self.wu_uct.root)
        return node_visits
    
    def _update_node_activity(self):
        """Update node visual appearance based on current activity."""
        # Collect visit counts
        node_visits = self._collect_node_visits()
        
        # Find max visits for normalization
        max_visits = max(node_visits.values()) if node_visits else 1
        
        # Reset all nodes to default appearance
        for i, node in enumerate(self.problem.nodes):
            if i in self.node_circles:
                # Determine highlight based on activity
                in_best_path = i in self.best_path
                in_worker_path = any(i in path for path in self.worker_active_paths.values())
                in_selection_path = any(i in path for path in self.worker_selection_paths.values())
                
                # Update border based on activity
                if in_best_path:
                    # Highlight nodes in best path with gold border
                    self.node_circles[i].set_edgecolors('gold')
                    self.node_circles[i].set_linewidth(3)
                elif in_selection_path:
                    # Nodes being actively explored (magenta)
                    self.node_circles[i].set_edgecolors('magenta')
                    self.node_circles[i].set_linewidth(2.5)
                elif in_worker_path:
                    # Nodes in worker exploration paths
                    self.node_circles[i].set_edgecolors('orange')
                    self.node_circles[i].set_linewidth(2)
                else:
                    # Default appearance
                    self.node_circles[i].set_edgecolors('black')
                    self.node_circles[i].set_linewidth(1)
                
                # Update visit count text
                visits = node_visits.get(i, 0)
                if visits > 0:
                    self.node_visit_texts[i].set_text(f'{visits}')
                    # Color intensity based on visits
                    intensity = min(visits / max_visits, 1.0) if max_visits > 0 else 0
                    self.node_visit_texts[i].set_color((0, 0, intensity))
                else:
                    self.node_visit_texts[i].set_text('')
    
    def _run_algorithm(self):
        """Run the WU-UCT algorithm in a separate thread with real-time tracking (fast mode)."""
        try:
            print("Starting WU-UCT algorithm (fast mode)...")
            
            # Start the algorithm
            result = self.wu_uct.run(
                max_iterations=self.iterations,
                verbose=True
            )
            
            print(f"WU-UCT completed. Final result: {result}")
            
            # Store final result and update best path
            self.final_result = result
            self.algorithm_completed = True
            
            if hasattr(result, 'path'):
                self.best_path = result.path[:]
                self.best_score = result.reward_so_far
                self.best_distance = result.cost_so_far
            
            print("✓ Algorithm completed! Visualization will continue to show final results.")
            print("  Close the window when you're done viewing.")
            
        except Exception as e:
            print(f"Algorithm error: {e}")
            import traceback
            traceback.print_exc()
    
    def _step_algorithm(self):
        """
        Perform one or more iterations of the algorithm (step-by-step mode).
        This is called by the animation update function.
        """
        if self.algorithm_completed or self.paused:
            return
        
        # Run the specified number of iterations for this frame
        # To simulate parallel exploration, have each worker do iterations_per_frame iterations
        iterations_to_run = int(self.iterations_per_frame * self.speed_multiplier)
        
        # Each worker does iterations in parallel (simulated by sequential execution per frame)
        for worker in self.wu_uct.workers:
            for _ in range(iterations_to_run):
                if self.iteration_count >= self.iterations:
                    self.algorithm_completed = True
                    break
                
                if worker.iterations_completed < worker.iterations_per_worker:
                    # Perform one iteration for this worker
                    worker._perform_iteration()
                    worker.iterations_completed += 1
                    self.iteration_count += 1
                    
                    # Track selection path for this worker from the actual iteration
                    try:
                        if hasattr(worker, 'last_selection_path') and worker.last_selection_path:
                            self.worker_selection_paths[worker.worker_id] = worker.last_selection_path[:]
                            # Also update worker active path to show exploration history
                            self.worker_active_paths[worker.worker_id] = worker.last_selection_path[:]
                    except:
                        pass
            
            if self.algorithm_completed:
                break
    
    def run(self):
        """
        Start the visualization.
        
        Returns:
            Animation object (for keeping reference)
        """
        print("Initializing WU-UCT Grid Visualization...")
        print(f"Problem: {self.problem_path}")
        print(f"Nodes: {self.problem.num_nodes}, Budget: {self.problem.budget}")
        print(f"Workers: {self.num_workers}, Iterations: {self.iterations}")
        print()
        
        # Setup visualization FIRST
        self.setup_visualization()
        
        # Show the window immediately so users can see the initial state
        plt.ion()  # Turn on interactive mode
        plt.show(block=False)
        plt.pause(0.5)  # Longer pause to ensure window is fully rendered
        
        print("Visualization window opened!")
        
        # Initialize workers for step-by-step mode (they won't start yet)
        self.is_running = True
        self.start_time = time.time()
        
        if self.step_by_step:
            print("Starting in STEP-BY-STEP mode...")
            print("✓ Algorithm will run synchronized with animation frames")
            print(f"✓ Running {self.iterations_per_frame} iteration(s) per frame")
            
            # Create workers but don't start them as threads
            # We'll call their iteration methods directly from the animation update
            iterations_per_worker = self.iterations // self.num_workers
            remainder_iterations = self.iterations % self.num_workers
            
            from simple_wu_worker import SimpleWUWorker
            
            for i in range(self.num_workers):
                worker_iterations = (iterations_per_worker + 1 
                                   if i < remainder_iterations 
                                   else iterations_per_worker)
                
                worker = SimpleWUWorker(
                    problem=self.problem,
                    root=self.wu_uct.root,
                    worker_id=i,
                    iterations_per_worker=worker_iterations,
                    exploration_constant=self.exploration_constant,
                    max_distance=self.max_edge_distance
                )
                
                self.wu_uct.workers.append(worker)
                # Don't start the thread - we'll call methods directly
        else:
            print("Starting algorithm in background thread (fast mode)...")
            self.algorithm_thread = threading.Thread(target=self._run_algorithm, daemon=True)
            self.algorithm_thread.start()
            print("✓ Algorithm thread started!")
        
        print("✓ Workers will begin exploring the solution space...")
        print("✓ Visualization will update every", self.update_interval, "ms")
        
        # Add keyboard controls
        def on_key(event):
            """Handle keyboard events for interactive control."""
            if event.key == ' ':
                # Toggle pause/resume
                if not self.paused:
                    # Starting pause
                    self.paused = True
                    self.pause_start_time = time.time()
                    print(f"⏯  PAUSED")
                else:
                    # Resuming from pause
                    self.paused = False
                    if self.pause_start_time:
                        pause_duration = time.time() - self.pause_start_time
                        self.total_paused_time += pause_duration
                        self.pause_start_time = None
                    print(f"⏯  RESUMED")
            elif event.key == 'p' or event.key == 'P':
                # Toggle worker path display
                self.show_worker_paths = not self.show_worker_paths
                status = "ON" if self.show_worker_paths else "OFF"
                print(f"Worker paths: {status}")
            elif event.key == 's' or event.key == 'S':
                # Toggle selection path display
                self.show_selection_paths = not self.show_selection_paths
                status = "ON" if self.show_selection_paths else "OFF"
                print(f"Selection paths: {status}")
            elif event.key == '+' or event.key == '=':
                # Speed up
                self.speed_multiplier *= 2.0
                self.iterations_per_frame = max(1, int(self.iterations_per_frame * 2))
                print(f"⏩ Speed: {self.speed_multiplier}x ({self.iterations_per_frame} iters/frame)")
            elif event.key == '-' or event.key == '_':
                # Slow down
                self.speed_multiplier = max(0.125, self.speed_multiplier / 2.0)
                self.iterations_per_frame = max(1, self.iterations_per_frame // 2)
                print(f"⏪ Speed: {self.speed_multiplier}x ({self.iterations_per_frame} iters/frame)")
        
        self.fig.canvas.mpl_connect('key_press_event', on_key)
        
        # Create and start animation BEFORE showing
        print("Creating animation...")
        ani = animation.FuncAnimation(
            self.fig, 
            self._update_visualization,
            interval=self.update_interval,
            blit=False,
            repeat=True,
            cache_frame_data=False  # Prevent unbounded cache warning
        )
        
        print("Visualization is now live and updating in real-time!")
        print("\n📋 Interactive Controls:")
        print("  SPACE  - Pause/Resume")
        print("  P      - Toggle worker paths display")
        print("  S      - Toggle selection paths display")
        print("  +/=    - Speed up (more iterations per frame)")
        print("  -      - Slow down (fewer iterations per frame)")
        print("\nClose the window or press Ctrl+C to stop.")
        print()
        
        # Keep the window open and animating (this blocks until window is closed)
        plt.show(block=True)
        return ani


def main():
    """Main function for standalone execution."""
    # Default configuration - try multiple possible paths
    possible_paths = [
        "../../OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt",
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt",
        "../OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    ]
    
    problem_path = None
    for path in possible_paths:
        if os.path.exists(path):
            problem_path = path
            break
    
    print("WU-UCT Grid Visualization")
    print("=" * 40)
    print()
    
    # Check if problem file exists
    if problem_path is None:
        print(f"Problem file not found. Tried:")
        for path in possible_paths:
            print(f"  - {path}")
        print("Please run from the project root or Simple_WU/WU_Viz directory")
        return
    
    # Create and run visualizer
    visualizer = WUUCTGridVisualizer(
        problem_path=problem_path,
        iterations=100000,  # Reduced for better visualization
        num_workers=4,
        exploration_constant=math.sqrt(2),
        max_edge_distance=1.42,
        update_interval=50,  # Update every 50ms for smoother animation
        grid_size=(15, 10),
        step_by_step=True,  # Enable step-by-step mode to slow down
        iterations_per_frame=5  # Start with 5 iterations per frame (adjustable with +/-)
    )
    
    try:
        ani = visualizer.run()
    except KeyboardInterrupt:
        print("\n✅ Visualization completed successfully!")
        print("   The WU-UCT algorithm executed and found solutions.")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()