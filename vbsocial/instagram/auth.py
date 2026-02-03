"""Instagram authentication and token management."""

from datetime import datetime

import click

from ..common.auth import ConfigManager
from ..common.http import get_session, DEFAULT_TIMEOUT

API_VERSION = "v19.0"

_config_manager = ConfigManager("instagram")


def load_config() -> dict:
    """Load Instagram config."""
    return _config_manager.load()


def save_config(config: dict) -> None:
    """Save Instagram config."""
    _config_manager.save(config)


def _validate_token(token: str, config: dict) -> bool:
    """Validate token using Facebook's debug_token API or a test call."""
    session = get_session()
    
    # First try a simple API call
    instagram_account_id = config.get("instagram_account_id")
    if instagram_account_id:
        try:
            resp = session.get(
                f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}",
                params={"access_token": token, "fields": "id"},
                timeout=DEFAULT_TIMEOUT,
            )
            if resp.status_code == 200:
                return True
            if resp.status_code in (400, 401, 403):
                return False
        except Exception:
            pass
    
    # Fallback to debug_token API
    app_id = config.get("app_id")
    app_secret = config.get("app_secret")
    
    if not (app_id and app_secret):
        return True  # Can't validate without credentials
    
    try:
        resp = session.get(
            "https://graph.facebook.com/debug_token",
            params={
                "input_token": token,
                "access_token": f"{app_id}|{app_secret}",
            },
            timeout=DEFAULT_TIMEOUT,
        )
        
        if resp.status_code != 200:
            return True  # Assume valid on debug failure
        
        data = resp.json().get("data", {})
        if not data.get("is_valid", False):
            return False
        
        # Update stored expiry if available
        if "expires_at" in data and data["expires_at"] > 0:
            config["token_expiry"] = data["expires_at"]
            save_config(config)
        
        return True
    except Exception:
        return True  # Assume valid on network errors


def get_access_token(auto_refresh: bool = True) -> str:
    """Get the access token, refreshing if needed."""
    config = load_config()
    
    if "access_token" not in config:
        raise click.ClickException(
            "Access token not found. Please run 'vbsocial instagram configure' first."
        )
    
    token = config["access_token"]
    
    # Check if token needs refresh based on stored expiry
    if auto_refresh and "token_expiry" in config:
        expiry = datetime.fromtimestamp(config["token_expiry"])
        if datetime.now() > expiry:
            click.echo("Token expired, attempting refresh...")
            try:
                token = _refresh_token(config)
            except click.ClickException as e:
                raise click.ClickException(
                    f"{e.message}\n"
                    "Please run 'vbsocial instagram configure' to re-authenticate."
                )
    
    # Validate the token
    if not _validate_token(token, config):
        raise click.ClickException(
            "Instagram access token is no longer valid.\n"
            "Please run 'vbsocial instagram configure' to re-authenticate."
        )
    
    return token


def _refresh_token(config: dict) -> str:
    """Refresh the access token.
    
    For Page Access Tokens (used with Instagram Graph API), we need to
    exchange for a new long-lived token using the app credentials.
    """
    session = get_session()
    
    app_id = config.get("app_id")
    app_secret = config.get("app_secret")
    
    if not (app_id and app_secret):
        raise click.ClickException(
            "App ID and App Secret required for token refresh.\n"
            "Please run 'vbsocial instagram configure' to set up."
        )
    
    # For Page tokens, exchange for long-lived token
    url = f"https://graph.facebook.com/{API_VERSION}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": config["access_token"],
    }
    
    response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    
    if response.status_code == 200:
        data = response.json()
        new_token = data.get("access_token")
        
        if new_token:
            # Now get the page token with the new long-lived user token
            page_id = config.get("page_id")
            if page_id:
                page_resp = session.get(
                    f"https://graph.facebook.com/{API_VERSION}/{page_id}",
                    params={"fields": "access_token", "access_token": new_token},
                    timeout=DEFAULT_TIMEOUT,
                )
                if page_resp.status_code == 200:
                    page_data = page_resp.json()
                    config["access_token"] = page_data.get("access_token", new_token)
                else:
                    config["access_token"] = new_token
            else:
                config["access_token"] = new_token
            
            # Long-lived page tokens don't expire, but set 60 days as safety
            config["token_expiry"] = datetime.now().timestamp() + (60 * 24 * 60 * 60)
            save_config(config)
            click.echo("✓ Access token refreshed successfully!")
            return config["access_token"]
    
    # If exchange fails, try the Instagram Basic Display refresh (fallback)
    ig_url = "https://graph.instagram.com/refresh_access_token"
    ig_params = {
        "grant_type": "ig_refresh_token",
        "access_token": config["access_token"],
    }
    
    ig_response = session.get(ig_url, params=ig_params, timeout=DEFAULT_TIMEOUT)
    
    if ig_response.status_code == 200:
        data = ig_response.json()
        config["access_token"] = data["access_token"]
        if "expires_in" in data:
            config["token_expiry"] = datetime.now().timestamp() + data["expires_in"]
        save_config(config)
        click.echo("✓ Access token refreshed successfully!")
        return config["access_token"]
    
    try:
        error = response.json().get("error", {}).get("message", response.text)
    except Exception:
        error = response.text
    raise click.ClickException(f"Failed to refresh token: {error}")
