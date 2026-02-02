"""YouTube analytics commands."""

from datetime import datetime

import click
from googleapiclient.discovery import build


def build_youtube():
    """Build YouTube service from credentials."""
    from .upload import get_credentials
    credentials = get_credentials()
    return build("youtube", "v3", credentials=credentials)


@click.command()
def stats() -> None:
    """Show channel statistics (subscribers, total views, video count)."""
    youtube = build_youtube()
    
    response = youtube.channels().list(
        part="statistics",
        mine=True,
    ).execute()
    
    if not response.get("items"):
        click.echo("No channel found!")
        return
    
    stats = response["items"][0]["statistics"]
    
    click.echo("\n=== Channel Statistics ===")
    click.echo(f"Subscribers: {int(stats['subscriberCount']):,}")
    click.echo(f"Total Views: {int(stats['viewCount']):,}")
    click.echo(f"Total Videos: {stats['videoCount']}")


@click.command()
@click.option(
    "--sort-by",
    type=click.Choice(["views", "likes", "comments", "date"]),
    default="date",
    help="Sort videos by metric",
)
@click.option(
    "--limit",
    type=int,
    default=10,
    help="Number of videos to show",
)
@click.option(
    "--top",
    is_flag=True,
    help="Show top videos instead of recent ones",
)
def videos(sort_by: str, limit: int, top: bool) -> None:
    """List videos with their metrics."""
    youtube = build_youtube()
    
    # Get channel ID
    channels_response = youtube.channels().list(
        part="id",
        mine=True,
    ).execute()
    
    if not channels_response.get("items"):
        click.echo("No channel found!")
        return
    
    channel_id = channels_response["items"][0]["id"]
    
    # Get videos
    video_list = []
    next_page_token = None
    
    while True:
        response = youtube.search().list(
            part="id",
            channelId=channel_id,
            maxResults=50,
            type="video",
            pageToken=next_page_token,
            order="relevance" if top else "date",
        ).execute()
        
        if not response.get("items"):
            break
        
        video_ids = [item["id"]["videoId"] for item in response["items"]]
        
        # Get detailed stats
        stats_response = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(video_ids),
        ).execute()
        
        for item in stats_response["items"]:
            video_list.append({
                "id": item["id"],
                "title": item["snippet"]["title"],
                "views": int(item["statistics"].get("viewCount", 0)),
                "likes": int(item["statistics"].get("likeCount", 0)),
                "comments": int(item["statistics"].get("commentCount", 0)),
                "date": datetime.strptime(
                    item["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"
                ),
            })
        
        next_page_token = response.get("nextPageToken")
        if not next_page_token or (not top and len(video_list) >= limit):
            break
    
    if not video_list:
        click.echo("No videos found!")
        return
    
    # Sort videos
    sort_keys = {
        "views": lambda x: x["views"],
        "likes": lambda x: x["likes"],
        "comments": lambda x: x["comments"],
        "date": lambda x: x["date"],
    }
    video_list.sort(key=sort_keys[sort_by], reverse=True)
    
    # Display
    if top:
        click.echo(f"\n=== Top {limit} Videos (sorted by {sort_by}) ===")
    else:
        click.echo(f"\n=== Latest {limit} Videos ===")
    
    click.echo(f"{'ID':<13} {'Title':<40} {'Views':>10} {'Likes':>8} {'Published':>12}")
    click.echo("-" * 87)
    
    for video in video_list[:limit]:
        title = video["title"][:38] + ("…" if len(video["title"]) > 38 else "")
        click.echo(
            f"{video['id']:<13} {title:<40} {video['views']:>10,} "
            f"{video['likes']:>8,} {video['date'].strftime('%Y-%m-%d'):>12}"
        )
    
    click.echo(f"\nTip: Use 'vbsocial youtube info <ID>' to see full details")
