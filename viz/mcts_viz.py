import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.lines import Line2D
from MCTS.mcts_base import MCTSSingleThread
from orienteering.orienteering import OrienteeringProblem

# Load problem (adjust path as needed)
nodes, budget = OrienteeringProblem.load_problem(
    "OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_10.txt"
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

solver = MCTSSingleThread(problem, iterations=10000)

fig, ax = plt.subplots(figsize=(8,6))
sc = ax.scatter(xs, ys, c='gray', s=40)
ax.set_title("MCTS Viz: press space to pause/resume")

# artists for selection path and best path
sel_scatter = ax.scatter([], [], s=120, facecolors='none', edgecolors='yellow', linewidths=2)
best_line = Line2D([], [], color='green', linewidth=2, alpha=0.8)
ax.add_line(best_line)

paused = False
def on_key(event):
    global paused
    if event.key == ' ':
        paused = not paused

fig.canvas.mpl_connect('key_press_event', on_key)

def update(frame):
    global paused
    if paused:
        return sel_scatter, best_line, sc

    ev = solver.step()

    # highlight selection path nodes (use node.state to get path indexes)
    sel_coords_x = []
    sel_coords_y = []
    for node in ev["selection_path"]:
        # infer the last chosen location in the node.state (adjust accessor if different)
        try:
            path = node.state.get_path()
            if path:
                last = path[-1]
                # assume last is index into original nodes list or has x,y attributes
                if isinstance(last, int):
                    sel_coords_x.append(xs[last]); sel_coords_y.append(ys[last])
                elif hasattr(last, "x") and hasattr(last, "y"):
                    sel_coords_x.append(last.x); sel_coords_y.append(last.y)
        except Exception:
            # fallback: skip if structure unknown
            pass

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

    ax.set_xlabel(f"iter: {ev['iteration']}  last_reward: {ev['reward']:.3f}")
    return sel_scatter, best_line, sc

ani = animation.FuncAnimation(fig, update, interval=50, blit=False)
plt.show()