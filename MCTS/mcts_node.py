import math
import random

from orienteering.orienteering import OrienteeringState

class MCTSNode:
    def __init__(self, state: OrienteeringState, parent=None, traditional_mcts: bool = False):
        self.state = state
        self.parent = parent
        self.children = []
        self.visits = 0
        self.total_reward = 0.0
        # copy actions list to avoid aliasing and randomize order
        self.untried_actions = list(state.get_available_actions(traditional_mcts=traditional_mcts) or [])
        if self.untried_actions:
            random.shuffle(self.untried_actions)
        # Mark as dead-end if no actions available and not terminal
        self.is_dead_end = (len(self.untried_actions) == 0 and not state.is_terminal())

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
    

    # def uct_best_child(self, c_param=math.sqrt(2)):
    #     for child in self.children:
    #         if child.visits == 0:
    #             return child
    #     choices = [
    #         (child.total_reward / child.visits) +
    #         c_param * math.sqrt(math.log(self.visits) / child.visits)
    #         for child in self.children
    #     ]
    #     return self.children[choices.index(max(choices))]

    def uct_best_child(self, c_param, epsilon): #c_param=math.sqrt(2), epsilon: float = 0.05
        if not self.children:
            raise ValueError("No children to select from.")

        # Filter out dead-end children (nodes with no actions that aren't terminal)
        viable_children = [c for c in self.children if not c.is_dead_end]
        
        # If all children are dead-ends, fall back to all children
        # (This shouldn't happen often but prevents crashes)
        if not viable_children:
            viable_children = self.children

        # epsilon-greedy occasional random pick
        if epsilon > 0.0 and random.random() < epsilon:
            return random.choice(viable_children)

        # prefer any unvisited child first
        unvisited = [c for c in viable_children if c.visits == 0]
        if unvisited:
            return random.choice(unvisited)

        # compute UCT using parent's visits guarded against 0
        parent_visits = max(1, self.visits)
        ln_parent = math.log(parent_visits)
        best_score = float("-inf")
        best_child = None
        
        sqrt_ln_parent = math.sqrt(ln_parent)
        for child in viable_children:
            # safe since all children visited >0 here
            exploit = child.total_reward / child.visits
            explore = c_param * sqrt_ln_parent / math.sqrt(child.visits)
            score = exploit + explore
            if score > best_score:
                best_score = score
                best_child = child
        return best_child
