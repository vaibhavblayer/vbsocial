"""Instagram analytics."""

import click

from ..instagram.auth import get_access_token, load_config, API_VERSION
from ..common.http import get_session, DEFAULT_TIMEOUT


def get_account_insights() -> dict:
    """Get Instagram account insights."""
    config = load_config()
    access_token = get_access_token()
    ig_account_id = config["instagram_account_id"]
    session = get_session()
    
    # Get basic account info
    account_url = f"https://graph.facebook.com/{API_VERSION}/{ig_account_id}"
    account_resp = session.get(
        account_url,
        params={
            "fields": "username,followers_count,follows_count,media_count",
            "access_token": access_token,
        },
        timeout=DEFAULT_TIMEOUT,
    )
    account_resp.raise_for_status()
    return account_resp.json()


def get_recent_media(limit: int = 10) -> list:
    """Get recent media with insights."""
    config = load_config()
    access_token = get_access_token()
    ig_account_id = config["instagram_account_id"]
    session = get_session()
    
    # Get recent media
    media_url = f"https://graph.facebook.com/{API_VERSION}/{ig_account_id}/media"
    media_resp = session.get(
        media_url,
        params={
            "fields": "id,caption,media_type,timestamp,like_count,comments_count,permalink",
            "limit": limit,
            "access_token": access_token,
        },
        timeout=DEFAULT_TIMEOUT,
    )
    media_resp.raise_for_status()
    return media_resp.json().get("data", [])


def get_media_insights(media_id: str) -> dict:
    """Get insights for a specific media."""
    access_token = get_access_token()
    session = get_session()
    
    insights_url = f"https://graph.facebook.com/{API_VERSION}/{media_id}/insights"
    insights_resp = session.get(
        insights_url,
        params={
            "metric": "impressions,reach,saved",
            "access_token": access_token,
        },
        timeout=DEFAULT_TIMEOUT,
    )
    
    if insights_resp.status_code != 200:
        return {}
    
    data = insights_resp.json().get("data", [])
    return {item["name"]: item["values"][0]["value"] for item in data}


@click.command(name="stats")
@click.option("--posts", "-p", default=5, help="Number of recent posts to show")
def instagram_stats(posts: int) -> None:
    """Show Instagram account stats and recent post metrics."""
    try:
        account = get_account_insights()
        
        click.echo(f"\n📸 Instagram: @{account.get('username', 'N/A')}")
        click.echo("=" * 50)
        click.echo(f"Followers: {account.get('followers_count', 0):,}")
        click.echo(f"Following: {account.get('follows_count', 0):,}")
        click.echo(f"Posts: {account.get('media_count', 0):,}")
        
        if posts > 0:
            media = get_recent_media(posts)
            if media:
                click.echo(f"\n📊 Recent Posts:")
                click.echo(f"{'Date':<12} {'Type':<10} {'Likes':>8} {'Comments':>8} {'Caption':<30}")
                click.echo("-" * 72)
                
                for item in media:
                    date = item.get("timestamp", "")[:10]
                    media_type = item.get("media_type", "")[:8]
                    likes = item.get("like_count", 0)
                    comments = item.get("comments_count", 0)
                    caption = (item.get("caption") or "")[:28]
                    if len(item.get("caption") or "") > 28:
                        caption += "…"
                    
                    click.echo(f"{date:<12} {media_type:<10} {likes:>8,} {comments:>8,} {caption:<30}")
    
    except Exception as e:
        click.echo(f"❌ Instagram: {e}")
