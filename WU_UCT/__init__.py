"""
WU-UCT: Watch the Unobservable UCT

True implementation of the WU-UCT algorithm from Chen et al. (2018):
"Watch the Unobservable: A New Approach for Parallel MCTS" (AAAI 2018)

Key features:
- Lock-free or minimally locked selection phase
- Local buffering of node statistics
- Prediction-based UCT with unobserved samples
- Asynchronous result commits
- Separate expansion and simulation workers
"""

__version__ = "1.0.0"
__author__ = "WU-UCT Implementation"

from WU_UCT.wu_uct_node import WUUCTNode
from WU_UCT.wu_uct_coordinator import WUUCTCoordinator
from WU_UCT.expansion_worker import ExpansionWorker
from WU_UCT.simulation_worker import SimulationWorker

__all__ = [
    'WUUCTNode',
    'WUUCTCoordinator',
    'ExpansionWorker',
    'SimulationWorker',
]
