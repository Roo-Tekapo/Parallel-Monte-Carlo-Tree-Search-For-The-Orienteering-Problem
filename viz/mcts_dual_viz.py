import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.lines import Line2D
import matplotlib.colors as mcolors
import numpy as np

from MCTS.mcts_base import MCTSSingleThread
from orienteering.orienteering import OrienteeringProblem


# Config
# PROBLEM_PATH = "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
# PROBLEM_PATH = "OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt"
# PROBLEM_PATH = "OP_Benchmark_Set/grid_patterns/grid_corners_b40.txt"
PROBLEM_PATH = "OP_Benchmark_Set/parallel_friendly_v2/xlarge/xlarge_40x40_r15_83.txt"
# PROBLEM_PATH = "OP_Benchmark_Set/parallel_friendly_v2/corridors/corridors_n6_l20_w3_24.txt"
# PROBLEM_PATH = "OP_Benchmark_Set/parallel_friendly_v2/clustered/clustered_c4_s4_sp6_19.txt"
# PROBLEM_PATH = "OP_Benchmark_Set/sample/sample_30.txt"
# PROBLEM_PATH = "OP_Benchmark_Set/sample/sample_1000.txt"
ITERATIONS = 100000
INITIAL_TREE_DEPTH = 100

# Performance settings
ANIMATION_INTERVAL = 100  # ms - reduced update frequency for smoother visualization
STEPS_PER_FRAME = 1       # Single MCTS step per visualization update for better debugging
MAX_TREE_NODES = 2000      # Limit tree visualization nodes


def extract_coords(nodes):
    xs, ys = [], []
    for n in nodes:
        if hasattr(n, "x") and hasattr(n, "y"):
            xs.append(n.x); ys.append(n.y)
        elif isinstance(n, (list, tuple)) and len(n) >= 2:
            xs.append(n[0]); ys.append(n[1])
        elif hasattr(n, "coord"):
            xs.append(n.coord[0]); ys.append(n.coord[1])
        else:
            raise RuntimeError("Unknown node format; adapt extract_coords")
    return xs, ys


def layout_tree(root, max_depth, max_nodes=500, max_breadth=10):
    # Collect nodes/edges up to depth with early termination
    nodes = []
    edges = []
    if root is None:
        return {}, [], []
    
    # Use BFS with limited node count for better performance
    queue = [(root, 0)]
    seen = {root}
    depth_counts = {}
    
    while queue and len(nodes) < max_nodes:
        node, depth = queue.pop(0)
        if depth > max_depth:
            continue
            
        nodes.append(node)
        depth_counts[depth] = depth_counts.get(depth, 0) + 1
        
        # Limit nodes per depth to prevent explosion
        if depth_counts[depth] > 50:  # Max 50 nodes per depth level
            continue
            
        if depth < max_depth:
            # Limit breadth (number of children processed per node)
            children_to_process = node.children[:max_breadth] if max_breadth > 0 else node.children
            for child in children_to_process:
                if child not in seen and len(nodes) < max_nodes:
                    seen.add(child)
                    edges.append((node, child))
                    queue.append((child, depth + 1))

    if not nodes:
        return {}, [], []

    # Faster layout calculation
    pos = {}
    by_depth = {}
    for i, node in enumerate(nodes):
        # Simple depth calculation based on distance from root
        depth = 0
        current = node
        while current.parent and depth < max_depth:
            depth += 1
            current = current.parent
        
        by_depth.setdefault(depth, []).append(node)

    max_d = max(by_depth.keys()) if by_depth else 0
    for d, level_nodes in by_depth.items():
        n = len(level_nodes)
        for i, node in enumerate(level_nodes):
            x = (i + 1) / (n + 1)
            y = 1.0 - (d / max(1, max_d)) if max_d > 0 else 0.5
            pos[node] = (x, y)
    
    return pos, nodes, edges


def node_label(node):
    try:
        last = node.state.path[-1]
    except Exception:
        last = "?"
    return f"{last}\n{node.visits}"


