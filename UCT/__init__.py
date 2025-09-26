"""
UCT package for Upper Confidence bounds applied to Trees algorithms.
Contains both single-threaded UCT and parallel WU-UCT implementations.

The package is now organized into focused modules:
- uct_single_thread: Base UCT implementation
- work_units: Data structures for work unit communication
- expansion_worker: Tree management and expansion logic
- simulation_worker: Random rollout simulations
- wu_uct_coordinator: Main WU-UCT algorithm coordinator
- wu_uct: Simplified interface combining all components
"""

# Core UCT components
from .uct_single_thread import UCTSingleThread, UCTNode

# WU-UCT data structures
from .work_units import WorkUnit, SimulationResult

# WU-UCT workers
from .expansion_worker import WUUCTExpansionWorker
from .simulation_worker import WUUCTSimulationWorker, SimulationWorkerPool

# WU-UCT main coordinator
from .wu_uct_coordinator import WUUCT, run_wu_uct

__all__ = [
    # Single-threaded UCT
    'UCTSingleThread', 
    'UCTNode',
    
    # WU-UCT data structures
    'WorkUnit',
    'SimulationResult',
    
    # WU-UCT workers
    'WUUCTExpansionWorker', 
    'WUUCTSimulationWorker',
    'SimulationWorkerPool',
    
    # WU-UCT main interface
    'WUUCT',
    'run_wu_uct'
]