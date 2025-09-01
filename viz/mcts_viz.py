import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.lines import Line2D
from MCTS.mcts_base import MCTSSingleThread
from orienteering.orienteering import OrienteeringProblem

# Load problem (adjust path as needed)
nodes, budget = OrienteeringProblem.load_problem(
    # "OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_85.txt"
    "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"

)
problem = OrienteeringProblem(nodes, budget)

# helper to extract coords from problem.nodes - adjust to your data structure
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

xs, ys = extract_coords(nodes)

solver = MCTSSingleThread(problem, iterations=1000)

fig, ax = plt.subplots(figsize=(8,6))
sc = ax.scatter(xs, ys, c='gray', s=40)
ax.set_title("MCTS Viz: press space to pause/resume")

# --- Highlight start & end nodes ---
start_node = nodes[0]
end_node   = nodes[1] 

# extract coords
def get_xy(n):
    if hasattr(n, "x") and hasattr(n, "y"):
        return n.x, n.y
    elif isinstance(n, (list, tuple)):
        return n[0], n[1]
    elif hasattr(n, "coord"):
        return n.coord[0], n.coord[1]
    else:
        raise RuntimeError("Unknown node format")

start_x, start_y = get_xy(start_node)
end_x, end_y     = get_xy(end_node)

start_scatter = ax.scatter([start_x], [start_y], c='blue', s=120, marker='o', label="Start")
end_scatter   = ax.scatter([end_x], [end_y], c='red',  s=120, marker='X', label="End")



# artists for selection path and best path
sel_scatter = ax.scatter([], [], s=120, facecolors='none', edgecolors='yellow', linewidths=2)
best_line = Line2D([], [], color='green', linewidth=2, alpha=0.8)
sel_line = Line2D([], [], color='orange', linewidth=1, alpha=0.6)
ax.add_line(best_line)
ax.add_line(sel_line)

paused = False
def on_key(event):
    global paused
    if event.key == ' ':
        paused = not paused

fig.canvas.mpl_connect('key_press_event', on_key)

# After plotting the nodes
node_texts = []
for i, (x, y) in enumerate(zip(xs, ys)):
    txt = ax.text(x, y, "", fontsize=8, ha='center', va='center', color='black')
    node_texts.append(txt)

def update(frame):
    global paused
    if paused:
        return sel_scatter, best_line, sc

    ev = solver.step()

    # highlight selection path nodes (use node.state to get path indexes)
    sel_coords_x = []
    sel_coords_y = []
    sel_line.set_data(sel_coords_x, sel_coords_y)
    try:
        if ev["selection_path"]:
            path = ev["selection_path"][-1].state.get_path()
            for p in path:
                if isinstance(p, int):
                    sel_coords_x.append(xs[p]); sel_coords_y.append(ys[p])
                elif hasattr(p, "x") and hasattr(p, "y"):
                    sel_coords_x.append(p.x); sel_coords_y.append(p.y)
    except Exception:
        pass

    sel_line.set_data(sel_coords_x, sel_coords_y)
    sel_scatter.set_offsets(list(zip(sel_coords_x, sel_coords_y)))

    # draw best child path if available
    best = ev.get("best_child")
    if best is not None:
        try:
            best_path = best.state.get_path()
            bx, by = [], []
            for p in best_path:
                if isinstance(p, int):
                    bx.append(xs[p]); by.append(ys[p])
                elif hasattr(p, "x") and hasattr(p, "y"):
                    bx.append(p.x); by.append(p.y)
            best_line.set_data(bx, by)
        except Exception:
            best_line.set_data([], [])
    else:
        best_line.set_data([], [])

    # Draw the full best_path as the green line
    best_leaf = solver.best_descendant(solver.root)
    best_path = best_leaf.state.get_path()
    bx, by = [], []
    for p in best_path:
        if isinstance(p, int):
            bx.append(xs[p]); by.append(ys[p])
        elif hasattr(p, "x") and hasattr(p, "y"):
            bx.append(p.x); by.append(p.y)
    best_line.set_data(bx, by)

    ax.set_xlabel(f"iter: {ev['iteration']}  last_reward: {ev['reward']:.3f}")

    # Update node labels with visits and reward
    # Build a mapping from node index to (visits, total_reward)
    node_stats = {}
    def collect_stats(node):
        if node is None: return
        idx = node.state.path[-1]
        average_reward = node.total_reward / node.visits if node.visits > 0 else 0
        node_stats[idx] = (node.visits, average_reward)
        for child in node.children:
            collect_stats(child)
    collect_stats(solver.root)

    for i, txt in enumerate(node_texts):
        visits, reward = node_stats.get(i, (0, 0))
        if visits > 0:
            txt.set_text(f"{visits}\n{int(reward)}")
        else:
            txt.set_text("")

    return sel_scatter, best_line, sc, *node_texts

ani = animation.FuncAnimation(fig, update, interval=50, blit=False)
plt.show()