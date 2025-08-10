import unittest
from orienteering.orienteering import Node, OrienteeringProblem, OrienteeringState

class TestOrienteering(unittest.TestCase):
    def setUp(self):
        # Create a simple problem with 3 nodes
        self.nodes = [
            Node(0, 0.0, 0.0, 10),
            Node(1, 1.0, 0.0, 20),
            Node(2, 0.0, 1.0, 30)
        ]
        self.budget = 2.0
        self.problem = OrienteeringProblem(self.nodes, self.budget)
        self.state = OrienteeringState(self.problem)

    def test_num_nodes(self):
        self.assertEqual(self.problem.num_nodes, 3)

    def test_get_distance(self):
        d = self.problem.get_distance(0, 1)
        self.assertAlmostEqual(d, 1.0)

    def test_is_terminal_initial(self):
        self.assertFalse(self.state.is_terminal())

    def test_copy(self):
        state2 = self.state.copy()
        self.assertEqual(state2.path, self.state.path)
        self.assertEqual(state2.cost_so_far, self.state.cost_so_far)
        self.assertEqual(state2.reward_so_far, self.state.reward_so_far)

    def test_get_available_actions(self):
        actions = self.state.get_available_actions()
        self.assertTrue(len(actions) > 0)
        for child in actions:
            self.assertIsInstance(child, OrienteeringState)

    def test_apply_action(self):
        actions = self.state.get_available_actions()
        if actions:
            action = actions[0].path[-1]
            new_state = self.state.apply_action(action)
            self.assertIn(action, new_state.path)
            self.assertGreaterEqual(new_state.cost_so_far, self.state.cost_so_far)

    def test_best_child(self):
        best = self.state.best_child()
        self.assertIsInstance(best, OrienteeringState)

    def test_get_reward_and_cost(self):
        self.assertEqual(self.state.get_reward(), 10)
        self.assertEqual(self.state.get_cost(), 0.0)

    def test_get_path(self):
        self.assertEqual(self.state.get_path(), [0])

if __name__ == "__main__":
    unittest.main()