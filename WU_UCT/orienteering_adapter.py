"""
Orienteering Problem Adapter for WU-UCT

Provides a consistent interface for the orienteering problem
that works with the WU-UCT implementation.
"""

from orienteering.orienteering_optimized import OrienteeringProblem as BaseOrienteeringProblem
from orienteering.orienteering_optimized import OrienteeringState


class OrienteeringAdapter:
    """
    Adapter to make OrienteeringProblem compatible with WU-UCT.
    
    Provides methods expected by WU-UCT workers.
    """
    
    def __init__(self, problem: BaseOrienteeringProblem):
        """
        Initialize adapter.
        
        Args:
            problem: Base orienteering problem instance
        """
        self.problem = problem
        self.nodes = problem.nodes
        self.budget = problem.budget
        self.num_nodes = problem.num_nodes
        self.normalize_rewards = problem.normalize_rewards
        self.reward_scale = problem.reward_scale
    
    def create_initial_state(self) -> OrienteeringState:
        """
        Create initial state for the problem.
        
        Returns:
            Initial OrienteeringState
        """
        return OrienteeringState(self.problem)
    
    def get_distance(self, from_node: int, to_node: int) -> float:
        """
        Get distance between two nodes.
        
        Args:
            from_node: Source node ID
            to_node: Destination node ID
            
        Returns:
            Distance between nodes
        """
        return self.problem.get_distance(from_node, to_node)
    
    def get_normalized_score(self, node_id: int) -> float:
        """
        Get normalized score for a node.
        
        Args:
            node_id: Node ID
            
        Returns:
            Normalized score
        """
        return self.problem.get_normalized_score(node_id)
    
    @staticmethod
    def load_problem(filename: str, normalize_rewards: bool = True, max_edge_distance: float = 1.42):
        """
        Load problem from file.
        
        Args:
            filename: Path to problem file
            normalize_rewards: Whether to normalize rewards
            max_edge_distance: Maximum edge distance constraint (default: 1.42)
            
        Returns:
            OrienteeringAdapter instance
        """
        nodes, budget = BaseOrienteeringProblem.load_problem(filename)
        problem = BaseOrienteeringProblem(nodes, budget, normalize_rewards=normalize_rewards, 
                                         max_edge_distance=max_edge_distance)
        return OrienteeringAdapter(problem)
    
    def __getattr__(self, name):
        """Delegate unknown attributes to underlying problem."""
        return getattr(self.problem, name)
