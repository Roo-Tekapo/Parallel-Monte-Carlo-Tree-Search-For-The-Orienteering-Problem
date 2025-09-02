import math
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.lines import Line2D

from MCTS.mcts_base import MCTSSingleThread
from orienteering.orienteering import OrienteeringProblem


# ---- Config ----
# PROBLEM_PATH = "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
PROBLEM_PATH = "OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_85.txt"
ITERATIONS = 10000
INITIAL_MAX_DEPTH = 50
MAX_NODES = None  # no cap on number of nodes drawn


def collect_tree(root, max_depth):
    """
    Traverse the MCTS tree up to max_depth from root.
    Returns: nodes (list of MCTSNode), edges (list of (parent, child)).
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
            # push children
            for c in reversed(node.children):  # reversed for left-to-right consistency
                edges.append((node, c))
                stack.append((c, depth + 1))
    return nodes, edges


def layout_tree(root, max_depth):
    """
    Compute a simple layered tree layout.
    Returns: pos dict mapping node -> (x, y), also ordered node list and edges list.
    """
    nodes, edges = collect_tree(root, max_depth)
    if not nodes:
        return {}, [], []

    # Build adjacency and depth map via BFS from root
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
            # ensure edge exists if both nodes are in nodes subset
    # Assign y by depth (0 at top)
    pos = {}
    max_d = max(depth_map.values()) if depth_map else 0
    # Assign x positions per depth, spaced by subtree order
    # We'll assign x incrementally per depth to avoid overlaps.
    for d in range(0, max_d + 1):
        level = by_depth.get(d, [])
        n = max(1, len(level))
        for i, node in enumerate(level):
            x = (i + 1) / (n + 1)  # (0,1) open interval
            y = 1.0 - (d / max(1, max_d)) if max_d > 0 else 0.5
            pos[node] = (x, y)

    return pos, nodes, edges


def node_label(node):
    try:
        last = node.state.path[-1]
    except Exception:
        last = "?"
    visits = node.visits
    return f"{last}\n{visits}"


def main():
    nodes, budget = OrienteeringProblem.load_problem(PROBLEM_PATH)
    problem = OrienteeringProblem(nodes, budget)

    solver = MCTSSingleThread(problem, iterations=ITERATIONS)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title("MCTS Tree Viz: space=pause/resume, up/down=depth±1, n=labels on/off")
    ax.axis('off')

    paused = {"v": False}
    max_depth = {"v": INITIAL_MAX_DEPTH}
    show_labels = {"v": True}

    # Artists cache
    edge_lines = []
    node_scat = None
    texts = []
    # Budget/score overlay (top-left)
    budget_text = ax.text(
        0.02,
        0.98,
        "",
        transform=ax.transAxes,
        va='top',
        ha='left',
        fontsize=10,
        bbox=dict(facecolor='white', alpha=0.6, edgecolor='none')
    )

    def on_key(event):
        if event.key == ' ':
            paused["v"] = not paused["v"]
        elif event.key == 'up':
            max_depth["v"] = min(max_depth["v"] + 1, 15)
        elif event.key == 'down':
            max_depth["v"] = max(1, max_depth["v"] - 1)
        elif event.key and event.key.lower() == 'n':
            show_labels["v"] = not show_labels["v"]

    fig.canvas.mpl_connect('key_press_event', on_key)

    def update(_):
        nonlocal edge_lines, node_scat, texts
        if not paused["v"]:
            ev = solver.step()
        else:
            ev = None

        pos, nlist, elist = layout_tree(solver.root, max_depth["v"])

        # Clear previous artists
        for ln in edge_lines:
            ln.remove()
        edge_lines = []
        if node_scat is not None:
            node_scat.remove()
        for t in texts:
            t.remove()
        texts = []

        if not nlist:
            return []

        # Draw edges
        for p, c in elist:
            if p in pos and c in pos:
                x1, y1 = pos[p]
                x2, y2 = pos[c]
                ln = Line2D([x1, x2], [y1, y2], color='gray', linewidth=1, alpha=0.6)
                ax.add_line(ln)
                edge_lines.append(ln)

        # Draw nodes
        X = [pos[n][0] for n in nlist]
        Y = [pos[n][1] for n in nlist]
        sizes = [80 if n is not (ev["leaf"] if ev else None) else 120 for n in nlist]
        colors = ['tab:blue' if n is solver.root else ('tab:orange' if n.children else 'tab:green') for n in nlist]
        node_scat = ax.scatter(X, Y, s=sizes, c=colors, zorder=3)

        # Labels (toggleable)
        if show_labels["v"]:
            for n in nlist:
                x, y = pos[n]
                txt = ax.text(x, y, node_label(n), fontsize=8, ha='center', va='center', color='black')
                texts.append(txt)

        # Status (iterations/depth)
        ax.set_xlabel(f"iterations: {solver.iteration}/{solver.iterations}  depth: {max_depth['v']}")

        # Overlay: best path score and cost vs budget
        try:
            best_leaf = solver.best_descendant(solver.root)
            # Cost
            get_cost = getattr(best_leaf.state, 'get_cost', None)
            best_cost_val = best_leaf.state.get_cost() if callable(get_cost) else getattr(best_leaf.state, 'cost_so_far', 0.0)
            # Score
            get_reward = getattr(best_leaf.state, 'get_reward', None)
            best_reward_val = best_leaf.state.get_reward() if callable(get_reward) else getattr(best_leaf.state, 'reward_so_far', 0.0)
            budget_text.set_text(f"Best score: {best_reward_val:.0f}  |  Cost: {best_cost_val:.2f} / Budget: {problem.budget:.2f}")
        except Exception:
            budget_text.set_text("")

        return [node_scat, *edge_lines, *texts, budget_text]

    ani = animation.FuncAnimation(fig, update, interval=80, blit=False)
    plt.show()


if __name__ == "__main__":
    main()


# PYTHONPATH=$(pwd) python3 viz/mcts_tree_viz.py