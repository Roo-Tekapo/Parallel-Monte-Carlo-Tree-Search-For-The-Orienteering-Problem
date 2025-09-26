"""
Work unit data structures for WU-UCT algorithm.
Contains the basic data classes used for communication between workers.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from orienteering.orienteering import OrienteeringState

if TYPE_CHECKING:
    from .uct_single_thread import UCTNode


@dataclass
class WorkUnit:
    """
    A work unit represents a leaf node that needs simulation.
    
    This is the basic unit of work passed from the expansion worker
    to the simulation workers. It contains:
    - The node that needs simulation
    - A copy of the state for the simulation
    - A unique work ID for tracking
    """
    node: 'UCTNode'
    state: OrienteeringState
    work_id: int
    
    def __post_init__(self):
        # Ensure we have a copy of the state to avoid race conditions
        # This is crucial for thread safety
        self.state = self.state.copy()


@dataclass
class SimulationResult:
    """
    Result of a simulation returned by simulation workers.
    
    Contains:
    - The work unit ID that this result corresponds to
    - The reward obtained from the simulation
    """
    work_id: int
    reward: float
    
    def __repr__(self):
        return f"SimulationResult(work_id={self.work_id}, reward={self.reward:.2f})"