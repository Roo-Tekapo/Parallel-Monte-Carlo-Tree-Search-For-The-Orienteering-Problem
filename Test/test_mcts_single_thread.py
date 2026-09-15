import unittest
from UCT.uct_single_thread import UCTSingleThread, UCTNode
from orienteering.orienteering_traditional import Node, OrienteeringProblem, OrienteeringState

class TestSingleThreadMCTS(unittest.TestCase):
    def setUp(self):
        # Create a small orienteering problem
        self.nodes = [
            Node(0, 0.0, 0.0, 5),
            Node(1, 2.0, 0.0, 10),
            Node(2, 2.0, 2.0, 15),
            Node(3, 0.0, 2.0, 20),
            Node(4, 1.0, 1.0, 25)
        ]
        self.budget = 5.0
        self.problem = OrienteeringProblem(self.nodes, self.budget, max_edge_distance=None)
        self.mcts = UCTSingleThread(self.problem, iterations=10)

    def test_init(self):
        root = self.mcts.initialize_root()
        self.assertIsInstance(root, UCTNode)
        self.assertIsInstance(root.state, OrienteeringState)

    def test_select_and_expand(self):
        root = self.mcts.initialize_root()
        leaf = self.mcts.selection(root)
        self.assertIsInstance(leaf, UCTNode)
        child = self.mcts.expansion(leaf)
        self.assertIsInstance(child, UCTNode)

    def test_simulate(self):
        root = self.mcts.initialize_root()
        reward = self.mcts.simulation(root.state)
        self.assertIsInstance(reward, (int, float))

    def test_backpropagate(self):
        root = self.mcts.initialize_root()
        child = self.mcts.expansion(root)
        self.mcts.backpropagation(child, 1.0)
        self.assertEqual(child.visits, 1)
        self.assertEqual(root.visits, 1)

    def test_run_iteration(self):
        info = self.mcts.run_iteration()
        self.assertIn('iteration', info)
        self.assertIn('reward', info)
        self.assertEqual(info['iteration'], 1)

if __name__ == "__main__":
    unittest.main()


# python3 -m unittest Test/test_mcts_single_thread.py
