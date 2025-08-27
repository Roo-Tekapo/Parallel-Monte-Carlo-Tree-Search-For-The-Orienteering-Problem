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
        # Randomize the order of untried actions to avoid systematic bias
        self.untried_actions = state.get_available_actions()
        random.shuffle(self.untried_actions)

    def is_fully_expanded(self):
        return len(self.untried_actions) == 0

    def uct_best_child(self, c_param=math.sqrt(2), epsilon: float = 0.0):
        if not self.children:
            raise ValueError("No children to select from.")
        """Select best child with UCT, handling zero-visit children and optional epsilon-greedy exploration."""
        # Occasional random exploration among existing children
        if epsilon > 0.0 and random.random() < epsilon:
            return random.choice(self.children)
        # Prefer exploring any unvisited child first
        unvisited = [c for c in self.children if c.visits == 0]
        if unvisited:
            return random.choice(unvisited)

        # All children visited at least once; compute UCB1
        best_score = float("-inf")
        best_child = None
        ln_parent = math.log(self.visits) if self.visits > 0 else 0.0
        for child in self.children:
            exploit = child.total_reward / child.visits
            explore = c_param * math.sqrt(ln_parent / child.visits)
            score = exploit + explore
            if score > best_score:
                best_score = score
                best_child = child
        return best_child
