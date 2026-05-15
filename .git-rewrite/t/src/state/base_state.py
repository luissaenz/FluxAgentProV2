"""src/state/base_state.py — Compatibility shim.

The canonical state lives in src/flows/state.py (BaseFlowState, FlowStatus).
This file exists only to resolve the import path documented in Phase 3 examples.
"""

from src.flows.state import BaseFlowState, FlowStatus

__all__ = ["BaseFlowState", "FlowStatus"]
