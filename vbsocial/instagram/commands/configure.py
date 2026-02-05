"""Instagram configuration command."""

from datetime import datetime

import click

from ..auth import save_config, load_config, API_VERSION
from ...common.http import get_session, DEFAULT_TIMEOUT
from ...common.config import load_json, get_platform_dir


def _get_existing_config() -> dict | None:
    """Try to load existing config."""
    try:
        config_file = get_platform_dir("instagram") / "config.json"
        return load_json(config_file)
    except Exception:
        return None


@click.command()
def configure() -> None:
    """Configure the Instagram CLI with your app credentials."""
    session = get_session()
    
    # Try to load existing config for defaults
    existing = _get_existing_config()
    
    click.echo("\n" + "=" * 60)
    click.echo("Instagram Configuration")
    click.echo("=" * 60)
    
    if existing:
        click.echo("\n📋 Existing configuration found:")
        click.echo(f"   App ID: {existing.get('app_id', 'N/A')}")
        click.echo(f"   Page ID: {existing.get('page_id', 'N/A')}")
        click.echo(f"   Instagram Account: {existing.get('instagram_account_id', 'N/A')}")
        click.echo(f"   Instagram Username: @{existing.get('instagram_username', 'N/A')}")
        click.echo("\n   Press Enter to keep existing values, or type new ones.")
    
    click.echo("\n📝 To get these values:")
    click.echo("   1. Go to https://developers.facebook.com/apps/")
    click.echo("   2. Select your app (or create one)")
    click.echo("   3. App ID is shown at the top")
    click.echo("   4. App Secret: Settings → Basic → App Secret")
    click.echo("   5. Access Token: Tools → Graph API Explorer")
    click.echo("      - Select your app")
    click.echo("      - Add permissions: pages_show_list, instagram_basic,")
    click.echo("        instagram_content_publish, pages_read_engagement")
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
        # Show masked version
        masked = default_app_secret[:4] + "*" * (len(default_app_secret) - 8) + default_app_secret[-4:]
        click.echo(f"App Secret [current: {masked}]")
        app_secret = click.prompt("App Secret (Enter to keep current)", default="", show_default=False)
        if not app_secret:
            app_secret = default_app_secret
    else:
        app_secret = click.prompt("App Secret", hide_input=True)
    
    # Get Initial Token
    click.echo("\n🔑 Get a fresh access token from Graph API Explorer:")
    click.echo(f"   https://developers.facebook.com/tools/explorer/?app_id={app_id}")
    click.echo("")
    initial_token = click.prompt("Access Token")
    
    config = {
        "app_id": app_id,
        "app_secret": app_secret,
        "access_token": initial_token,
    }
    
    # Get Facebook Pages
    click.echo("\nFetching your Facebook Pages...")
    
    account_url = f"https://graph.facebook.com/{API_VERSION}/me/accounts"
    account_response = session.get(
        account_url,
        params={"access_token": initial_token},
        timeout=DEFAULT_TIMEOUT,
    )
    
    if account_response.status_code != 200:
        try:
            error = account_response.json().get("error", {}).get("message", account_response.text)
        except Exception:
            error = account_response.text
        raise click.ClickException(f"Failed to fetch pages: {error}")
    
    pages = account_response.json().get("data", [])
    if not pages:
        raise click.ClickException(
            "No Facebook Pages found. Make sure your account has access to a Facebook Page "
            "and the token has pages_show_list permission."
        )
    
    # If multiple pages, let user choose
    if len(pages) > 1:
        click.echo("\nAvailable Facebook Pages:")
        for idx, page in enumerate(pages, 1):
            marker = " ← (previously used)" if existing and page["id"] == existing.get("page_id") else ""
            click.echo(f"  {idx}. {page['name']} (ID: {page['id']}){marker}")
        
        # Default to previously used page if exists
        default_idx = 1
        if existing and existing.get("page_id"):
            for idx, page in enumerate(pages, 1):
                if page["id"] == existing.get("page_id"):
                    default_idx = idx
                    break
        
        page_idx = click.prompt("Choose a page number", type=int, default=default_idx) - 1
        page = pages[page_idx]
    else:
        page = pages[0]
    
    click.echo(f"\n✓ Selected page: {page['name']}")
    config["page_id"] = page["id"]
    config["page_access_token"] = page["access_token"]
    
    # Get Instagram Business Account ID for the selected page
    click.echo("Fetching Instagram Business Account...")
    
    ig_url = f"https://graph.facebook.com/{API_VERSION}/{page['id']}"
    ig_response = session.get(
        ig_url,
        params={
            "fields": "instagram_business_account{id,username}",
            "access_token": config["page_access_token"],
        },
        timeout=DEFAULT_TIMEOUT,
    )
    
    if ig_response.status_code != 200:
        raise click.ClickException(f"Failed to fetch Instagram account: {ig_response.text}")
    
    ig_data = ig_response.json()
    if "instagram_business_account" not in ig_data:
        raise click.ClickException(
            "No Instagram Business Account found.\n"
            "Make sure your Facebook Page is connected to an Instagram Professional Account:\n"
            "  1. Go to your Facebook Page settings\n"
            "  2. Click 'Linked Accounts' or 'Instagram'\n"
            "  3. Connect your Instagram Professional account"
        )
    
    ig_account = ig_data["instagram_business_account"]
    config["instagram_account_id"] = ig_account["id"]
    config["instagram_username"] = ig_account.get("username", "")
    
    # Use the page access token
    config["access_token"] = config["page_access_token"]
    
    # Exchange for long-lived page token immediately
    click.echo("\nExchanging for long-lived token...")
    
    # First exchange user token for long-lived user token
    exchange_url = f"https://graph.facebook.com/{API_VERSION}/oauth/access_token"
    exchange_resp = session.get(
        exchange_url,
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": initial_token,
        },
        timeout=DEFAULT_TIMEOUT,
    )
    
    if exchange_resp.status_code == 200:
        long_lived_user_token = exchange_resp.json().get("access_token")
        if long_lived_user_token:
            config["long_lived_user_token"] = long_lived_user_token
            click.echo("✓ Got long-lived user token!")
            
            # Now get the page token with the long-lived user token
            # Page tokens derived from long-lived user tokens are also long-lived (never expire)
            page_token_resp = session.get(
                f"https://graph.facebook.com/{API_VERSION}/{page['id']}",
                params={"fields": "access_token", "access_token": long_lived_user_token},
                timeout=DEFAULT_TIMEOUT,
            )
            
            if page_token_resp.status_code == 200:
                long_lived_page_token = page_token_resp.json().get("access_token")
                if long_lived_page_token:
                    config["access_token"] = long_lived_page_token
                    click.echo("✓ Got long-lived page token!")
    else:
        # Exchange failed - this can happen due to Facebook API issues
        # Fall back to using the page token directly (it's already long-lived)
        try:
            error = exchange_resp.json().get("error", {}).get("message", exchange_resp.text)
        except Exception:
            error = exchange_resp.text
        click.echo(f"⚠️  Token exchange failed: {error}")
        click.echo("   Using page token directly (should still work for ~60 days)")
        # The page_access_token we got earlier is already set in config["access_token"]
    
    # Set expiry - long-lived page tokens don't expire if derived from long-lived user token
    # But we set 60 days as a safety check
    config["token_expiry"] = datetime.now().timestamp() + (60 * 24 * 60 * 60)
    config["token_created"] = datetime.now().isoformat()
    
    save_config(config)
    
    click.echo("\n" + "=" * 60)
    click.echo("✓ Configuration saved successfully!")
    click.echo("=" * 60)
    click.echo(f"\n  Instagram Account: @{config['instagram_username']}")
    click.echo(f"  Account ID: {config['instagram_account_id']}")
    click.echo(f"  Facebook Page: {page['name']} ({config['page_id']})")
    click.echo(f"\n  Token expires: ~60 days")
    click.echo("\nYou can now use:")
    click.echo("  vbsocial instagram post -i image.jpg -c 'Caption'")
    click.echo("  vbsocial instagram post -s -i story.jpg")
