"""YouTube Shorts upload command."""

import os

import click
from googleapiclient.http import MediaFileUpload

from .upload import get_credentials
from googleapiclient.discovery import build


@click.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("-t", "--title", required=True, help="Short title (max 100 chars)")
@click.option("-d", "--description", default="", help="Short description")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option(
    "-p", "--privacy",
    type=click.Choice(["private", "public", "unlisted"], case_sensitive=False),
    default="private",
    help="Privacy status",
)
def shorts(video_path: str, title: str, description: str, tags: str, privacy: str) -> None:
    """Upload a YouTube Short (vertical video, max 60 seconds).
    
    Example:
        vbsocial youtube shorts video.mp4 -t "My Short" -d "Description" --tags "tag1,tag2"
    """
    # Validate title length
    if len(title) > 100:
        raise click.ClickException("Title must be 100 characters or less")
    
    # Add #Shorts to description if not present (helps YouTube identify it as a Short)
    if "#shorts" not in description.lower():
        description = f"{description}\n\n#Shorts".strip()
    
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)
    
    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    if "Shorts" not in tag_list:
        tag_list.append("Shorts")
    
    click.echo(f"Uploading Short: {title}")
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tag_list,
            "categoryId": "22",  # People & Blogs (common for Shorts)
        },
        "status": {
            "privacyStatus": privacy.lower(),
            "selfDeclaredMadeForKids": False,
        },
    }
    
    media = MediaFileUpload(
        video_path,
        chunksize=1024 * 1024,
        resumable=True,
        mimetype="video/*",
    )
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            click.echo(f"Uploading... {progress}%")
    
    video_id = response["id"]
    click.echo(f"\n✓ Short uploaded successfully!")
    click.echo(f"Video ID: {video_id}")
    click.echo(f"URL: https://youtube.com/shorts/{video_id}")
