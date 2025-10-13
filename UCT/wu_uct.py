"""
WU-UCT (Work Unit UCT) - Main interface module.

This module provides a simplified interface to the WU-UCT algorithm
by importing the necessary components from the modular implementation.

The actual implementation is now split across multiple focused files:
- work_units.py: Data structures for work communication
- expansion_worker.py: Tree management and selection/expansion
- simulation_worker.py: Random rollout simulations  
- wu_uct_coordinator.py: Main algorithm coordinator

This approach makes the code much easier to understand and maintain
while providing the same functionality as the original monolithic file.
"""

import math

# Import all the components from the modular implementation
from .work_units import WorkUnit, SimulationResult
from .expansion_worker import WUUCTExpansionWorker
from .simulation_worker import WUUCTSimulationWorker, SimulationWorkerPool
from .wu_uct_coordinator import WUUCT, run_wu_uct

# Re-export the main classes for backward compatibility
__all__ = [
    'WorkUnit',
    'SimulationResult', 
    'WUUCTExpansionWorker',
    'WUUCTSimulationWorker',
    'SimulationWorkerPool',
    'WUUCT',
    'run_wu_uct'
]


if __name__ == "__main__":
    # Test the WU-UCT implementation using the new modular structure
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from orienteering.orienteering import OrienteeringProblem, OrienteeringState
    from work_units import WorkUnit, SimulationResult
    from expansion_worker import WUUCTExpansionWorker
    from simulation_worker import WUUCTSimulationWorker, SimulationWorkerPool
    from wu_uct_coordinator import WUUCT, run_wu_uct
    
    print("Testing WU-UCT with modular implementation...")
    
    # Load test problem
    nodes, budget = OrienteeringProblem.load_problem(
        "../OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    )
    
    problem = OrienteeringProblem(nodes, budget)
    
    # Test using the main WUUCT class
    wu_uct = WUUCT(problem, 
                   expansion_workers=1, 
                   simulation_workers=4, 
                   exploration_constant=math.sqrt(2))
    
    print("Running WU-UCT algorithm...")
    best_state = wu_uct.run(max_iterations=10000, verbose=True)
    
    print(f"\nResults:")
    print(f"Best path: {best_state.get_path()}")
    print(f"Total reward: {best_state.get_reward()}")
    print(f"Total cost: {best_state.get_cost()}")
    print(f"Statistics: {wu_uct.get_statistics()}")
    
    print("\n" + "="*50)
    print("Testing convenience function...")
    
    # Test using the convenience function
    best_state_2 = run_wu_uct(problem, 
                             max_iterations=5000,
                             simulation_workers=3,
                             verbose=True)
    
    print(f"\nConvenience function results:")
    print(f"Best path: {best_state_2.get_path()}")
    print(f"Total reward: {best_state_2.get_reward()}")
    print(f"Total cost: {best_state_2.get_cost()}")