def main():
    # Load problem and solver
    nodes, budget = OrienteeringProblem.load_problem(PROBLEM_PATH)
    problem = OrienteeringProblem(nodes, budget)
    solver = MCTSSingleThread(problem, iterations=ITERATIONS)

    xs, ys = extract_coords(nodes)

    # Extract node scores for color mapping
    node_scores = [node.score for node in nodes]
    min_score = min(node_scores)
    max_score = max(node_scores)

    # Create color mapping - use 'Blues' colormap where darker = higher reward
    cmap = plt.cm.Blues
    norm = mcolors.Normalize(vmin=min_score, vmax=max_score)
    node_colors = [cmap(norm(score)) for score in node_scores]

    # Figure 1: Map view
    fig_map, ax_map = plt.subplots(figsize=(10,6))
    sc = ax_map.scatter(xs, ys, c=node_colors, s=40, edgecolors='black', linewidths=0.5)
    ax_map.set_title("Map Viz: space=pause, a=agg/per, r=visits/avg, q=reset (Node color = reward)")
    
    # Add colorbar to show reward scale
    cbar = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax_map, shrink=0.6)
    cbar.set_label('Node Reward', rotation=270, labelpad=15)
    start_scatter = ax_map.scatter([xs[0]], [ys[0]], c='green', s=120, marker='o', label="Start")
    end_scatter   = ax_map.scatter([xs[1]], [ys[1]], c='red',  s=120, marker='X', label="End")
    sel_scatter = ax_map.scatter([], [], s=120, facecolors='none', edgecolors='yellow', linewidths=2)
    best_line = Line2D([], [], color='green', linewidth=2, alpha=0.8)
    sel_line = Line2D([], [], color='orange', linewidth=1, alpha=0.6)
    ax_map.add_line(best_line)
    ax_map.add_line(sel_line)
    current_scatter = ax_map.scatter([], [], s=200, facecolors='none', edgecolors='magenta', linewidths=2, alpha=0.9)
    budget_text_map = ax_map.text(0.02, 0.98, "", transform=ax_map.transAxes, va='top', ha='left', fontsize=10,
                                  bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))
    node_texts = [ax_map.text(x, y, "", fontsize=8, ha='center', va='center', color='black') for x,y in zip(xs,ys)]

    # Figure 2: Tree view
    fig_tree, ax_tree = plt.subplots(figsize=(10,6))
    ax_tree.set_title("Tree Viz: up/down=depth ±1, left/right=breadth ±1, n=labels on/off")
    ax_tree.axis('off')
    edge_lines = []
    node_scat = None
    texts_tree = []
    budget_text_tree = ax_tree.text(0.02, 0.98, "", transform=ax_tree.transAxes, va='top', ha='left', fontsize=10,
                                    bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))

    # State
    paused = {"v": False}
    aggregate_stats = {"v": False}
    label_metric = {"v": 'visits'}
    max_depth = {"v": INITIAL_TREE_DEPTH}
    max_breadth = {"v": 10}  # Maximum children per node to display
    show_tree_labels = {"v": True}
    
    # Performance optimization: cache tree layout
    last_tree_update = {"iter": -1, "pos": {}, "nodes": [], "edges": []}
    last_stats_update = {"iter": -1, "stats": {}}

    def on_key_map(event):
        if event.key == ' ':
            paused["v"] = not paused["v"]
        elif event.key.lower() == 'a':
            aggregate_stats["v"] = not aggregate_stats["v"]
        elif event.key and event.key.lower() == 'r':
            label_metric["v"] = 'avg' if label_metric["v"] == 'visits' else 'visits'
        elif event.key and event.key.lower() == 'q':
            # Reset/restart the MCTS algorithm
            nonlocal solver
            solver = MCTSSingleThread(problem, iterations=ITERATIONS)
            print("MCTS algorithm reset")

    def on_key_tree(event):
        if event.key == 'up':
            max_depth["v"] = min(max_depth["v"] + 1, 15)
        elif event.key == 'down':
            max_depth["v"] = max(1, max_depth["v"] - 1)
        elif event.key == 'left':
            max_breadth["v"] = max(1, max_breadth["v"] - 1)
        elif event.key == 'right':
            max_breadth["v"] = min(max_breadth["v"] + 1, 50)
        elif event.key and event.key.lower() == 'n':
            show_tree_labels["v"] = not show_tree_labels["v"]

    fig_map.canvas.mpl_connect('key_press_event', on_key_map)
    fig_tree.canvas.mpl_connect('key_press_event', on_key_tree)

    def update(_):
        nonlocal edge_lines, node_scat, texts_tree
        
        # Run multiple MCTS steps per frame for better performance
        ev = {"reward": 0.0, "selection_path": [], "best_child": None}
        if not paused["v"]:
            try:
                for _ in range(STEPS_PER_FRAME):
                    if solver.iteration < solver.iterations:
                        ev = solver.step()
                        # Check if we're stuck (no available actions and not terminal)
                        if ev.get("selection_path"):
                            last_state = ev["selection_path"][-1].state
                            if not last_state.is_terminal() and not last_state.get_available_actions():
                                print(f"Warning: Got stuck at iteration {solver.iteration}, state: {last_state}")
                                print(f"  Path: {last_state.path}")
                                print(f"  Cost: {last_state.cost_so_far:.2f} / Budget: {solver.problem.budget}")
                    else:
                        break
            except Exception as e:
                print(f"Error during MCTS step at iteration {solver.iteration}: {e}")
                import traceback
                traceback.print_exc()
        
        # Only update tree visualization every few iterations to reduce overhead
        should_update_tree = (solver.iteration % (STEPS_PER_FRAME * 2) == 0 or 
                             solver.iteration != last_tree_update["iter"])

        # ---- Update map viz (lighter weight updates) ----
        # selection path - only if we have a valid selection
        if ev.get("selection_path"):
            path = ev["selection_path"][-1].state.get_path()
            sel_x, sel_y = [], []
            current_xy = None
            for p in path:
                if isinstance(p, int): 
                    sel_x.append(xs[p])
                    sel_y.append(ys[p])
            last = path[-1]
            if isinstance(last, int): 
                current_xy = (xs[last], ys[last])
            sel_line.set_data(sel_x, sel_y)
            sel_scatter.set_offsets(list(zip(sel_x, sel_y)))
            current_scatter.set_offsets([current_xy] if current_xy else [])

        # best path
        best_leaf = solver.best_descendant(solver.root)
        best_path = best_leaf.state.get_path()
        bx, by = [], []
        for p in best_path:
            if isinstance(p, int): 
                bx.append(xs[p])
                by.append(ys[p])
        best_line.set_data(bx, by)

        ax_map.set_xlabel(f"iterations: {solver.iteration}/{solver.iterations}  last_reward: {ev['reward']:.3f}  mode: {'agg' if aggregate_stats['v'] else 'per'}")

        # Update node stats only occasionally
        if solver.iteration != last_stats_update["iter"] or solver.iteration % STEPS_PER_FRAME == 0:
            node_stats = {}
            def collect_stats(node, depth=0):
                if node is None or depth > 10:  # Limit recursion depth
                    return
                idx = node.state.path[-1]
                avg = (node.total_reward / node.visits) if node.visits > 0 else 0.0
                entry = node_stats.get(idx)
                if aggregate_stats["v"]:
                    if entry is None:
                        node_stats[idx] = {'visits': node.visits, 'best_avg': avg}
                    else:
                        entry['visits'] += node.visits
                        if avg > entry['best_avg']:
                            entry['best_avg'] = avg
                else:
                    if entry is None or node.visits > entry['visits']:
                        node_stats[idx] = {'visits': node.visits, 'best_avg': avg}
                
                # Limit the number of children processed
                for i, c in enumerate(node.children):
                    if i < 20:  # Only process first 20 children
                        collect_stats(c, depth + 1)
            
            collect_stats(solver.root)
            last_stats_update["iter"] = solver.iteration
            last_stats_update["stats"] = node_stats

        # Update node text labels
        for i, txt in enumerate(node_texts):
            stats = last_stats_update["stats"].get(i)
            visits_val = stats['visits'] if stats else 0
            avg_val = int(stats['best_avg']) if stats else 0
            bottom = visits_val if label_metric["v"] == 'visits' else avg_val
            txt.set_text(f"{i}\n{bottom}")

        # budget/score overlay map
        get_cost = getattr(best_leaf.state, 'get_cost', None)
        best_cost = best_leaf.state.get_cost() if callable(get_cost) else getattr(best_leaf.state, 'cost_so_far', 0.0)
        get_reward = getattr(best_leaf.state, 'get_reward', None)
        best_reward = best_leaf.state.get_reward() if callable(get_reward) else getattr(best_leaf.state, 'reward_so_far', 0.0)
        budget_text_map.set_text(f"Best score: {best_reward:.0f}  |  Cost: {best_cost:.2f} / Budget: {problem.budget:.2f}")

        # ---- Update tree viz (less frequently) ----
        if should_update_tree:
            pos, nlist, elist = layout_tree(solver.root, max_depth["v"], MAX_TREE_NODES, max_breadth["v"])
            last_tree_update["iter"] = solver.iteration
            last_tree_update["pos"] = pos
            last_tree_update["nodes"] = nlist
            last_tree_update["edges"] = elist
        else:
            # Use cached values
            pos = last_tree_update["pos"]
            nlist = last_tree_update["nodes"]
            elist = last_tree_update["edges"]
        
        # clear previous tree elements
        for ln in edge_lines: 
            ln.remove()
        edge_lines = []
        if node_scat is not None: 
            node_scat.remove()
        for t in texts_tree: 
            t.remove()
        texts_tree = []

        if nlist:
            # edges
            for p, c in elist:
                if p in pos and c in pos:
                    x1, y1 = pos[p]
                    x2, y2 = pos[c]
                    ln = Line2D([x1, x2], [y1, y2], color='gray', linewidth=1, alpha=0.6)
                    ax_tree.add_line(ln)
                    edge_lines.append(ln)
            
            # nodes
            X = [pos[n][0] for n in nlist if n in pos]
            Y = [pos[n][1] for n in nlist if n in pos]
            sizes = [80 if n is not (ev.get('leaf') if ev else None) else 120 for n in nlist if n in pos]
            colors = ['tab:blue' if n is solver.root else ('tab:orange' if n.children else 'tab:green') for n in nlist if n in pos]
            
            if X and Y:  # Only create scatter if we have points
                node_scat = ax_tree.scatter(X, Y, s=sizes, c=colors, zorder=3)
                
                if show_tree_labels["v"]:
                    for n in nlist:
                        if n in pos:
                            x, y = pos[n]
                            texts_tree.append(ax_tree.text(x, y, node_label(n), fontsize=8, ha='center', va='center', color='black'))

        ax_tree.set_xlabel(f"iterations: {solver.iteration}/{solver.iterations}  depth: {max_depth['v']}  breadth: {max_breadth['v']}")
        budget_text_tree.set_text(f"Best score: {best_reward:.0f}  |  Cost: {best_cost:.2f} / Budget: {problem.budget:.2f}")

        # Only refresh tree figure when needed
        if should_update_tree:
            fig_tree.canvas.draw_idle()

        # return map artists (animation bound to map fig)
        return [sel_scatter, best_line, sc, current_scatter, budget_text_map, *node_texts]

    ani = animation.FuncAnimation(fig_map, update, interval=ANIMATION_INTERVAL, blit=False, cache_frame_data=False)
    plt.show()


if __name__ == "__main__":
    main()



# PYTHONPATH=$(pwd) python3 viz/mcts_dual_viz.py