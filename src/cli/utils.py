"""src/cli/utils.py — CLI-specific utilities for FAP-CLI."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def save_json(path: Path, data: Any):
    """Save data as pretty-printed JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(path: Path) -> Any:
    """Load JSON data from a file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
