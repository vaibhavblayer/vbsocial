"""X (Twitter) analytics."""

import click

from ..x.auth import create_oauth_session
from ..common.http import get_session, DEFAULT_TIMEOUT


def get_user_info(access_token: str) -> dict:
    """Get X user info."""
    session = get_session()
    
    resp = session.get(
        "https://api.twitter.com/2/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"user.fields": "public_metrics,username,name"},
        timeout=DEFAULT_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("data", {})


def get_recent_tweets(access_token: str, user_id: str, limit: int = 10) -> list:
    """Get recent tweets with metrics."""
    session = get_session()
    
    resp = session.get(
        f"https://api.twitter.com/2/users/{user_id}/tweets",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "max_results": min(limit, 100),
            "tweet.fields": "created_at,public_metrics,text",
        },
        timeout=DEFAULT_TIMEOUT,
    )
    
    if resp.status_code != 200:
        return []
    
    return resp.json().get("data", [])


@click.command(name="stats")
@click.option("--posts", "-p", default=5, help="Number of recent tweets to show")
def x_stats(posts: int) -> None:
    """Show X account stats and recent tweet metrics."""
    try:
        access_token = create_oauth_session()
        user = get_user_info(access_token)
        metrics = user.get("public_metrics", {})
        
        click.echo(f"\n🐦 X: @{user.get('username', 'N/A')}")
        click.echo("=" * 50)
        click.echo(f"Followers: {metrics.get('followers_count', 0):,}")
        click.echo(f"Following: {metrics.get('following_count', 0):,}")
        click.echo(f"Tweets: {metrics.get('tweet_count', 0):,}")
        
        if posts > 0:
            tweets = get_recent_tweets(access_token, user.get("id"), posts)
            if tweets:
                click.echo(f"\n📊 Recent Tweets:")
                click.echo(f"{'Date':<12} {'Likes':>8} {'Retweets':>10} {'Replies':>8} {'Text':<25}")
                click.echo("-" * 68)
                
                for tweet in tweets:
                    date = tweet.get("created_at", "")[:10]
                    pm = tweet.get("public_metrics", {})
                    likes = pm.get("like_count", 0)
                    retweets = pm.get("retweet_count", 0)
                    replies = pm.get("reply_count", 0)
                    text = (tweet.get("text") or "")[:23]
                    if len(tweet.get("text") or "") > 23:
                        text += "…"
                    
                    click.echo(f"{date:<12} {likes:>8,} {retweets:>10,} {replies:>8,} {text:<25}")
    
    except Exception as e:
        click.echo(f"❌ X: {e}")
