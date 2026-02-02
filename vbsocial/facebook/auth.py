"""Facebook authentication and token management."""

from datetime import datetime

import click

from ..common.auth import ConfigManager
from ..common.http import get_session, DEFAULT_TIMEOUT

API_VERSION = "v19.0"

_config_manager = ConfigManager("facebook")


def load_config() -> dict:
    """Load Facebook config."""
    return _config_manager.load()


def save_config(config: dict) -> None:
    """Save Facebook config."""
    _config_manager.save(config)


def _validate_token(access_token: str) -> bool:
    """Validate token by making a test API call."""
    session = get_session()
    
    try:
        resp = session.get(
            f"https://graph.facebook.com/{API_VERSION}/me",
            params={"access_token": access_token},
            timeout=DEFAULT_TIMEOUT,
        )
        return resp.status_code == 200
    except Exception:
        return True  # Assume valid on network errors


def get_access_token(auto_refresh: bool = True) -> str:
    """Get the access token, refreshing if needed."""
    config = load_config()
    
    if "access_token" not in config:
        raise click.ClickException(
            "Access token not found. Please run 'vbsocial facebook configure' first."
        )
    
    token = config["access_token"]
    
    # Check if token needs refresh based on stored expiry
    if auto_refresh and "token_expiry" in config:
        expiry = datetime.fromtimestamp(config["token_expiry"])
        if datetime.now() > expiry:
            click.echo("Token expired, attempting refresh...")
            return _refresh_token(config)
    
    # Validate the token is still working
    if not _validate_token(token):
        click.echo("Token appears invalid, attempting refresh...")
        try:
            return _refresh_token(config)
        except click.ClickException:
            raise click.ClickException(
                "Facebook token is invalid and refresh failed.\n"
                "Please run 'vbsocial facebook configure' to re-authenticate."
            )
    
    return token


def _refresh_token(config: dict) -> str:
    """Refresh the access token using app credentials."""
    if "app_id" not in config or "app_secret" not in config:
        raise click.ClickException(
            "Cannot refresh token: app_id or app_secret missing from config.\n"
            "Please run 'vbsocial facebook configure' to set up credentials."
        )
    
    session = get_session()
    
    url = f"https://graph.facebook.com/{API_VERSION}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": config["app_id"],
        "client_secret": config["app_secret"],
        "fb_exchange_token": config["access_token"],
    }
    
    response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    
    if response.status_code == 200:
        data = response.json()
        config["access_token"] = data["access_token"]
        if "expires_in" in data:
            config["token_expiry"] = datetime.now().timestamp() + data["expires_in"]
        save_config(config)
        click.echo("✓ Access token refreshed successfully!")
        return config["access_token"]
    else:
        try:
            error = response.json().get("error", {}).get("message", response.text)
        except Exception:
            error = response.text
        raise click.ClickException(f"Failed to refresh token: {error}")
