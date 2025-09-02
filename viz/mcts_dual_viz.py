import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.lines import Line2D

from MCTS.mcts_base import MCTSSingleThread
from orienteering.orienteering import OrienteeringProblem


# Config
# PROBLEM_PATH = "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
PROBLEM_PATH = "OP_Benchmark_Set/sample/sample_6_small.txt"
ITERATIONS = 100000
INITIAL_TREE_DEPTH = 8


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


def layout_tree(root, max_depth, max_nodes=400):
    # Collect nodes/edges up to depth
    nodes = []
    edges = []
    if root is None:
        return {}, [], []
    stack = [(root, 0)]
    seen = set()
    while stack and len(nodes) < max_nodes:
        node, d = stack.pop()
        if node in seen: continue
        seen.add(node)
        nodes.append(node)
        if d < max_depth:
            for c in reversed(node.children):
                edges.append((node, c))
                stack.append((c, d+1))

    if not nodes:
        return {}, [], []

    # BFS depth mapping for layout
    depth_map = {root: 0}
    by_depth = {0: [root]}
    q = [root]
    seen2 = {root}
    while q:
        cur = q.pop(0)
        d = depth_map[cur]
        if d >= max_depth:
            continue
        for c in cur.children:
            if c not in seen2:
                seen2.add(c)
                depth_map[c] = d+1
                by_depth.setdefault(d+1, []).append(c)
                q.append(c)

    pos = {}
    max_d = max(depth_map.values()) if depth_map else 0
    for d in range(0, max_d+1):
        level = by_depth.get(d, [])
        n = max(1, len(level))
        for i, node in enumerate(level):
            x = (i+1)/(n+1)
            y = 1.0 - (d/max(1, max_d)) if max_d>0 else 0.5
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

    # Figure 1: Map view
    fig_map, ax_map = plt.subplots(figsize=(8,6))
    sc = ax_map.scatter(xs, ys, c='gray', s=40)
    ax_map.set_title("Map Viz: space=pause, a=agg/per, r=visits/avg")
    start_scatter = ax_map.scatter([xs[0]], [ys[0]], c='blue', s=120, marker='o', label="Start")
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
    ax_tree.set_title("Tree Viz: up/down=depth ±1, n=labels on/off")
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
    show_tree_labels = {"v": True}

    def on_key_map(event):
        if event.key == ' ':
            paused["v"] = not paused["v"]
        elif event.key.lower() == 'a':
            aggregate_stats["v"] = not aggregate_stats["v"]
        elif event.key and event.key.lower() == 'r':
            label_metric["v"] = 'avg' if label_metric["v"] == 'visits' else 'visits'

    def on_key_tree(event):
        if event.key == 'up':
            max_depth["v"] = min(max_depth["v"] + 1, 15)
        elif event.key == 'down':
            max_depth["v"] = max(1, max_depth["v"] - 1)
        elif event.key and event.key.lower() == 'n':
            show_tree_labels["v"] = not show_tree_labels["v"]

    fig_map.canvas.mpl_connect('key_press_event', on_key_map)
    fig_tree.canvas.mpl_connect('key_press_event', on_key_tree)

    def update(_):
        nonlocal edge_lines, node_scat, texts_tree
        # Step once per frame
        if not paused["v"]:
            ev = solver.step()
        else:
            ev = {"reward": 0.0, "selection_path": [], "best_child": None}

        # ---- Update map viz ----
        # selection path
        sel_x, sel_y = [], []
        current_xy = None
        if ev.get("selection_path"):
            path = ev["selection_path"][-1].state.get_path()
            for p in path:
                if isinstance(p,int): sel_x.append(xs[p]); sel_y.append(ys[p])
            last = path[-1]
            if isinstance(last,int): current_xy = (xs[last], ys[last])
        sel_line.set_data(sel_x, sel_y)
        sel_scatter.set_offsets(list(zip(sel_x, sel_y)))
        current_scatter.set_offsets([current_xy] if current_xy else [])

        # best path
        best_leaf = solver.best_descendant(solver.root)
        best_path = best_leaf.state.get_path()
        bx, by = [], []
        for p in best_path:
            if isinstance(p,int): bx.append(xs[p]); by.append(ys[p])
        best_line.set_data(bx, by)

        ax_map.set_xlabel(f"iterations: {solver.iteration}/{solver.iterations}  last_reward: {ev['reward']:.3f}  mode: {'agg' if aggregate_stats['v'] else 'per'}")

        # node stats aggregation
        node_stats = {}
        def collect_stats(node):
            if node is None: return
            idx = node.state.path[-1]
            avg = (node.total_reward / node.visits) if node.visits>0 else 0.0
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
            for c in node.children:
                collect_stats(c)
        collect_stats(solver.root)

        for i, txt in enumerate(node_texts):
            stats = node_stats.get(i)
            visits_val = stats['visits'] if stats else 0
            avg_val = int(stats['best_avg']) if stats else 0
            bottom = visits_val if label_metric["v"] == 'visits' else avg_val
            txt.set_text(f"{i}\n{bottom}")

        # budget/score overlay map
        get_cost = getattr(best_leaf.state, 'get_cost', None)
        best_cost = best_leaf.state.get_cost() if callable(get_cost) else getattr(best_leaf.state,'cost_so_far',0.0)
        get_reward = getattr(best_leaf.state, 'get_reward', None)
        best_reward = best_leaf.state.get_reward() if callable(get_reward) else getattr(best_leaf.state,'reward_so_far',0.0)
        budget_text_map.set_text(f"Best score: {best_reward:.0f}  |  Cost: {best_cost:.2f} / Budget: {problem.budget:.2f}")

        # ---- Update tree viz ----
        pos, nlist, elist = layout_tree(solver.root, max_depth["v"]) 
        # clear previous
        for ln in edge_lines: ln.remove()
        edge_lines = []
        if node_scat is not None: node_scat.remove()
        for t in texts_tree: t.remove()
        texts_tree = []

        if nlist:
            # edges
            for p,c in elist:
                if p in pos and c in pos:
                    x1,y1 = pos[p]; x2,y2 = pos[c]
                    ln = Line2D([x1,x2],[y1,y2], color='gray', linewidth=1, alpha=0.6)
                    ax_tree.add_line(ln)
                    edge_lines.append(ln)
            # nodes
            X = [pos[n][0] for n in nlist]
            Y = [pos[n][1] for n in nlist]
            sizes = [80 if n is not (ev.get('leaf') if ev else None) else 120 for n in nlist]
            colors = ['tab:blue' if n is solver.root else ('tab:orange' if n.children else 'tab:green') for n in nlist]
            node_scat = ax_tree.scatter(X, Y, s=sizes, c=colors, zorder=3)
            if show_tree_labels["v"]:
                for n in nlist:
                    x,y = pos[n]
                    texts_tree.append(ax_tree.text(x, y, node_label(n), fontsize=8, ha='center', va='center', color='black'))

        ax_tree.set_xlabel(f"iterations: {solver.iteration}/{solver.iterations}  depth: {max_depth['v']}")
        budget_text_tree.set_text(f"Best score: {best_reward:.0f}  |  Cost: {best_cost:.2f} / Budget: {problem.budget:.2f}")

        # ensure tree fig refreshes
        fig_tree.canvas.draw_idle()

        # return map artists (animation bound to map fig)
        return [sel_scatter, best_line, sc, current_scatter, budget_text_map, *node_texts]

    ani = animation.FuncAnimation(fig_map, update, interval=60, blit=False)
    plt.show()


if __name__ == "__main__":
    main()



# PYTHONPATH=$(pwd) python3 viz/mcts_dual_viz.py