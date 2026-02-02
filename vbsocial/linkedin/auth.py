"""LinkedIn OAuth 2.0 authentication."""

import os
from urllib.parse import parse_qs, urlparse

import click
from requests_oauthlib import OAuth2Session

from ..common.auth import TokenManager
from ..common.http import get_session, DEFAULT_TIMEOUT

# LinkedIn OAuth2 settings
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
REDIRECT_URI = "https://localhost"
SCOPE = ["openid", "profile", "w_member_social", "w_organization_social"]

_token_manager = TokenManager("linkedin")


def get_credentials() -> tuple[str, str]:
    """Get OAuth credentials from environment."""
    client_id = os.getenv("LINKEDIN_CLIENT_ID_10X")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET_10X")
    
    if not client_id or not client_secret:
        raise click.ClickException(
            "Missing environment variables. Please set:\n"
            "  export LINKEDIN_CLIENT_ID_10X='your_client_id'\n"
            "  export LINKEDIN_CLIENT_SECRET_10X='your_client_secret'"
        )
    
    return client_id, client_secret


def _validate_token(access_token: str) -> bool:
    """Validate token by calling the userinfo endpoint."""
    session = get_session()
    
    try:
        resp = session.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=DEFAULT_TIMEOUT,
        )
        return resp.status_code == 200
    except Exception:
        return True  # Assume valid on network errors


def create_oauth_session() -> str:
    """Create an OAuth session with LinkedIn.
    
    Returns the access token string.
    """
    # Try to load existing token
    token = _token_manager.load()
    
    if token and "access_token" in token:
        access_token = token["access_token"]
        
        if _validate_token(access_token):
            return access_token
        
        click.echo("Stored LinkedIn token appears to be expired/invalid. Re-authorizing...")
        _token_manager.delete()
    
    # Get new token
    client_id, client_secret = get_credentials()
    
    linkedin = OAuth2Session(client_id, redirect_uri=REDIRECT_URI, scope=SCOPE)
    authorization_url, state = linkedin.authorization_url(AUTH_URL)
    
    click.echo("\n" + "=" * 60)
    click.echo("LinkedIn Authorization Required")
    click.echo("=" * 60)
    click.echo("\n1. Open this URL in your browser:")
    click.echo(f"\n   {authorization_url}\n")
    click.echo("2. Sign in and authorize the application")
    click.echo("3. You'll be redirected to a URL starting with https://localhost")
    click.echo("4. Copy the ENTIRE URL from your browser's address bar")
    click.echo("   (It will show an error page, that's normal)\n")
    
    redirect_response = click.prompt("Paste the full redirect URL here")
    
    # Parse the redirect URL
    parsed_url = urlparse(redirect_response)
    params = parse_qs(parsed_url.query)
    
    # Check for errors
    if "error" in params:
        error_desc = params.get("error_description", ["Unknown error"])[0]
        raise click.ClickException(f"Authorization failed: {error_desc}")
    
    if "code" not in params:
        raise click.ClickException(
            "No authorization code found in the URL.\n"
            "Make sure you copied the complete URL including all parameters."
        )
    
    code = params["code"][0]
    
    # Exchange code for token
    session = get_session()
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    response = session.post(TOKEN_URL, data=token_data, timeout=DEFAULT_TIMEOUT)
    token = response.json()
    
    if "error" in token:
        raise click.ClickException(
            f"Failed to get token: {token.get('error_description', token['error'])}"
        )
    
    _token_manager.save(token)
    
    click.echo("\n✓ LinkedIn authentication successful!")
    return token["access_token"]
