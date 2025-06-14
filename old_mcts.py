import math
import random

# Hardcoded orienteering problem as a matrix
# Each row: [x, y, score]
nodes = [
    [10.5, 14.4, 0],   # Start node (id 0)
    [11.2, 14.1, 0],   # End node (id 1)
    [18, 15.9, 10],
    [18.3, 13.3, 10],
    [16.5, 9.3, 10],
    [15.4, 11, 10],
    [14.9, 13.2, 5],
    [16.3, 13.3, 5],
    [16.4, 17.8, 5],
    [15, 17.9, 5],
    [16.1, 19.6, 10],
    [15.7, 20.6, 10],
    [13.2, 20.1, 10],
    [14.3, 15.3, 5],
    [14, 5.1, 10],
    [11.4, 6.7, 15],
    [8.3, 5, 15],
    [7.9, 9.8, 10],
    [11.4, 12, 5],
    [11.2, 17.6, 5],
    [10.1, 18.7, 5],
    [11.7, 20.3, 10],
    [10.2, 22.1, 10],
    [9.7, 23.8, 10],
    [10.1, 26.4, 15],
    [7.4, 24, 15],
    [8.2, 19.9, 15],
    [8.7, 17.7, 10],
    [8.9, 13.6, 10],
    [5.6, 11.1, 10],
    [4.9, 18.9, 10],
    [7.3, 18.8, 10],
]
BUDGET = 30  # Tmax from your file
START_NODE = 0
END_NODE = 1

def distance(a, b):
    return math.hypot(nodes[a][0] - nodes[b][0], nodes[a][1] - nodes[b][1])

class State:
    def __init__(self, path=None, cost=0, score=0):
        self.path = path or [START_NODE]
        self.cost = cost
        self.score = score

    def copy(self):
        return State(self.path[:], self.cost, self.score)

    def is_terminal(self):
        return self.path[-1] == END_NODE and len(self.path) > 1

    def available_actions(self):
        visited = set(self.path)
        actions = []
        for i in range(len(nodes)):
            if i not in visited and i != START_NODE and i != END_NODE:
                # Check if we can visit this node and then reach END_NODE within budget
                next_cost = self.cost + distance(self.path[-1], i) + distance(i, END_NODE)
                if next_cost <= BUDGET:
                    actions.append(i)
        # Option to go directly to END_NODE if not already there
        if self.path[-1] != END_NODE:
            if self.cost + distance(self.path[-1], END_NODE) <= BUDGET:
                actions.append(END_NODE)
        return actions

    def do_action(self, action):
        if action == END_NODE:
            new_cost = self.cost + distance(self.path[-1], END_NODE)
            return State(self.path + [END_NODE], new_cost, self.score)
        else:
            new_cost = self.cost + distance(self.path[-1], action)
            new_score = self.score + nodes[action][2]
            return State(self.path + [action], new_cost, new_score)

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
            for child in self.children.values() if child.visits > 0
        ]
        if not choices:
            return None
        return max(choices, key=lambda x: x[0])[1]

def tree_policy(node):
    while not node.state.is_terminal():
        actions = node.state.available_actions()
        if not actions:
            break
        if len(node.children) < len(actions):
            for action in actions:
                if action not in node.children:
                    new_state = node.state.do_action(action)
                    child = MCTSNode(new_state, node)
                    node.children[action] = child
                    return child
        else:
            next_node = node.best_child()
            if next_node is None:
                break
            node = next_node
    return node

def default_policy(state):
    current = state.copy()
    while not current.is_terminal():
        actions = current.available_actions()
        if not actions:
            break
        action = random.choice(actions)
        current = current.do_action(action)
    return current.score

def backup(node, reward):
    while node is not None:
        node.visits += 1
        node.value += reward
        node = node.parent

def mcts(root_state, iterations):
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
    path, score = mcts(initial_state, iterations=10000)
    print("Best path:", path)
    print("Score:", score)