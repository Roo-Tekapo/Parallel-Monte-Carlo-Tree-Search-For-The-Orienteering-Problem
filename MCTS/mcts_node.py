import math
import random

from orienteering.orienteering import OrienteeringState

class MCTSNode:
    def __init__(self, state: OrienteeringState, parent=None):
        self.state = state
        self.parent = parent
        self.children = []
        self.visits = 0
        self.total_reward = 0.0
        # copy actions list to avoid aliasing and randomize order
        self.untried_actions = list(state.get_available_actions() or [])
        if self.untried_actions:
            random.shuffle(self.untried_actions)

    def __repr__(self):
        try:
            last = self.state.path[-1]
        except Exception:
            last = None
        return f"<MCTSNode last={last} visits={self.visits} reward={self.total_reward:.1f} children={len(self.children)}>"

    def is_fully_expanded(self):
        return len(self.untried_actions) == 0

    def find_child_by_action(self, action):
        """Return child whose state's last node equals action, or None."""
        for c in self.children:
            try:
                if c.state.path and c.state.path[-1] == action:
                    return c
            except Exception:
                continue
        return None

    def add_child(self, child_node):
        """Attach an already-created MCTSNode as child (keeps parent link consistent)."""
        child_node.parent = self
        self.children.append(child_node)
        return child_node

    def uct_best_child(self, c_param=math.sqrt(2), epsilon: float = 0.0):
        if not self.children:
            raise ValueError("No children to select from.")

        # epsilon-greedy occasional random pick
        if epsilon > 0.0 and random.random() < epsilon:
            return random.choice(self.children)

        # prefer any unvisited child first
        unvisited = [c for c in self.children if c.visits == 0]
        if unvisited:
            return random.choice(unvisited)

        # compute UCT using parent's visits guarded against 0
        parent_visits = max(1, self.visits)
        ln_parent = math.log(parent_visits)
        best_score = float("-inf")
        best_child = None
        for child in self.children:
            # safe since all children visited >0 here
            exploit = child.total_reward / child.visits
            explore = c_param * math.sqrt(ln_parent / child.visits)
            score = exploit + explore
            if score > best_score:
                best_score = score
                best_child = child
        return best_child
