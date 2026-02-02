"""YouTube video info command."""

import click
from googleapiclient.discovery import build

from .upload import get_credentials


@click.command()
@click.argument("video_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def info(video_id: str, as_json: bool) -> None:
    """View detailed information about a video.
    
    VIDEO_ID can be the full URL or just the ID.
    
    Examples:
        vbsocial youtube info dQw4w9WgXcQ
        vbsocial youtube info https://youtube.com/watch?v=dQw4w9WgXcQ
        vbsocial youtube info https://youtu.be/dQw4w9WgXcQ
    """
    # Extract video ID from URL if needed
    video_id = _extract_video_id(video_id)
    
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)
    
    response = youtube.videos().list(
        part="snippet,statistics,status,contentDetails",
        id=video_id,
    ).execute()
    
    if not response.get("items"):
        raise click.ClickException(f"Video not found: {video_id}")
    
    video = response["items"][0]
    snippet = video["snippet"]
    stats = video.get("statistics", {})
    status = video["status"]
    content = video.get("contentDetails", {})
    
    if as_json:
        import json
        click.echo(json.dumps(video, indent=2))
        return
    
    # Display formatted info
    click.echo(f"\n{'='*60}")
    click.echo(f"Title: {snippet['title']}")
    click.echo(f"{'='*60}")
    click.echo(f"\nChannel: {snippet['channelTitle']}")
    click.echo(f"Published: {snippet['publishedAt'][:10]}")
    click.echo(f"Privacy: {status['privacyStatus']}")
    click.echo(f"Duration: {_format_duration(content.get('duration', 'PT0S'))}")
    
    click.echo(f"\n--- Statistics ---")
    click.echo(f"Views: {int(stats.get('viewCount', 0)):,}")
    click.echo(f"Likes: {int(stats.get('likeCount', 0)):,}")
    click.echo(f"Comments: {int(stats.get('commentCount', 0)):,}")
    
    click.echo(f"\n--- Description ---")
    desc = snippet.get("description", "")
    click.echo(desc[:500] + ("..." if len(desc) > 500 else ""))
    
    tags = snippet.get("tags", [])
    if tags:
        click.echo(f"\n--- Tags ({len(tags)}) ---")
        click.echo(", ".join(tags[:20]))
        if len(tags) > 20:
            click.echo(f"... and {len(tags) - 20} more")
    
    click.echo(f"\n--- URLs ---")
    click.echo(f"Watch: https://youtube.com/watch?v={video_id}")
    click.echo(f"Short: https://youtu.be/{video_id}")


def _extract_video_id(url_or_id: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    import re
    
    # Already just an ID
    if re.match(r"^[a-zA-Z0-9_-]{11}$", url_or_id):
        return url_or_id
    
    # youtu.be/ID
    match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url_or_id)
    if match:
        return match.group(1)
    
    # youtube.com/watch?v=ID
    match = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", url_or_id)
    if match:
        return match.group(1)
    
    # youtube.com/shorts/ID
    match = re.search(r"/shorts/([a-zA-Z0-9_-]{11})", url_or_id)
    if match:
        return match.group(1)
    
    # Assume it's an ID
    return url_or_id


def _format_duration(iso_duration: str) -> str:
    """Convert ISO 8601 duration to human readable format."""
    import re
    
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not match:
        return iso_duration
    
    hours, minutes, seconds = match.groups()
    parts = []
    
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds or 0}s")
    
    return " ".join(parts)
