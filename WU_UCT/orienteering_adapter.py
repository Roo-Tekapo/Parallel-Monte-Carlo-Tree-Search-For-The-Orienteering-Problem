"""
Orienteering Problem Adapter for WU-UCT

Provides a consistent interface for the orienteering problem
that works with the WU-UCT implementation.
"""

import os

# Check environment variable to determine which orienteering variant to use
_USE_NO_END = os.environ.get('WU_UCT_USE_NO_END', 'false').lower() in ('true', '1', 'yes')

if _USE_NO_END:
    from orienteering.orienteering_no_end import (
        OrienteeringProblemNoEnd as BaseOrienteeringProblem,
        OrienteeringStateNoEnd as OrienteeringState
    )
else:
    from orienteering.orienteering_optimized import (
        OrienteeringProblem as BaseOrienteeringProblem,
        OrienteeringState
    )


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
    def load_problem(filename: str, normalize_rewards: bool = True, max_edge_distance: float = 1.42,
                    use_no_end: bool = None):
        """
        Load problem from file.
        
        Args:
            filename: Path to problem file
            normalize_rewards: Whether to normalize rewards
            max_edge_distance: Maximum edge distance constraint (default: 1.42)
            use_no_end: If specified, overrides environment variable for no-end mode
            
        Returns:
            OrienteeringAdapter instance
        """
        # Allow explicit override via parameter
        if use_no_end is not None:
            os.environ['WU_UCT_USE_NO_END'] = 'true' if use_no_end else 'false'
            # Reimport to get the correct variant
            global BaseOrienteeringProblem, OrienteeringState
            if use_no_end:
                from orienteering.orienteering_no_end import (
                    OrienteeringProblemNoEnd as BaseOrienteeringProblem,
                    OrienteeringStateNoEnd as OrienteeringState
                )
            else:
                from orienteering.orienteering_optimized import (
                    OrienteeringProblem as BaseOrienteeringProblem,
                    OrienteeringState
                )
        
        nodes, budget = BaseOrienteeringProblem.load_problem(filename)
        problem = BaseOrienteeringProblem(nodes, budget, normalize_rewards=normalize_rewards, 
                                         max_edge_distance=max_edge_distance)
        return OrienteeringAdapter(problem)
    
    def __getattr__(self, name):
        """Delegate unknown attributes to underlying problem."""
        return getattr(self.problem, name)


def set_variant(use_no_end: bool):
    """
    Set the orienteering variant to use.
    
    This sets an environment variable that determines which problem/state
    classes are imported. Should be called before loading any problems.
    
    Args:
        use_no_end: If True, use no-end variant. If False, use traditional.
    """
    os.environ['WU_UCT_USE_NO_END'] = 'true' if use_no_end else 'false'
