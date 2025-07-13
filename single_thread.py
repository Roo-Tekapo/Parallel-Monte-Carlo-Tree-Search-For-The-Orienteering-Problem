import math
import random
from collections import namedtuple

Node = namedtuple('Node', ['id', 'x', 'y', 'score'])

def load_problem(filename):
    with open(filename, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    # First line: Tmax P
    budget, _ = lines[0].split()
    budget = float(budget)
    node_lines = lines[1:]
    nodes = []
    for idx, line in enumerate(node_lines):
        x, y, score = line.split()
        nodes.append(Node(idx, float(x), float(y), int(score)))
    return nodes, budget

# Load nodes and budget from file
nodes, BUDGET = load_problem(
    # r'OP_Benchmark_Set\Tsiligirides_1\tsiligirides_problem_1_budget_85.txt'
    # r'OP_Benchmark_Set\test_OP_budget_30.txt'
    r"OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_10.txt"
)
START_NODE = 0
END_NODE = 1

def distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

class State:
    def __init__(self, path=None, cost=0, score=0):
        self.path = path or [START_NODE]
        self.cost = cost
        self.score = score

    def copy(self):
        return State(self.path[:], self.cost, self.score)

    def is_terminal(self):
        # Terminal if last node is END_NODE and path has at least two nodes
        return self.path[-1] == END_NODE and len(self.path) > 1

    def available_actions(self):
        visited = set(self.path)
        actions = []
        # Optional nodes are those not start or end and not visited
        for node in nodes:
            if node.id not in visited and node.id != START_NODE and node.id != END_NODE:
                # Check if we can visit this node and then reach END_NODE within budget
                next_cost = self.cost + distance(nodes[self.path[-1]], node) + distance(node, nodes[END_NODE])
                if next_cost <= BUDGET:
                    actions.append(node.id)
        # Option to go directly to END_NODE if not already there
        if self.path[-1] != END_NODE:
            if self.cost + distance(nodes[self.path[-1]], nodes[END_NODE]) <= BUDGET:
                actions.append(END_NODE)
        # Debug print
        # print(f"At path {self.path}, available actions: {actions}")
        return actions

    def do_action(self, action):
        if action == END_NODE:
            new_cost = self.cost + distance(nodes[self.path[-1]], nodes[END_NODE])
            return State(self.path + [END_NODE], new_cost, self.score)
        else:
            # print(f"Performing action: {action} from path {self.path}")
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
    path, score = mcts(initial_state, iterations=1000)
    print("Best path:", path)
    print("Score:", score)