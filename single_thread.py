import math
import random
from collections import namedtuple

# Define the problem instance (Tsiligirides Problem 1, budget 0.5)
Node = namedtuple('Node', ['id', 'x', 'y', 'score'])
nodes = [
    Node(0, 0, 0, 0),    # Depot (start/end)
    Node(1, 1, 3, 10),
    Node(2, 4, 3, 8),
    Node(3, 2, 5, 7),
    Node(4, 6, 1, 6),
    Node(5, 3, 7, 5),
    Node(6, 5, 6, 4),
    Node(7, 8, 2, 3),
    Node(8, 7, 7, 2),
    Node(9, 9, 5, 1)
]
BUDGET = 0.5 * sum(
    math.hypot(nodes[i].x - nodes[j].x, nodes[i].y - nodes[j].y)
    for i in range(len(nodes)) for j in range(i+1, len(nodes))
) / (len(nodes) - 1)  # Example budget calculation

def distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

class State:
    def __init__(self, path=None, cost=0, score=0):
        self.path = path or [0]
        self.cost = cost
        self.score = score

    def copy(self):
        return State(self.path[:], self.cost, self.score)

    def is_terminal(self):
        return self.path[-1] == 0 and len(self.path) > 1

    def available_actions(self):
        visited = set(self.path)
        actions = []
        for node in nodes:
            if node.id not in visited and node.id != 0:
                next_cost = self.cost + distance(nodes[self.path[-1]], node) + distance(node, nodes[0])
                if next_cost <= BUDGET:
                    actions.append(node.id)
        if self.path[-1] != 0:
            actions.append(0)  # Option to return to depot
        return actions

    def do_action(self, action):
        if action == 0:
            # Return to depot
            new_cost = self.cost + distance(nodes[self.path[-1]], nodes[0])
            return State(self.path + [0], new_cost, self.score)
        else:
            node = nodes[action]
            new_cost = self.cost + distance(nodes[self.path[-1]], node)
            new_score = self.score + node.score
            return State(self.path + [action], new_cost, new_score)

# MCTS Node
class MCTSNode:
    def __init__(self, state, parent=None):
        self.state = state
        self.parent = parent
        self.children = {}
        self.visits = 0
        self.value = 0

    def is_fully_expanded(self):
        return set(self.children.keys()) == set(self.state.available_actions())

    def best_child(self, c_param=1.4):
        choices = [
            (child.value / child.visits + c_param * math.sqrt(2 * math.log(self.visits) / child.visits), child)
            for child in self.children.values()
        ]
        return max(choices, key=lambda x: x[0])[1]

def tree_policy(node):
    while not node.state.is_terminal():
        actions = node.state.available_actions()
        if len(node.children) < len(actions):
            # Expand
            for action in actions:
                if action not in node.children:
                    new_state = node.state.do_action(action)
                    child = MCTSNode(new_state, node)
                    node.children[action] = child
                    return child
        else:
            node = node.best_child()
    return node

def default_policy(state):
    current = state.copy()
    while not current.is_terminal():
        actions = current.available_actions()
        action = random.choice(actions)
        current = current.do_action(action)
    return current.score

def backup(node, reward):
    while node is not None:
        node.visits += 1
        node.value += reward
        node = node.parent

def mcts(root_state, iterations=1000):
    root = MCTSNode(root_state)
    for _ in range(iterations):
        node = tree_policy(root)
        reward = default_policy(node.state)
        backup(node, reward)
    # Return the best path found
    best = max(root.children.values(), key=lambda n: n.value / n.visits)
    return best.state.path, best.state.score

if __name__ == "__main__":
    initial_state = State()
    path, score = mcts(initial_state, iterations=1000)
    print("Best path:", path)
    print("Score:", score)