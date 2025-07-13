import math
import random
from collections import namedtuple


START_NODE = 0
END_NODE = 1

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

def getDistance(a, b):
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
        # print("Current path:", self.path, "with cost:", self.cost, "and score:", self.score)
        for i in range(len(nodes)):
            if i not in visited and i != START_NODE and i != END_NODE:
                # Check if we can visit this node and then reach END_NODE within budget
                next_cost = self.cost + getDistance(self.path[-1], i) + getDistance(i, END_NODE)
                if next_cost <= BUDGET:
                    actions.append(i)
        # Option to go directly to END_NODE if not already there
        if self.path[-1] != END_NODE:
            if self.cost + getDistance(self.path[-1], END_NODE) <= BUDGET:
                actions.append(END_NODE)
        return actions

    def do_action(self, action):
        print(f"Performing action: {action} from path {self.path}")
        if action == END_NODE:
            new_cost = self.cost + getDistance(self.path[-1], END_NODE)
            print(f"Reached END_NODE with cost: {new_cost}")
            return State(self.path + [END_NODE], new_cost, self.score)
        else:
            new_cost = self.cost + getDistance(self.path[-1], action)
            new_score = self.score + nodes[action][2]
            print(f"Visiting node {action} with cost: {new_cost} and score: {new_score}")
            return State(self.path + [action], new_cost, new_score)
        
    def __str__(self) -> str:
        return f"Path {self.path} cost: {self.cost:0.2f}, score: {self.score}"