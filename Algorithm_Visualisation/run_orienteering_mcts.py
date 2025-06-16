from Algorithm_Visualisation.orienteering import Orienteering
from Algorithm_Visualisation.monte_carlo_tree_search import MCTS

NUM_CITIES = 15
DISTANCE_BUDGET = 200
ITERATIONS = 1000

# Initialize problem and MCTS
problem = Orienteering(nodes=NUM_CITIES, distance=DISTANCE_BUDGET)
root = problem.get_root()
mcts = MCTS(root)

# Run MCTS
mcts.iterate(ITERATIONS)

# Find the best terminal node among root's children
best_child = None
best_score = -1
for child in mcts.children.get(root, []):
    # Only consider terminal nodes
    if child.is_terminal():
        score = sum(1 for pt in child.tup if pt is not None)
        if score > best_score:
            best_score = score
            best_child = child

# If no terminal child found, pick the best by average reward
if best_child is None and mcts.children.get(root):
    best_child = max(mcts.children[root], key=lambda n: mcts.Q[n] / mcts.N[n])

if best_child:
    path = [pt for pt in best_child.tup if pt is not None]
    score = sum(1 for pt in best_child.tup if pt is not None)
    print("Best path:", path)
    print("Score:", score)
    print("Total distance:", best_child.get_total_distance(best_child.tup))
else:
    print("No solution found.")