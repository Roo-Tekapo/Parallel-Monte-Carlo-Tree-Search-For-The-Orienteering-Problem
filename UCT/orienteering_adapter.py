"""
Orienteering Problem Adapter for UCT

This module provides a unified import interface that can switch between
traditional and no-end orienteering variants based on configuration.

Usage in other UCT modules:
    Instead of:
        from orienteering.orienteering_traditional import OrienteeringProblem, OrienteeringState
    
    Use:
        from UCT.orienteering_adapter import OrienteeringProblem, OrienteeringState, END_NODE, START_NODE
"""

import os
import sys

# Configuration: Check for environment variable or use default
_USE_NO_END = os.environ.get('UCT_USE_NO_END', 'false').lower() in ('true', '1', 'yes')

# Import from appropriate module based on configuration
if _USE_NO_END:
    from orienteering.orienteering_no_end import (
        OrienteeringProblem,
        OrienteeringState,
        START_NODE,
        END_NODE,
        Node
    )
    _VARIANT = "No-End"
else:
    from orienteering.orienteering_traditional import (
        OrienteeringProblem,
        OrienteeringState,
        START_NODE,
        END_NODE,
        Node
    )
    _VARIANT = "Traditional"


def get_variant():
    """Get the current orienteering variant being used."""
    return _VARIANT


def set_variant(use_no_end: bool):
    """
    Set the orienteering variant.
    
    WARNING: This only affects future imports. Already imported modules
    will not be affected. Call this BEFORE importing other UCT modules.
    
    Args:
        use_no_end: If True, use no-end variant. If False, use traditional.
    """
    os.environ['UCT_USE_NO_END'] = 'true' if use_no_end else 'false'


# Export all for easy import
__all__ = [
    'OrienteeringProblem',
    'OrienteeringState',
    'START_NODE',
    'END_NODE',
    'Node',
    'get_variant',
    'set_variant'
]
