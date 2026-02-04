"""X (Twitter) OAuth 2.0 authentication with PKCE."""

import os
import base64
import hashlib
import re
from datetime import datetime, timedelta

import click
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth

from ..common.auth import TokenManager
from ..common.http import get_session, DEFAULT_TIMEOUT

AUTH_URL = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"

_token_manager = TokenManager("x")


def get_credentials() -> tuple[str, str]:
    """Get OAuth credentials from environment."""
    client_id = os.environ.get("X_CLIENT_ID_10X")
    client_secret = os.environ.get("X_CLIENT_SECRET_10X")
    
    if not client_id or not client_secret:
        raise click.ClickException(
            "Missing environment variables. Please set:\n"
            "  export X_CLIENT_ID_10X='your_client_id'\n"
            "  export X_CLIENT_SECRET_10X='your_client_secret'"
        )
    
    return client_id, client_secret


def _validate_token(access_token: str) -> bool:
    """Validate token by making a test API call."""
    session = get_session()
    
    try:
        resp = session.get(
            "https://api.x.com/2/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=DEFAULT_TIMEOUT,
        )
        return resp.status_code == 200
    except Exception:
        return True  # Assume valid on network errors


def _refresh_token(token: dict) -> dict | None:
    """Refresh the access token using the refresh token.
    
    X OAuth 2.0 tokens expire after 2 hours but can be refreshed
    using the refresh_token (requires offline.access scope).
    """
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        return None
    
    client_id, client_secret = get_credentials()
    session = get_session()
    
    click.echo("  Refreshing X access token...")
    
    try:
        resp = session.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
            },
            auth=HTTPBasicAuth(client_id, client_secret),
            timeout=DEFAULT_TIMEOUT,
        )
        
        if resp.status_code == 200:
            new_token = resp.json()
            # Add expires_at timestamp
            new_token["expires_at"] = datetime.now().timestamp() + new_token.get("expires_in", 7200)
            _token_manager.save(new_token)
            click.echo("✓ X token refreshed successfully!")
            return new_token
        else:
            click.echo(f"  ⚠️  Refresh failed: {resp.text}")
            return None
    except Exception as e:
        click.echo(f"  ⚠️  Refresh error: {e}")
        return None


def create_oauth_session() -> str:
    """Create and configure OAuth 2.0 session with user context.
    
    Returns the access token string.
    """
    client_id, client_secret = get_credentials()
    
    # Try to load existing token
    token = _token_manager.load()
    
    if token:
        # Check if token is expired or expiring soon (within 10 minutes)
        if "expires_at" in token:
            expiry = datetime.fromtimestamp(token["expires_at"])
            refresh_threshold = expiry - timedelta(minutes=10)
            
            if datetime.now() > expiry:
                click.echo("X token expired, attempting refresh...")
                new_token = _refresh_token(token)
                if new_token:
                    return new_token["access_token"]
                # If refresh fails, continue to re-auth
            elif datetime.now() > refresh_threshold:
                click.echo("X token expiring soon, refreshing...")
                new_token = _refresh_token(token)
                if new_token:
                    return new_token["access_token"]
                # If refresh fails, use current token
                if _validate_token(token["access_token"]):
                    return token["access_token"]
            else:
                # Token is still valid
                if _validate_token(token["access_token"]):
                    return token["access_token"]
                
                # Token validation failed, try refresh
                click.echo("X token validation failed, attempting refresh...")
                new_token = _refresh_token(token)
                if new_token:
                    return new_token["access_token"]
        else:
            # No expiry info, validate and use
            if _validate_token(token["access_token"]):
                return token["access_token"]
        
        click.echo("Stored X token is invalid. Re-authorizing...")
        _token_manager.delete()
    
    # No valid token exists, get a new one
    scopes = ["tweet.read", "tweet.write", "users.read", "offline.access"]
    
    # Create code verifier and challenge for PKCE
    code_verifier = base64.urlsafe_b64encode(os.urandom(30)).decode("utf-8")
    code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)
    
    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
    code_challenge = code_challenge.replace("=", "")
    
    # Create OAuth session
    oauth = OAuth2Session(
        client_id,
        redirect_uri="https://localhost",
        scope=scopes,
    )
    
    # Get authorization URL
    auth_url, state = oauth.authorization_url(
        AUTH_URL,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    
    click.echo("\n" + "=" * 60)
    click.echo("X (Twitter) Authorization Required")
    click.echo("=" * 60)
    click.echo("\n1. Open this URL in your browser:")
    click.echo(f"\n   {auth_url}\n")
    click.echo("2. Authorize the application")
    click.echo("3. You'll be redirected to a URL starting with https://localhost")
    click.echo("4. Copy the ENTIRE URL from your browser's address bar")
    click.echo("   (It will show an error page, that's normal)\n")
    
    auth_response = click.prompt("Paste the full callback URL here")
    
    try:
        # Fetch token with PKCE
        token = oauth.fetch_token(
            token_url=TOKEN_URL,
            authorization_response=auth_response,
            code_verifier=code_verifier,
            client_id=client_id,
            client_secret=client_secret,
            auth=HTTPBasicAuth(client_id, client_secret),
        )
    except Exception as e:
        raise click.ClickException(
            f"Failed to get token: {e}\n"
            "Make sure you copied the complete URL including all parameters."
        )
    
    # Add expires_at timestamp
    token["expires_at"] = datetime.now().timestamp() + token.get("expires_in", 7200)
    
    # Save token for future use
    _token_manager.save(token)
    
    click.echo("\n✓ X authentication successful!")
    click.echo(f"  Token expires in {token.get('expires_in', 7200) // 60} minutes")
    click.echo("  (Will auto-refresh using refresh_token)")
    return token["access_token"]


def refresh_x_token() -> str | None:
    """Manually refresh the X token. Returns new access token or None."""
    token = _token_manager.load()
    if not token:
        raise click.ClickException("No X token found. Please authorize first.")
    
    new_token = _refresh_token(token)
    if new_token:
        return new_token["access_token"]
    return None
