import unittest
from orienteering.orienteering import Node, OrienteeringProblem, OrienteeringState

class TestOrienteering(unittest.TestCase):
    def setUp(self):
        # Create a more complex problem with 5 nodes
        self.nodes = [
            Node(0, 0.0, 0.0, 5),
            Node(1, 2.0, 0.0, 10),
            Node(2, 2.0, 2.0, 15),
            Node(3, 0.0, 2.0, 20),
            Node(4, 1.0, 1.0, 25)
        ]
        self.budget = 5.0
        self.problem = OrienteeringProblem(self.nodes, self.budget)
        self.state = OrienteeringState(self.problem)
        # print("Initial state:", self.state)

    def test_num_nodes(self):
        self.assertEqual(self.problem.num_nodes, 5)
        # print("Number of nodes in problem:", self.problem.num_nodes)

    def test_load_problem_from_file(self):
        # Path to your test file
        # filename = "OP_Benchmark_Set/Tsiligirides_1/tsiligirides_problem_1_budget_10.txt"
        filename = "OP_Benchmark_Set/set_64_1/set_64_1_15.txt"
        nodes, budget = OrienteeringProblem.load_problem(filename)
        # Check budget
        self.assertEqual(budget, 15.0)
        # Check number of nodes (should match lines in file minus header)
        self.assertEqual(len(nodes), 64)
        # Check first node values
        self.assertEqual(nodes[0].id, 0)
        self.assertAlmostEqual(nodes[0].x, 0)
        self.assertAlmostEqual(nodes[0].y, -7)
        self.assertEqual(nodes[0].score, 0)
        # Check last node values
        self.assertEqual(nodes[-1].id, 63)
        self.assertAlmostEqual(nodes[-1].x, 1)
        self.assertAlmostEqual(nodes[-1].y, 6)
        self.assertEqual(nodes[-1].score, 6)

    def test_get_distance(self):
        d = self.problem.get_distance(0, 1)
        self.assertAlmostEqual(d, 2.0)

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

    def test_apply_action_node_0_to_1(self):
        # Move from node 0 to node 1
        new_state = self.state.apply_action(1)
        self.assertEqual(new_state.path, [0, 1])
        self.assertIn(1, new_state.visited)
        self.assertAlmostEqual(new_state.cost_so_far, self.problem.get_distance(0, 1))
        self.assertEqual(new_state.reward_so_far, self.nodes[0].score + self.nodes[1].score)

    def test_best_child(self):
        best = self.state.best_child()
        self.assertIsInstance(best, OrienteeringState)

    def test_get_reward(self):
        self.assertEqual(self.state.get_reward(), 5)

    def test_get_cost(self):
        self.assertEqual(self.state.get_cost(), 0.0)

    def test_get_path(self):
        self.assertEqual(self.state.get_path(), [0])

if __name__ == "__main__":
    unittest.main()


# python3 -m unittest Test/test_orienteering.py
# python3 -m unittest discover -s Test