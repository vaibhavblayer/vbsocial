"""Shared configuration utilities for all platforms."""

import os
import json
import stat
from pathlib import Path
from typing import Any

# Base directory for all vbsocial config/tokens
VBSOCIAL_DIR = Path.home() / ".vbsocial"


def get_platform_dir(platform: str) -> Path:
    """Get the config directory for a specific platform."""
    return VBSOCIAL_DIR / platform


def ensure_dir(path: Path) -> None:
    """Create directory with secure permissions if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    # Set directory permissions to owner-only (700)
    os.chmod(path, stat.S_IRWXU)


def save_json(path: Path, data: dict[str, Any]) -> None:
    """Save JSON data to file with secure permissions."""
    ensure_dir(path.parent)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
    # Set file permissions to owner read/write only (600)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def load_json(path: Path) -> dict[str, Any] | None:
    """Load JSON data from file, returns None if not found."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None
