"""Instagram token refresh command."""

from datetime import datetime

import click

from ..auth import load_config, save_config, API_VERSION, _refresh_token
from ...common.http import get_session, DEFAULT_TIMEOUT


@click.command()
@click.option("--force", "-f", is_flag=True, help="Force refresh even if token is valid")
def refresh(force: bool) -> None:
    """Refresh Instagram access token.
    
    Instagram tokens expire after ~60 days. This command refreshes
    the token using the stored long-lived user token.
    
    If refresh fails, you'll need to run 'vbsocial instagram configure'.
    """
    config = load_config()
    
    if "access_token" not in config:
        raise click.ClickException(
            "No token found. Run 'vbsocial instagram configure' first."
        )
    
    session = get_session()
    
    # Check current token status
    click.echo("\n🔍 Checking current token...")
    
    instagram_account_id = config.get("instagram_account_id")
    if instagram_account_id:
        resp = session.get(
            f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}",
            params={"access_token": config["access_token"], "fields": "id,username"},
            timeout=DEFAULT_TIMEOUT,
        )
        
        if resp.status_code == 200:
            data = resp.json()
            click.echo(f"  ✓ Current token is valid")
            click.echo(f"  Account: @{data.get('username', 'unknown')}")
            
            if not force:
                click.echo("\n  Token is working. Use --force to refresh anyway.")
                return
        else:
            click.echo(f"  ✗ Current token is invalid")
    
    # Try to refresh
    click.echo("\n🔄 Refreshing token...")
    
    try:
        new_token = _refresh_token(config)
        
        # Verify the new token
        resp = session.get(
            f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}",
            params={"access_token": new_token, "fields": "id,username"},
            timeout=DEFAULT_TIMEOUT,
        )
        
        if resp.status_code == 200:
            click.echo("\n✓ Token refreshed successfully!")
            
            # Show expiry info
            if "token_expiry" in config:
                expiry = datetime.fromtimestamp(config["token_expiry"])
                click.echo(f"  Expires: {expiry.strftime('%Y-%m-%d')}")
        else:
            click.echo("\n⚠️  Token refreshed but validation failed")
            click.echo("  Try running 'vbsocial instagram configure'")
            
    except click.ClickException as e:
        click.echo(f"\n✗ Refresh failed: {e.message}")
        click.echo("\n  The long-lived user token may have expired.")
        click.echo("  Please run 'vbsocial instagram configure' to re-authenticate.")


@click.command(name="token-info")
def token_info() -> None:
    """Show Instagram token information."""
    config = load_config()
    
    if "access_token" not in config:
        raise click.ClickException("No token found. Run 'vbsocial instagram configure' first.")
    
    session = get_session()
    
    click.echo("\n📋 Instagram Token Info")
    click.echo("=" * 40)
    
    # Basic config info
    click.echo(f"  Username: @{config.get('instagram_username', 'unknown')}")
    click.echo(f"  Account ID: {config.get('instagram_account_id', 'unknown')}")
    click.echo(f"  Page ID: {config.get('page_id', 'unknown')}")
    
    # Token dates
    if "token_created" in config:
        click.echo(f"  Token created: {config['token_created'][:10]}")
    
    if "token_expiry" in config:
        expiry = datetime.fromtimestamp(config["token_expiry"])
        days_left = (expiry - datetime.now()).days
        status = "✓" if days_left > 7 else "⚠️" if days_left > 0 else "✗"
        click.echo(f"  Token expires: {expiry.strftime('%Y-%m-%d')} ({days_left} days) {status}")
    
    # Has long-lived user token?
    has_ll = "long_lived_user_token" in config
    click.echo(f"  Long-lived user token: {'✓ Yes' if has_ll else '✗ No'}")
    
    # Validate current token
    click.echo("\n🔍 Validating token...")
    
    instagram_account_id = config.get("instagram_account_id")
    if instagram_account_id:
        resp = session.get(
            f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}",
            params={"access_token": config["access_token"], "fields": "id,username,followers_count"},
            timeout=DEFAULT_TIMEOUT,
        )
        
        if resp.status_code == 200:
            data = resp.json()
            click.echo(f"  ✓ Token is valid")
            if "followers_count" in data:
                click.echo(f"  Followers: {data['followers_count']}")
        else:
            try:
                error = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                error = resp.text
            click.echo(f"  ✗ Token is invalid: {error}")
            click.echo("\n  Run 'vbsocial instagram refresh' or 'vbsocial instagram configure'")
