"""Shared authentication utilities for OAuth flows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import click

from .config import load_json, save_json, get_platform_dir


class TokenManager:
    """Manages OAuth tokens with caching and expiry checking."""
    
    def __init__(self, platform: str, token_filename: str = "token.json"):
        self.platform = platform
        self.token_file = get_platform_dir(platform) / token_filename
    
    def load(self) -> dict[str, Any] | None:
        """Load token from file if it exists."""
        return load_json(self.token_file)
    
    def save(self, token: dict[str, Any]) -> None:
        """Save token to file with secure permissions."""
        save_json(self.token_file, token)
    
    def delete(self) -> None:
        """Delete the token file."""
        try:
            self.token_file.unlink()
        except FileNotFoundError:
            pass
    
    def is_expired(self, token: dict[str, Any], buffer_minutes: int = 5) -> bool:
        """Check if token is expired or will expire soon."""
        if "expires_at" not in token:
            return False
        
        expiry = datetime.fromtimestamp(token["expires_at"])
        from datetime import timedelta
        return datetime.now() > expiry - timedelta(minutes=buffer_minutes)
    
    def get_valid_token(self) -> dict[str, Any] | None:
        """Get token if it exists and is not expired."""
        token = self.load()
        if token and not self.is_expired(token):
            return token
        return None


class ConfigManager:
    """Manages platform configuration files."""
    
    def __init__(self, platform: str, config_filename: str = "config.json"):
        self.platform = platform
        self.config_file = get_platform_dir(platform) / config_filename
    
    def load(self) -> dict[str, Any]:
        """Load config, raises ClickException if not found."""
        config = load_json(self.config_file)
        if config is None:
            raise click.ClickException(
                f"Config not found. Please run 'vbsocial {self.platform} configure' first."
            )
        return config
    
    def save(self, config: dict[str, Any]) -> None:
        """Save config to file with secure permissions."""
        save_json(self.config_file, config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a specific config value."""
        config = self.load()
        return config.get(key, default)
