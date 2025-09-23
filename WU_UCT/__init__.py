"""
WU-UCT (Worker-UCT) Implementation for Orienteering Problem

This module provides a parallel Monte Carlo Tree Search implementation
based on the WU-UCT algorithm, adapted for the Orienteering Problem.

Key Components:
- WUOrienteeringNode: Node representation for the search tree
- WUOrienteeringTree: Main tree structure and algorithm implementation  
- WUOrienteeringWorker: Worker threads for parallel execution
- WUOrienteeringSolver: High-level solver interface

Usage:
    from WU_UCT import WUOrienteeringSolver
    from orienteering.orienteering import OrienteeringProblem
    
    # Load problem
    nodes, budget = OrienteeringProblem.load_problem("problem.txt")
    problem = OrienteeringProblem(nodes, budget)
    
    # Create solver
    solver = WUOrienteeringSolver(problem, num_workers=4)
    
    # Solve
    path, reward, stats = solver.solve(max_iterations=10000, verbose=True)
"""

try:
    from .wu_orienteering_node import WUOrienteeringNode
    from .wu_orienteering_tree import WUOrienteeringTree
    from .wu_orienteering_worker import WUOrienteeringWorker, OrienteeringSimulationWorker, OrienteeringExpansionWorker
    from .main import WUOrienteeringSolver
    
    __all__ = [
        'WUOrienteeringNode',
        'WUOrienteeringTree', 
        'WUOrienteeringWorker',
        'OrienteeringSimulationWorker',
        'OrienteeringExpansionWorker',
        'WUOrienteeringSolver'
    ]
    
except ImportError as e:
    # Fallback for development/debugging
    print(f"Warning: Could not import WU_UCT components: {e}")
    __all__ = []