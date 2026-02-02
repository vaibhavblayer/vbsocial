"""Facebook configuration command."""

from datetime import datetime

import click

from ..auth import save_config, API_VERSION
from ...common.http import get_session, DEFAULT_TIMEOUT
from ...common.config import load_json, get_platform_dir


def _get_existing_config() -> dict | None:
    """Try to load existing config."""
    try:
        config_file = get_platform_dir("facebook") / "config.json"
        return load_json(config_file)
    except Exception:
        return None


@click.command()
def configure() -> None:
    """Configure the Facebook CLI with your app credentials."""
    session = get_session()
    
    # Try to load existing config for defaults
    existing = _get_existing_config()
    
    click.echo("\n" + "=" * 60)
    click.echo("Facebook Configuration")
    click.echo("=" * 60)
    
    if existing:
        click.echo("\n📋 Existing configuration found:")
        click.echo(f"   App ID: {existing.get('app_id', 'N/A')}")
        click.echo(f"   Page ID: {existing.get('page_id', 'N/A')}")
        click.echo("\n   Press Enter to keep existing values, or type new ones.")
    
    click.echo("\n📝 To get these values:")
    click.echo("   1. Go to https://developers.facebook.com/apps/")
    click.echo("   2. Select your app (or create one)")
    click.echo("   3. App ID is shown at the top")
    click.echo("   4. App Secret: Settings → Basic → App Secret")
    click.echo("   5. Page ID: Your Facebook Page → About → Page ID")
    click.echo("   6. Access Token: Tools → Graph API Explorer")
    click.echo("      - Select your app and page")
    click.echo("      - Add permissions: pages_manage_posts, pages_read_engagement")
    click.echo("      - Click 'Generate Access Token'")
    click.echo("")
    
    # Get App ID
    default_app_id = existing.get("app_id") if existing else None
    if default_app_id:
        app_id = click.prompt("App ID", default=default_app_id, show_default=True)
    else:
        app_id = click.prompt("App ID")
    
    # Get App Secret
    default_app_secret = existing.get("app_secret") if existing else None
    if default_app_secret:
        masked = default_app_secret[:4] + "*" * (len(default_app_secret) - 8) + default_app_secret[-4:]
        click.echo(f"App Secret [current: {masked}]")
        app_secret = click.prompt("App Secret (Enter to keep current)", default="", show_default=False)
        if not app_secret:
            app_secret = default_app_secret
    else:
        app_secret = click.prompt("App Secret", hide_input=True)
    
    # Get Page ID
    default_page_id = existing.get("page_id") if existing else None
    if default_page_id:
        page_id = click.prompt("Page ID", default=default_page_id, show_default=True)
    else:
        page_id = click.prompt("Page ID")
    
    # Get Initial Token
    click.echo("\n🔑 Get a fresh access token from Graph API Explorer:")
    click.echo(f"   https://developers.facebook.com/tools/explorer/?app_id={app_id}")
    click.echo("")
    initial_token = click.prompt("Access Token (short-lived)")
    
    config = {
        "app_id": app_id,
        "app_secret": app_secret,
        "page_id": page_id,
        "access_token": initial_token,
    }
    
    # Exchange the initial token for a long-lived one
    click.echo("\nExchanging for long-lived token...")
    
    url = f"https://graph.facebook.com/{API_VERSION}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": initial_token,
    }
    
    response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    
    if response.status_code == 200:
        data = response.json()
        config["access_token"] = data["access_token"]
        if "expires_in" in data:
            config["token_expiry"] = datetime.now().timestamp() + data["expires_in"]
        else:
            # Default to 60 days
            config["token_expiry"] = datetime.now().timestamp() + (60 * 24 * 60 * 60)
        
        save_config(config)
        
        click.echo("\n" + "=" * 60)
        click.echo("✓ Configuration saved successfully!")
        click.echo("=" * 60)
        click.echo(f"\n  App ID: {app_id}")
        click.echo(f"  Page ID: {page_id}")
        click.echo(f"  Token expires: ~60 days")
        click.echo("\nYou can now use:")
        click.echo("  vbsocial facebook post photo image.jpg -m 'Caption'")
        click.echo("  vbsocial facebook post video video.mp4 -m 'Caption'")
    else:
        try:
            error = response.json().get("error", {}).get("message", response.text)
        except Exception:
            error = response.text
        raise click.ClickException(f"Failed to exchange token: {error}")
