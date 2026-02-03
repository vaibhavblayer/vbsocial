"""YouTube analytics (wrapper for existing)."""

import click


def build_youtube():
    """Build YouTube service from credentials."""
    from ..youtube.upload import get_credentials
    from googleapiclient.discovery import build
    credentials = get_credentials()
    return build("youtube", "v3", credentials=credentials)


@click.command(name="stats")
@click.option("--posts", "-p", default=5, help="Number of recent videos to show")
def youtube_stats(posts: int) -> None:
    """Show YouTube channel stats and recent video metrics."""
    try:
        youtube = build_youtube()
        
        # Get channel stats
        response = youtube.channels().list(
            part="snippet,statistics",
            mine=True,
        ).execute()
        
        if not response.get("items"):
            click.echo("❌ YouTube: No channel found")
            return
        
        channel = response["items"][0]
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})
        
        click.echo(f"\n▶️  YouTube: {snippet.get('title', 'N/A')}")
        click.echo("=" * 50)
        click.echo(f"Subscribers: {int(stats.get('subscriberCount', 0)):,}")
        click.echo(f"Total Views: {int(stats.get('viewCount', 0)):,}")
        click.echo(f"Videos: {stats.get('videoCount', 0)}")
        
        if posts > 0:
            # Get recent videos
            channel_id = channel["id"]
            search_resp = youtube.search().list(
                part="id",
                channelId=channel_id,
                maxResults=posts,
                type="video",
                order="date",
            ).execute()
            
            if search_resp.get("items"):
                video_ids = [item["id"]["videoId"] for item in search_resp["items"]]
                
                videos_resp = youtube.videos().list(
                    part="snippet,statistics",
                    id=",".join(video_ids),
                ).execute()
                
                if videos_resp.get("items"):
                    click.echo(f"\n📊 Recent Videos:")
                    click.echo(f"{'Date':<12} {'Views':>10} {'Likes':>8} {'Comments':>8} {'Title':<25}")
                    click.echo("-" * 68)
                    
                    for video in videos_resp["items"]:
                        date = video["snippet"]["publishedAt"][:10]
                        vs = video.get("statistics", {})
                        views = int(vs.get("viewCount", 0))
                        likes = int(vs.get("likeCount", 0))
                        comments = int(vs.get("commentCount", 0))
                        title = video["snippet"]["title"][:23]
                        if len(video["snippet"]["title"]) > 23:
                            title += "…"
                        
                        click.echo(f"{date:<12} {views:>10,} {likes:>8,} {comments:>8,} {title:<25}")
    
    except Exception as e:
        click.echo(f"❌ YouTube: {e}")
