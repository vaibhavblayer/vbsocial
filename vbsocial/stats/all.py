"""Unified stats command for all platforms."""

import os

import click


def show_instagram_summary():
    """Show Instagram summary."""
    try:
        from .instagram import get_account_insights
        account = get_account_insights()
        click.echo(f"📸 Instagram @{account.get('username', 'N/A')}: "
                   f"{account.get('followers_count', 0):,} followers, "
                   f"{account.get('media_count', 0)} posts")
    except Exception as e:
        click.echo(f"📸 Instagram: ❌ {e}")


def show_facebook_summary():
    """Show Facebook summary."""
    try:
        from .facebook import get_page_info
        page = get_page_info()
        click.echo(f"📘 Facebook {page.get('name', 'N/A')}: "
                   f"{page.get('followers_count', 0):,} followers, "
                   f"{page.get('fan_count', 0):,} likes")
    except Exception as e:
        click.echo(f"📘 Facebook: ❌ {e}")


def show_linkedin_summary():
    """Show LinkedIn summary."""
    try:
        from ..linkedin.auth import create_oauth_session
        from .linkedin import get_profile_info, get_org_info, get_org_followers
        
        access_token = create_oauth_session()
        org_id = os.getenv("LINKEDIN_ORGANIZATION_ID")
        
        if org_id:
            org_info = get_org_info(access_token, org_id)
            followers = get_org_followers(access_token, org_id)
            click.echo(f"💼 LinkedIn {org_info.get('localizedName', 'Org')}: "
                       f"{followers:,} followers")
        else:
            profile = get_profile_info(access_token)
            click.echo(f"💼 LinkedIn {profile.get('name', 'N/A')}: Connected")
    except Exception as e:
        click.echo(f"💼 LinkedIn: ❌ {e}")


def show_x_summary():
    """Show X summary."""
    try:
        from ..x.auth import create_oauth_session
        from .x import get_user_info
        
        access_token = create_oauth_session()
        user = get_user_info(access_token)
        metrics = user.get("public_metrics", {})
        click.echo(f"🐦 X @{user.get('username', 'N/A')}: "
                   f"{metrics.get('followers_count', 0):,} followers, "
                   f"{metrics.get('tweet_count', 0):,} tweets")
    except Exception as e:
        click.echo(f"🐦 X: ❌ {e}")


def show_youtube_summary():
    """Show YouTube summary."""
    try:
        from .youtube import build_youtube
        youtube = build_youtube()
        response = youtube.channels().list(
            part="snippet,statistics",
            mine=True,
        ).execute()
        
        if response.get("items"):
            channel = response["items"][0]
            stats = channel.get("statistics", {})
            name = channel.get("snippet", {}).get("title", "N/A")
            click.echo(f"▶️  YouTube {name}: "
                       f"{int(stats.get('subscriberCount', 0)):,} subs, "
                       f"{int(stats.get('viewCount', 0)):,} views")
        else:
            click.echo("▶️  YouTube: No channel found")
    except Exception as e:
        click.echo(f"▶️  YouTube: ❌ {e}")


@click.command(name="stats")
@click.option("--platform", "-p", 
              type=click.Choice(["all", "instagram", "facebook", "linkedin", "x", "youtube"]),
              default="all", help="Platform to show stats for")
@click.option("--posts", "-n", default=0, help="Number of recent posts to show (0 for summary only)")
def stats(platform: str, posts: int) -> None:
    """Show stats for all social media platforms.
    
    Examples:
        vbsocial stats                    # Quick summary of all platforms
        vbsocial stats -n 5               # Summary + 5 recent posts each
        vbsocial stats -p instagram -n 10 # Instagram with 10 posts
    """
    click.echo("\n" + "=" * 55)
    click.echo("📊 Social Media Stats")
    click.echo("=" * 55)
    
    if platform == "all":
        show_instagram_summary()
        show_facebook_summary()
        show_linkedin_summary()
        show_x_summary()
        show_youtube_summary()
        
        if posts > 0:
            click.echo(f"\nTip: Use 'vbsocial stats -p <platform> -n {posts}' for detailed post metrics")
    else:
        # Import and run specific platform stats
        if platform == "instagram":
            from .instagram import instagram_stats
            ctx = click.Context(instagram_stats)
            ctx.invoke(instagram_stats, posts=posts if posts > 0 else 5)
        elif platform == "facebook":
            from .facebook import facebook_stats
            ctx = click.Context(facebook_stats)
            ctx.invoke(facebook_stats, posts=posts if posts > 0 else 5)
        elif platform == "linkedin":
            from .linkedin import linkedin_stats
            ctx = click.Context(linkedin_stats)
            ctx.invoke(linkedin_stats, posts=posts if posts > 0 else 5)
        elif platform == "x":
            from .x import x_stats
            ctx = click.Context(x_stats)
            ctx.invoke(x_stats, posts=posts if posts > 0 else 5)
        elif platform == "youtube":
            from .youtube import youtube_stats
            ctx = click.Context(youtube_stats)
            ctx.invoke(youtube_stats, posts=posts if posts > 0 else 5)
    
    click.echo("")
