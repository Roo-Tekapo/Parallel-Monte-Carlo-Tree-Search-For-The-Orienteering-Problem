"""
Simple_WU - Simplified WU-UCT Implementation

This package contains a simplified version of WU-UCT where each worker
handles both tree expansion and simulation, eliminating the need for
separate worker types and complex coordination.

Key differences from the full UCT implementation:
- Single worker type that handles both expansion and simulation
- Simplified coordination without work unit queues
- Each worker maintains its own portion of search iterations
- Direct tree access with proper synchronization
"""