"""src/cli/config.py — CLI Configuration Manager."""

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

FAP_DIR = Path.home() / ".fap"
CONFIG_FILE = FAP_DIR / "config.json"


class CLIConfig(BaseModel):
    """CLI Configuration Schema."""
    api_url: str = Field(default="http://localhost:8000")
    org_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    last_sync: Optional[str] = None

    def save(self):
        """Save configuration to ~/.fap/config.json with restricted permissions."""
        FAP_DIR.mkdir(parents=True, exist_ok=True)
        
        # Note: In Windows, chmod 600 doesn't have the same effect as Linux.
        # We still set it for POSIX compatibility.
        if os.name != 'nt':
            try:
                FAP_DIR.chmod(0o700)
            except Exception:
                pass

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

        if os.name != 'nt':
            try:
                CONFIG_FILE.chmod(0o600)
            except Exception:
                pass

    @classmethod
    def load(cls) -> "CLIConfig":
        """Load configuration from ~/.fap/config.json."""
        if not CONFIG_FILE.exists():
            return cls()

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return cls(**data)
        except Exception:
            # If corrupted, return default
            return cls()
