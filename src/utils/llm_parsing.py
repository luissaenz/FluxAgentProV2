"""src/utils/llm_parsing.py — Helpers for parsing LLM outputs and tracking tokens."""

import json
import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Find the first JSON object in a block of text.

    Compatible with common LLM patterns like markdown blocks or plain text wraps.
    """
    try:
        # Search for { ... } - non-greedy might be better if multiple,
        # but usually we want the whole definition block.
        json_match = re.search(r"(\{[\s\S]*\})", text)
        if json_match:
            raw_text = json_match.group(1).strip()
            return json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse extracted JSON: %s", e)
    except Exception as e:
        logger.error("Unexpected error extracting JSON: %s", e)
    return None


def extract_token_usage(crew_output: Any) -> int:
    """
    Extract total tokens from CrewAI output, handling different versions and attribute names.

    Supports:
    - result.token_usage (dict or object)
    - result.usage_metrics (dict or object)
    """
    tokens = 0
    # Try token_usage attribute
    if hasattr(crew_output, "token_usage") and crew_output.token_usage:
        usage = crew_output.token_usage
        tokens = (
            usage.get("total_tokens", 0)
            if isinstance(usage, dict)
            else getattr(usage, "total_tokens", 0)
        )
    # Try usage_metrics attribute (fallback for other versions)
    elif hasattr(crew_output, "usage_metrics") and crew_output.usage_metrics:
        usage = crew_output.usage_metrics
        tokens = (
            usage.get("total_tokens", 0)
            if isinstance(usage, dict)
            else getattr(usage, "total_tokens", 0)
        )

    return int(tokens)
