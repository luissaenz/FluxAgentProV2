"""GenericFlow — First concrete flow to prove the Phase-1 stack.

Self-registers as ``generic_flow`` at import time. Accepts input
with a ``text`` key and delegates processing to GenericCrew.
"""

from __future__ import annotations

from typing import Dict, Any
import logging

from .base_flow import BaseFlow
from .registry import register_flow
from ..crews.generic_crew import create_generic_crew

logger = logging.getLogger(__name__)


@register_flow("generic_flow")
class GenericFlow(BaseFlow):
    """Demo flow that processes text via a single-agent crew."""

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        if "text" not in input_data:
            logger.error("Missing 'text' in input_data")
            return False
        if not isinstance(input_data["text"], str):
            logger.error("'text' must be a string")
            return False
        return True

    async def _run_crew(self) -> Dict[str, Any]:
        crew = create_generic_crew()
        result = await crew.kickoff_async(
            inputs={"text": self.state.input_data["text"]}
        )
        
        # Track tokens
        if hasattr(result, "token_usage") and result.token_usage:
            self.state.update_tokens(result.token_usage.get("total_tokens", 0))
        elif hasattr(result, "usage_metrics") and result.usage_metrics:
            self.state.update_tokens(result.usage_metrics.get("total_tokens", 0))
        else:
            self.state.update_tokens(self.state.estimate_tokens(str(result)))

        return {"processed_text": str(result)}
