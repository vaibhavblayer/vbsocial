"""Facebook analytics."""

import click

from ..facebook.auth import get_access_token, load_config, API_VERSION
from ..common.http import get_session, DEFAULT_TIMEOUT


def get_page_info() -> dict:
    """Get Facebook page info and stats."""
    config = load_config()
    access_token = get_access_token()
    page_id = config.get("page_id")
    session = get_session()
    
    if not page_id:
        raise click.ClickException("No page_id in config. Run 'vbsocial facebook configure'")
    
    page_url = f"https://graph.facebook.com/{API_VERSION}/{page_id}"
    page_resp = session.get(
        page_url,
        params={
            "fields": "name,followers_count,fan_count,new_like_count",
            "access_token": access_token,
        },
        timeout=DEFAULT_TIMEOUT,
    )
    page_resp.raise_for_status()
    return page_resp.json()


def get_recent_posts(limit: int = 10) -> list:
    """Get recent posts with metrics."""
    config = load_config()
    access_token = get_access_token()
    page_id = config.get("page_id")
    session = get_session()
    
    posts_url = f"https://graph.facebook.com/{API_VERSION}/{page_id}/posts"
    posts_resp = session.get(
        posts_url,
        params={
            "fields": "id,message,created_time,shares,reactions.summary(true),comments.summary(true)",
            "limit": limit,
            "access_token": access_token,
        },
        timeout=DEFAULT_TIMEOUT,
    )
    posts_resp.raise_for_status()
    return posts_resp.json().get("data", [])


@click.command(name="stats")
@click.option("--posts", "-p", default=5, help="Number of recent posts to show")
def facebook_stats(posts: int) -> None:
    """Show Facebook page stats and recent post metrics."""
    try:
        page = get_page_info()
        
        click.echo(f"\n📘 Facebook: {page.get('name', 'N/A')}")
        click.echo("=" * 50)
        click.echo(f"Followers: {page.get('followers_count', 0):,}")
        click.echo(f"Page Likes: {page.get('fan_count', 0):,}")
        
        if posts > 0:
            post_list = get_recent_posts(posts)
            if post_list:
                click.echo(f"\n📊 Recent Posts:")
                click.echo(f"{'Date':<12} {'Reactions':>10} {'Comments':>10} {'Shares':>8} {'Message':<25}")
                click.echo("-" * 70)
                
                for item in post_list:
                    date = item.get("created_time", "")[:10]
                    reactions = item.get("reactions", {}).get("summary", {}).get("total_count", 0)
                    comments = item.get("comments", {}).get("summary", {}).get("total_count", 0)
                    shares = item.get("shares", {}).get("count", 0)
                    message = (item.get("message") or "")[:23]
                    if len(item.get("message") or "") > 23:
                        message += "…"
                    
                    click.echo(f"{date:<12} {reactions:>10,} {comments:>10,} {shares:>8,} {message:<25}")
    
    except Exception as e:
        click.echo(f"❌ Facebook: {e}")
