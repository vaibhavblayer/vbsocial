"""X (Twitter) OAuth 2.0 authentication with PKCE."""

import os
import base64
import hashlib
import re
from datetime import datetime

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


def create_oauth_session() -> str:
    """Create and configure OAuth 2.0 session with user context.
    
    Returns the access token string.
    """
    client_id, client_secret = get_credentials()
    
    # Try to load existing valid token
    token = _token_manager.get_valid_token()
    
    if token:
        # Validate the token is still working
        if _validate_token(token["access_token"]):
            return token["access_token"]
        
        click.echo("Stored X token appears to be invalid. Re-authorizing...")
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
    return token["access_token"]
