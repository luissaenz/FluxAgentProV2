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
        text = input_data.get("text")
        if not text or not isinstance(text, str) or not text.strip():
            logger.error("Missing or empty 'text' in input_data")
            return False
        return True

    async def _run_crew(self) -> Dict[str, Any]:
        crew = create_generic_crew()
        result = await crew.kickoff_async(
            inputs={"text": self.state.input_data["text"]}
        )
        
        # Track tokens
        tokens = 0
        if hasattr(result, "token_usage") and result.token_usage:
            usage = result.token_usage
            tokens = usage.get("total_tokens", 0) if isinstance(usage, dict) else getattr(usage, "total_tokens", 0)
        elif hasattr(result, "usage_metrics") and result.usage_metrics:
            usage = result.usage_metrics
            tokens = usage.get("total_tokens", 0) if isinstance(usage, dict) else getattr(usage, "total_tokens", 0)
        
        if tokens:
            self.state.update_tokens(tokens)
        else:
            self.state.update_tokens(self.state.estimate_tokens(str(result)))

        return {"processed_text": str(result)}
