"""
Orienteering Problem Adapter for Tree Parallel MCTS

This module provides a unified import interface that can switch between
different orienteering variants based on configuration.

Usage in Tree modules:
    Instead of:
        from orienteering.orienteering_optimized import OrienteeringProblem, OrienteeringState
    
    Use:
        from Tree.orienteering_adapter import OrienteeringProblem, OrienteeringState, END_NODE, START_NODE
"""

import os
import sys

# Configuration: Check for environment variable or use default
# Default to optimized version for better performance
_USE_OPTIMIZED = os.environ.get('TREE_USE_OPTIMIZED', 'true').lower() in ('true', '1', 'yes')
_USE_NO_END = os.environ.get('TREE_USE_NO_END', 'false').lower() in ('true', '1', 'yes')

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
elif _USE_OPTIMIZED:
    from orienteering.orienteering_optimized import (
        OrienteeringProblem,
        OrienteeringState,
        START_NODE,
        END_NODE,
        Node
    )
    _VARIANT = "Optimized"
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


def set_variant(use_optimized: bool = True, use_no_end: bool = False):
    """
    Set the orienteering variant.
    
    WARNING: This only affects future imports. Already imported modules
    will not be affected. Call this BEFORE importing other Tree modules.
    
    Args:
        use_optimized: If True, use optimized variant (default)
        use_no_end: If True, use no-end variant. Overrides use_optimized.
    """
    if use_no_end:
        os.environ['TREE_USE_NO_END'] = 'true'
        os.environ['TREE_USE_OPTIMIZED'] = 'false'
    else:
        os.environ['TREE_USE_NO_END'] = 'false'
        os.environ['TREE_USE_OPTIMIZED'] = 'true' if use_optimized else 'false'


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
