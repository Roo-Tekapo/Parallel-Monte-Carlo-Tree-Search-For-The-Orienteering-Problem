import unittest
from orienteering.orienteering import Node, OrienteeringProblem, OrienteeringState
from MCTS.mcts_base import MCTSSingleThread
from MCTS.mcts_node import MCTSNode

from orienteering.orienteering_traditional import OrienteeringStateTraditional

class TestMCTSSingleThread(unittest.TestCase):
    def setUp(self):
        self.nodes = [
            Node(0, 0.0, 0.0, 5),
            Node(1, 2.0, 0.0, 10),
            Node(2, 2.0, 2.0, 15),
            Node(3, 0.0, 2.0, 20),
            Node(4, 1.0, 1.0, 25)
        ]
        self.budget = 5.0
        self.problem = OrienteeringProblem(self.nodes, self.budget)

    def test_run_returns_state(self):
        solver = MCTSSingleThread(self.problem, iterations=10)
        best_state = solver.run()
        self.assertTrue(isinstance(best_state, (OrienteeringState, OrienteeringStateTraditional)))
        self.assertTrue(hasattr(best_state, "get_path"))
        self.assertTrue(hasattr(best_state, "get_reward"))
        self.assertTrue(hasattr(best_state, "get_cost"))

# class TestMCTSNode(unittest.TestCase):
#     def setUp(self):
#         self.nodes = [
#             Node(0, 0.0, 0.0, 5),
#             Node(1, 2.0, 0.0, 10),
#             Node(2, 2.0, 2.0, 15)
#         ]
#         self.budget = 5.0
#         self.problem = OrienteeringProblem(self.nodes, self.budget)
#         self.state = OrienteeringState(self.problem)
#         self.node = MCTSNode(self.state)
#         # Add two children with different rewards and visits
#         child1 = MCTSNode(self.state.copy(), parent=self.node)
#         child1.visits = 10
#         child1.total_reward = 50
#         child2 = MCTSNode(self.state.copy(), parent=self.node)
#         child2.visits = 5
#         child2.total_reward = 40
#         self.node.children = [child1, child2]
#         self.node.visits = 15

#     def test_uct_best_child_returns_child(self):
#         best_child = self.node.uct_best_child()
#         print(f"Best child visits: {best_child.visits}, total reward: {best_child.total_reward}")
#         self.assertIn(best_child, self.node.children)
#         self.assertIsInstance(best_child, MCTSNode)

if __name__ == "__main__":
    unittest.main()


# python -m unittest Test/test_mcts_base_and_node.py